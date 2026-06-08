#!/usr/bin/env python3
"""
macOS-friendly email attachment scanner.

Configuration is read from environment variables or a local .env file next to
this script. Keep passwords and bot tokens out of the Python source file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email
import email.header
import email.utils
import html
import imaplib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_dotenv(SCRIPT_DIR / ".env")
load_dotenv(Path.home() / "emailscan.env")


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Account:
    address: str
    password: str
    server: str
    mailbox: str = "INBOX"


def load_accounts() -> list[Account]:
    raw_json = env("EMAIL_ACCOUNTS_JSON")
    if raw_json:
        rows = json.loads(raw_json)
        return [
            Account(
                address=row["address"],
                password=row["password"],
                server=row.get("server", "imap.gmail.com"),
                mailbox=row.get("mailbox", "INBOX"),
            )
            for row in rows
        ]

    accounts: list[Account] = []
    gmail_address = env("GMAIL_ADDRESS")
    gmail_password = env("GMAIL_APP_PASSWORD")
    if gmail_address and gmail_password:
        accounts.append(Account(gmail_address, gmail_password, env("GMAIL_IMAP_SERVER", "imap.gmail.com")))

    extra_address = env("EXTRA_IMAP_ADDRESS")
    extra_password = env("EXTRA_IMAP_PASSWORD")
    extra_server = env("EXTRA_IMAP_SERVER")
    if extra_address and extra_password and extra_server:
        accounts.append(Account(extra_address, extra_password, extra_server))

    return accounts


SAVE_FOLDER = Path(env("SAVE_FOLDER", str(Path.home() / "Desktop" / "from Canada"))).expanduser()
PROCESSED_LOG = SAVE_FOLDER / ".processed_emails.txt"
SCAN_DAYS = int(env("SCAN_DAYS", "7"))
ENABLE_BROWSER_DOWNLOADS = env_bool("ENABLE_BROWSER_DOWNLOADS", False)
WATER_SENDERS = {
    sender.strip().lower()
    for sender in env("WATER_SENDERS").split(",")
    if sender.strip()
}

ONEDRIVE_PATTERN = re.compile(
    r"https?://(?:[a-zA-Z0-9-]+\.)?sharepoint\.com/\S+"
    r"|https?://1drv\.ms/\S+"
    r"|https?://onedrive\.live\.com/\S+",
    re.IGNORECASE,
)


def decode_header(value: str | None) -> str:
    if not value:
        return ""
    pieces: list[str] = []
    for part, charset in email.header.decode_header(value):
        if isinstance(part, bytes):
            pieces.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            pieces.append(part)
    return "".join(pieces)


def safe_filename(name: str, fallback: str = "attachment") -> str:
    cleaned = name.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    cleaned = re.sub(r"[\x00-\x1f]+", "_", cleaned)
    cleaned = cleaned.strip(". ")
    return cleaned or fallback


def unique_path(folder: Path, filename: str) -> Path:
    path = folder / filename
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = folder / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def load_processed() -> set[str]:
    if not PROCESSED_LOG.exists():
        return set()
    return {line.strip() for line in PROCESSED_LOG.read_text(encoding="utf-8").splitlines() if line.strip()}


def save_processed(key: str) -> None:
    with PROCESSED_LOG.open("a", encoding="utf-8") as handle:
        handle.write(key + "\n")


def send_telegram(downloaded_files: list[str], errors: list[str], *, enabled: bool) -> None:
    token = env("TELEGRAM_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not enabled or not token or not chat_id:
        return

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    if downloaded_files:
        file_list = "\n".join(f"  - {name}" for name in downloaded_files)
        message = f"Email Scan Report\n{now}\n\nDownloaded {len(downloaded_files)} file(s):\n{file_list}"
    else:
        message = f"Email Scan Report\n{now}\n\nNo new files found."

    if errors:
        error_list = "\n".join(f"  - {item}" for item in errors)
        message += f"\n\nErrors:\n{error_list}"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30):
        pass


def message_body(msg: email.message.Message) -> str:
    parts: list[str] = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get_content_type() not in {"text/plain", "text/html"}:
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        parts.append(payload.decode(charset, errors="replace"))
    return html.unescape("\n".join(parts))


def extract_onedrive_links(body: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for raw_link in ONEDRIVE_PATTERN.findall(body):
        link = raw_link.rstrip('.,;:!?)>]}"\'')
        if link and link not in seen:
            seen.add(link)
            links.append(link)
    return links


def filename_from_response(response: urllib.response.addinfourl, fallback_url: str) -> str:
    disposition = response.headers.get("Content-Disposition", "")
    match = re.search(r"filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?", disposition, re.IGNORECASE)
    if match:
        encoded = match.group(1) or match.group(2)
        return safe_filename(urllib.parse.unquote(encoded))

    parsed = urllib.parse.urlparse(response.geturl() or fallback_url)
    basename = Path(urllib.parse.unquote(parsed.path)).name
    return safe_filename(basename, "onedrive_download")


def with_download_flag(link: str) -> str:
    parsed = urllib.parse.urlparse(link)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query = [(key, value) for key, value in query if key.lower() != "download"]
    query.append(("download", "1"))
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))


def direct_download_candidates(link: str) -> list[str]:
    parsed = urllib.parse.urlparse(link)
    candidates = [with_download_flag(link), link]

    if parsed.netloc.lower().endswith("sharepoint.com"):
        share_value = urllib.parse.quote(link, safe="")
        candidates.append(f"{parsed.scheme}://{parsed.netloc}/_layouts/15/download.aspx?share={share_value}")

    if parsed.netloc.lower() == "onedrive.live.com":
        params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        if params.get("resid"):
            download_params = {"resid": params["resid"]}
            if params.get("authkey"):
                download_params["authkey"] = params["authkey"]
            candidates.append(
                f"{parsed.scheme}://{parsed.netloc}/download?{urllib.parse.urlencode(download_params)}"
            )

    seen: set[str] = set()
    unique_candidates: list[str] = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            unique_candidates.append(candidate)
    return unique_candidates


def extract_download_urls_from_html(html_text: str) -> list[str]:
    normalized = html.unescape(html_text)
    normalized = normalized.replace("\\u0026", "&").replace("\\/", "/")

    urls: list[str] = []
    patterns = [
        r'"downloadUrl"\s*:\s*"([^"]+)"',
        r"https?://[^\"'<> ]+/download\.aspx\?[^\"'<> ]+",
        r"https?://[^\"'<> ]+[?&]download=1[^\"'<> ]*",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, normalized, flags=re.IGNORECASE):
            url = match if isinstance(match, str) else match[0]
            url = url.replace("\\", "")
            if url.startswith("http") and url not in urls:
                urls.append(url)
    return urls


def try_download_url(candidate: str, save_folder: Path) -> tuple[str | None, list[str]]:
    request = urllib.request.Request(
        candidate,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/octet-stream,*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=90) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/html" in content_type:
            page = response.read(2 * 1024 * 1024).decode("utf-8", errors="replace")
            return None, extract_download_urls_from_html(page)

        filename = filename_from_response(response, candidate)
        if filename == "onedrive_download" and "application/json" in content_type:
            raise RuntimeError("link returned JSON instead of a downloadable file")

        path = unique_path(save_folder, filename)
        with path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        return path.name


def download_direct(link: str, save_folder: Path) -> str | None:
    candidates = direct_download_candidates(link)
    errors: list[str] = []

    while candidates:
        candidate = candidates.pop(0)
        try:
            name, discovered = try_download_url(candidate, save_folder)
            if name:
                return name
            for url in discovered:
                if url not in candidates:
                    candidates.append(url)
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            errors.append(str(exc))

    detail = "; ".join(errors) if errors else "link returned an HTML page instead of a downloadable file"
    raise RuntimeError(detail)


def wait_for_browser_downloads(folder: Path, before: set[Path], timeout_seconds: int = 120) -> list[str]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        current = set(folder.iterdir())
        partial = [item for item in current if item.name.endswith((".crdownload", ".tmp"))]
        new_files = [item for item in current - before if item.is_file() and not item.name.endswith((".crdownload", ".tmp"))]
        if new_files and not partial:
            return [item.name for item in new_files]
        time.sleep(2)
    return []


def download_with_browser(link: str, save_folder: Path) -> list[str]:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager

    before = set(save_folder.iterdir())
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(save_folder),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    try:
        driver.get(link)
        wait = WebDriverWait(driver, 30)
        download_button = wait.until(
            ec.element_to_be_clickable(
                (
                    By.XPATH,
                    '//button[contains(@aria-label,"Download") or contains(.,"Download") or contains(.,"下载")]',
                )
            )
        )
        download_button.click()
        return wait_for_browser_downloads(save_folder, before)
    finally:
        driver.quit()


def download_attachments(msg: email.message.Message, downloaded_files: list[str]) -> int:
    count = 0
    today = dt.date.today().strftime("%Y%m%d")
    for part in msg.walk():
        if part.get_content_disposition() != "attachment":
            continue
        raw_filename = decode_header(part.get_filename())
        if not raw_filename:
            continue
        filename = safe_filename(raw_filename)
        save_name = f"{today}_Water_{filename}"
        path = unique_path(SAVE_FOLDER, save_name)
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        path.write_bytes(payload)
        downloaded_files.append(path.name)
        count += 1
    return count


def scan_mailbox(account: Account, downloaded_files: list[str], errors: list[str], processed: set[str]) -> None:
    print(f"Connecting to {account.address}")
    since_date = (dt.date.today() - dt.timedelta(days=SCAN_DAYS)).strftime("%d-%b-%Y")

    with imaplib.IMAP4_SSL(account.server, 993) as mail:
        mail.login(account.address, account.password)
        mail.select(account.mailbox)
        status, data = mail.uid("search", None, f'(SINCE "{since_date}")')
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        uids = data[0].split()
        print(f"Found {len(uids)} recent emails.")

        for uid in uids:
            uid_text = uid.decode("ascii", errors="replace")
            processed_key = f"{account.address}|uid:{uid_text}"
            if processed_key in processed:
                continue

            status, msg_data = mail.uid("fetch", uid, "(RFC822)")
            if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                errors.append(f"{account.address}: failed to fetch UID {uid_text}")
                continue

            msg = email.message_from_bytes(msg_data[0][1])
            sender = email.utils.parseaddr(msg.get("From", ""))[1].lower()
            subject = decode_header(msg.get("Subject")) or "(no subject)"
            is_water = sender in WATER_SENDERS
            links = extract_onedrive_links(message_body(msg))

            if not is_water and not links:
                continue

            print(f"- {sender} | {subject}")
            had_retryable_failure = False
            did_work = False

            if is_water:
                attachment_count = download_attachments(msg, downloaded_files)
                did_work = did_work or attachment_count > 0

            for link in links:
                try:
                    name = download_direct(link, SAVE_FOLDER)
                    if name:
                        downloaded_files.append(name)
                        did_work = True
                        continue
                except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                    errors.append(f"OneDrive direct download failed for {subject}: {exc}")

                if ENABLE_BROWSER_DOWNLOADS:
                    try:
                        names = download_with_browser(link, SAVE_FOLDER)
                        if names:
                            downloaded_files.extend(names)
                            did_work = True
                        else:
                            had_retryable_failure = True
                            errors.append(f"OneDrive browser download timed out for {subject}")
                    except Exception as exc:
                        had_retryable_failure = True
                        errors.append(f"OneDrive browser download failed for {subject}: {exc}")
                else:
                    had_retryable_failure = True

            if not had_retryable_failure:
                save_processed(processed_key)
                processed.add(processed_key)
            elif did_work and is_water:
                save_processed(processed_key)
                processed.add(processed_key)


def check_config(accounts: list[Account]) -> int:
    print(f"Python: {sys.version.split()[0]}")
    print(f"Save folder: {SAVE_FOLDER}")
    print(f"Scan days: {SCAN_DAYS}")
    print(f"Configured accounts: {len(accounts)}")
    print(f"Water senders: {', '.join(sorted(WATER_SENDERS))}")
    print(f"Telegram configured: {bool(env('TELEGRAM_TOKEN') and env('TELEGRAM_CHAT_ID'))}")
    print(f"Browser fallback enabled: {ENABLE_BROWSER_DOWNLOADS}")
    if ENABLE_BROWSER_DOWNLOADS:
        try:
            import selenium  # noqa: F401
            import webdriver_manager  # noqa: F401

            print("Browser dependencies: OK")
        except Exception as exc:
            print(f"Browser dependencies: missing ({exc})")
            return 2

    if not accounts:
        print("No email accounts configured. Add .env values before running.")
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan email and download matching attachments/files.")
    parser.add_argument("--check-config", action="store_true", help="validate local configuration without logging in")
    parser.add_argument("--no-telegram", action="store_true", help="skip Telegram notification for this run")
    args = parser.parse_args()

    accounts = load_accounts()
    if args.check_config:
        return check_config(accounts)

    if not accounts:
        print("No email accounts configured. Run with --check-config for details.", file=sys.stderr)
        return 2

    SAVE_FOLDER.mkdir(parents=True, exist_ok=True)
    downloaded_files: list[str] = []
    errors: list[str] = []
    processed = load_processed()

    for account in accounts:
        try:
            scan_mailbox(account, downloaded_files, errors, processed)
        except Exception as exc:
            errors.append(f"{account.address}: {exc}")

    print(f"Done. Downloaded {len(downloaded_files)} file(s) to {SAVE_FOLDER}")
    for item in downloaded_files:
        print(f"  - {item}")
    if errors:
        print("Errors:")
        for item in errors:
            print(f"  - {item}")

    try:
        send_telegram(downloaded_files, errors, enabled=not args.no_telegram)
    except Exception as exc:
        print(f"Telegram notification failed: {exc}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
