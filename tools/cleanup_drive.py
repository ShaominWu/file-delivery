#!/usr/bin/env python3
"""
Cloud cleanup tool.
Deletes old delivery files from Google Drive, Dropbox, and OneDrive.
"""

import argparse
import json
import os
import pickle
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

try:
    from dropbox_uploader import DropboxUploader
except Exception:
    DropboxUploader = None


TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(TOOLS_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CLIENTS_CONFIG = os.path.join(CONFIG_DIR, "clients.json")
ONEDRIVE_CONFIG = os.path.join(CONFIG_DIR, "onedrive_credentials.json")


def load_clients_config():
    with open(CLIENTS_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    return config.get("clients", {}), config.get("settings", {})


def cutoff_datetime(days_old):
    return datetime.now(timezone.utc) - timedelta(days=days_old)


def parse_cloud_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def size_mb(size):
    return int(size or 0) / (1024 * 1024)


# ================= Google Drive =================
def get_google_credentials():
    token_path = os.path.join(TOOLS_DIR, "token.pickle")
    if not os.path.exists(token_path):
        print(f"❌ 找不到 {token_path}")
        return None

    with open(token_path, "rb") as token:
        return pickle.load(token)


def google_get_folder_id(service, folder_name, parent_id=None):
    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    try:
        results = service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
        ).execute()
        items = results.get("files", [])
        if items:
            return items[0]["id"]
    except HttpError as e:
        print(f"❌ 查找 Google Drive 文件夹时出错: {e}")

    return None


def google_list_files(service, folder_id):
    files = []
    page_token = None

    while True:
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces="drive",
                fields="nextPageToken, files(id, name, createdTime, modifiedTime, size)",
                pageToken=page_token,
            ).execute()
            files.extend(results.get("files", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break
        except HttpError as e:
            print(f"❌ 列出 Google Drive 文件时出错: {e}")
            break

    return files


def google_delete_file(service, file_id):
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except HttpError as e:
        print(f"❌ 删除 Google Drive 文件失败: {e}")
        return False


def cleanup_google_client(service, root_folder, client_name, days_old, dry_run):
    print(f"\n📁 Google Drive 客户: {client_name}")

    root_folder_id = google_get_folder_id(service, root_folder)
    if not root_folder_id:
        print(f"  ❌ 找不到主文件夹: {root_folder}")
        return 0, 0

    client_folder_id = google_get_folder_id(service, client_name, root_folder_id)
    if not client_folder_id:
        print(f"  ⚠️ 找不到客户文件夹 {client_name}")
        return 0, 0

    files = google_list_files(service, client_folder_id)
    if not files:
        print("  ℹ️ 没有文件需要清理")
        return 0, 0

    print(f"  找到 {len(files)} 个文件")
    cutoff = cutoff_datetime(days_old)
    deleted_count = 0
    deleted_size = 0

    for item in files:
        created_time = parse_cloud_time(item.get("createdTime"))
        item_size = int(item.get("size", 0))
        if created_time and created_time < cutoff:
            print(f"  🗑️  {item['name']} (创建于 {created_time:%Y-%m-%d})")
            if dry_run:
                print("     [模拟删除]")
                deleted_count += 1
                deleted_size += item_size
            elif google_delete_file(service, item["id"]):
                print("     ✅ 已删除")
                deleted_count += 1
                deleted_size += item_size
        else:
            date_text = created_time.strftime("%Y-%m-%d") if created_time else "未知日期"
            print(f"  ⏳ {item['name']} (保留，创建于 {date_text})")

    print(f"  📊 清理完成: {deleted_count} 个文件, 释放 {size_mb(deleted_size):.1f} MB")
    return deleted_count, deleted_size


def cleanup_google_drive(clients, settings, days_old, dry_run, specific_client):
    creds = get_google_credentials()
    if not creds:
        print("❌ Google Drive 授权失败")
        return 0, 0

    service = build("drive", "v3", credentials=creds)
    root_folder = settings.get("google_drive_folder", "客户文件交付")
    print("✅ Google Drive 连接成功")
    print("\n" + "=" * 60)
    print(f"🧹 Google Drive 清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)

    total_count = 0
    total_size = 0
    client_names = [specific_client] if specific_client else list(clients.keys())
    for client_name in client_names:
        if client_name not in clients:
            print(f"❌ 未知客户: {client_name}")
            continue
        count, deleted_size = cleanup_google_client(
            service, root_folder, client_name, days_old, dry_run
        )
        total_count += count
        total_size += deleted_size

    return total_count, total_size


# ================= Dropbox =================
def cleanup_dropbox_client(uploader, root_folder, client_name, days_old, dry_run):
    print(f"\n📁 Dropbox 客户: {client_name}")
    path = f"/{root_folder}/{client_name}".replace("//", "/")

    try:
        result = uploader.dbx.files_list_folder(path)
        entries = list(result.entries)
        while result.has_more:
            result = uploader.dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)
    except Exception as e:
        print(f"  ⚠️ 找不到或无法读取客户文件夹 {path}: {e}")
        return 0, 0

    files = [entry for entry in entries if hasattr(entry, "id") and hasattr(entry, "server_modified")]
    if not files:
        print("  ℹ️ 没有文件需要清理")
        return 0, 0

    print(f"  找到 {len(files)} 个文件")
    cutoff = cutoff_datetime(days_old)
    deleted_count = 0
    deleted_size = 0

    for item in files:
        modified_time = parse_cloud_time(item.server_modified)
        item_size = int(getattr(item, "size", 0) or 0)
        if modified_time and modified_time < cutoff:
            print(f"  🗑️  {item.name} (修改于 {modified_time:%Y-%m-%d})")
            if dry_run:
                print("     [模拟删除]")
                deleted_count += 1
                deleted_size += item_size
            else:
                ok, error = uploader.delete_file(item.path_lower or item.path_display)
                if ok:
                    print("     ✅ 已删除")
                    deleted_count += 1
                    deleted_size += item_size
                else:
                    print(f"     ❌ 删除失败: {error}")
        else:
            date_text = modified_time.strftime("%Y-%m-%d") if modified_time else "未知日期"
            print(f"  ⏳ {item.name} (保留，修改于 {date_text})")

    print(f"  📊 清理完成: {deleted_count} 个文件, 释放 {size_mb(deleted_size):.1f} MB")
    return deleted_count, deleted_size


def cleanup_dropbox(clients, settings, days_old, dry_run, specific_client):
    if DropboxUploader is None:
        print("\n⚠️ Dropbox 模块不可用，跳过 Dropbox 清理")
        return 0, 0

    uploader = DropboxUploader()
    if not uploader.is_authenticated():
        print("\n⚠️ Dropbox 未认证，跳过 Dropbox 清理")
        return 0, 0

    root_folder = settings.get("dropbox_folder", settings.get("google_drive_folder", "客户文件交付"))
    print("\n✅ Dropbox 连接成功")
    print("\n" + "=" * 60)
    print(f"🧹 Dropbox 清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)

    total_count = 0
    total_size = 0
    client_names = [specific_client] if specific_client else list(clients.keys())
    for client_name in client_names:
        if client_name not in clients:
            print(f"❌ 未知客户: {client_name}")
            continue
        count, deleted_size = cleanup_dropbox_client(
            uploader, root_folder, client_name, days_old, dry_run
        )
        total_count += count
        total_size += deleted_size

    return total_count, total_size


# ================= OneDrive =================
def load_onedrive_config():
    if not os.path.exists(ONEDRIVE_CONFIG):
        return None
    with open(ONEDRIVE_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def save_onedrive_config(config):
    with open(ONEDRIVE_CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")


def get_onedrive_access_token(config):
    env_token = os.environ.get("ONEDRIVE_ACCESS_TOKEN")
    if env_token:
        return env_token

    required = ["client_id", "refresh_token"]
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise RuntimeError(f"缺少 OneDrive 配置: {', '.join(missing)}")

    tenant_id = config.get("tenant_id", "consumers")
    data = {
        "client_id": config["client_id"],
        "refresh_token": config["refresh_token"],
        "grant_type": "refresh_token",
        "scope": config.get("scope", "offline_access Files.ReadWrite User.Read"),
    }
    if config.get("client_secret"):
        data["client_secret"] = config["client_secret"]

    request = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        data=urllib.parse.urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("refresh_token") and payload["refresh_token"] != config.get("refresh_token"):
        config["refresh_token"] = payload["refresh_token"]
        save_onedrive_config(config)

    return payload["access_token"]


def graph_request(method, path, access_token):
    request = urllib.request.Request(
        f"https://graph.microsoft.com/v1.0{path}",
        headers={"Authorization": f"Bearer {access_token}"},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status == 204:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        details = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Microsoft Graph {e.code}: {details}") from e


def onedrive_children_path(config, folder_path):
    drive_id = config.get("drive_id")
    encoded = urllib.parse.quote(folder_path.strip("/"), safe="/")
    if drive_id:
        return f"/drives/{drive_id}/root:/{encoded}:/children"
    return f"/me/drive/root:/{encoded}:/children"


def onedrive_delete_path(config, item_id):
    drive_id = config.get("drive_id")
    if drive_id:
        return f"/drives/{drive_id}/items/{item_id}"
    return f"/me/drive/items/{item_id}"


def cleanup_onedrive_client(config, access_token, root_folder, client_name, days_old, dry_run):
    print(f"\n📁 OneDrive 客户: {client_name}")
    folder_path = f"{root_folder}/{client_name}".strip("/")

    try:
        result = graph_request("GET", onedrive_children_path(config, folder_path), access_token)
    except Exception as e:
        print(f"  ⚠️ 找不到或无法读取客户文件夹 /{folder_path}: {e}")
        return 0, 0

    files = [item for item in result.get("value", []) if "file" in item]
    if not files:
        print("  ℹ️ 没有文件需要清理")
        return 0, 0

    print(f"  找到 {len(files)} 个文件")
    cutoff = cutoff_datetime(days_old)
    deleted_count = 0
    deleted_size = 0

    for item in files:
        created_time = parse_cloud_time(item.get("createdDateTime") or item.get("lastModifiedDateTime"))
        item_size = int(item.get("size", 0) or 0)
        if created_time and created_time < cutoff:
            print(f"  🗑️  {item['name']} (创建于 {created_time:%Y-%m-%d})")
            if dry_run:
                print("     [模拟删除]")
                deleted_count += 1
                deleted_size += item_size
            else:
                graph_request("DELETE", onedrive_delete_path(config, item["id"]), access_token)
                print("     ✅ 已删除")
                deleted_count += 1
                deleted_size += item_size
        else:
            date_text = created_time.strftime("%Y-%m-%d") if created_time else "未知日期"
            print(f"  ⏳ {item['name']} (保留，创建于 {date_text})")

    print(f"  📊 清理完成: {deleted_count} 个文件, 释放 {size_mb(deleted_size):.1f} MB")
    return deleted_count, deleted_size


def cleanup_onedrive(clients, settings, days_old, dry_run, specific_client):
    config = load_onedrive_config()
    if not config and not os.environ.get("ONEDRIVE_ACCESS_TOKEN"):
        print("\n⚠️ OneDrive 未配置，跳过 OneDrive 清理")
        print(f"   需要创建授权文件: {ONEDRIVE_CONFIG}")
        return 0, 0

    config = config or {}
    try:
        access_token = get_onedrive_access_token(config)
    except Exception as e:
        print(f"\n⚠️ OneDrive 授权失败，跳过 OneDrive 清理: {e}")
        return 0, 0

    root_folder = config.get(
        "root_folder",
        settings.get("onedrive_folder", settings.get("google_drive_folder", "客户文件交付")),
    )
    print("\n✅ OneDrive 连接成功")
    print("\n" + "=" * 60)
    print(f"🧹 OneDrive 清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)

    total_count = 0
    total_size = 0
    client_names = [specific_client] if specific_client else list(clients.keys())
    for client_name in client_names:
        if client_name not in clients:
            print(f"❌ 未知客户: {client_name}")
            continue
        count, deleted_size = cleanup_onedrive_client(
            config, access_token, root_folder, client_name, days_old, dry_run
        )
        total_count += count
        total_size += deleted_size

    return total_count, total_size


# ================= Local sent folders =================
def cleanup_local_sent_client(client_info, local_base, client_name, days_old, dry_run):
    print(f"\n📁 本地已发送 客户: {client_name}")

    client_folder = os.path.join(local_base, client_info.get("folder", client_name))
    sent_folder = os.path.join(client_folder, "已发送")
    if not os.path.isdir(sent_folder):
        print("  ℹ️ 没有「已发送」文件夹")
        return 0, 0

    cutoff = cutoff_datetime(days_old)
    deleted_count = 0
    deleted_size = 0
    found_count = 0

    for root, dirs, files in os.walk(sent_folder):
        dirs[:] = [d for d in dirs if d != "#SyncVersion"]
        for filename in files:
            if filename in {"desktop.ini", "Thumbs.db", ".DS_Store"}:
                continue

            file_path = os.path.join(root, filename)
            try:
                st = os.stat(file_path)
            except OSError:
                continue

            found_count += 1
            modified_time = datetime.fromtimestamp(st.st_mtime, timezone.utc)
            if modified_time < cutoff:
                print(f"  🗑️  {filename} (修改于 {modified_time:%Y-%m-%d})")
                if dry_run:
                    print("     [模拟删除]")
                    deleted_count += 1
                    deleted_size += st.st_size
                else:
                    try:
                        os.remove(file_path)
                        print("     ✅ 已删除")
                        deleted_count += 1
                        deleted_size += st.st_size
                    except OSError as e:
                        print(f"     ❌ 删除失败: {e}")
            else:
                print(f"  ⏳ {filename} (保留，修改于 {modified_time:%Y-%m-%d})")

    if not found_count:
        print("  ℹ️ 没有文件需要清理")

    print(f"  📊 清理完成: {deleted_count} 个文件, 释放 {size_mb(deleted_size):.1f} MB")
    return deleted_count, deleted_size


def cleanup_local_sent(clients, settings, days_old, dry_run, specific_client):
    local_base = settings.get("windows_sync_folder", settings.get("local_sync_folder", ""))
    if not local_base or not os.path.isdir(local_base):
        print(f"\n⚠️ 本地绿联云同步文件夹不存在，跳过本地清理: {local_base}")
        return 0, 0

    print("\n" + "=" * 60)
    print(f"🧹 本地「已发送」清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)

    total_count = 0
    total_size = 0
    client_names = [specific_client] if specific_client else list(clients.keys())
    for client_name in client_names:
        if client_name not in clients:
            print(f"❌ 未知客户: {client_name}")
            continue
        count, deleted_size = cleanup_local_sent_client(
            clients[client_name], local_base, client_name, days_old, dry_run
        )
        total_count += count
        total_size += deleted_size

    return total_count, total_size


def main():
    parser = argparse.ArgumentParser(description="清理云端旧文件")
    parser.add_argument("--days", type=int, default=7, help="云端保留天数（默认7天）")
    parser.add_argument("--local-days", type=int, default=30, help="本地「已发送」保留天数（默认30天）")
    parser.add_argument("--dry-run", action="store_true", help="模拟模式，不真正删除")
    parser.add_argument("--client", type=str, help="指定客户名称（如MM、MIG等）")
    parser.add_argument(
        "--cloud",
        choices=["scheduled", "all", "google", "dropbox", "onedrive", "local"],
        default="scheduled",
        help="要清理的位置（默认scheduled: Google Drive + Dropbox + OneDrive + 本地已发送）",
    )
    args = parser.parse_args()

    try:
        clients, settings = load_clients_config()
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return 1

    total_count = 0
    total_size = 0

    if args.cloud in ("scheduled", "all", "google"):
        count, deleted_size = cleanup_google_drive(
            clients, settings, args.days, args.dry_run, args.client
        )
        total_count += count
        total_size += deleted_size

    if args.cloud in ("scheduled", "all", "dropbox"):
        count, deleted_size = cleanup_dropbox(
            clients, settings, args.days, args.dry_run, args.client
        )
        total_count += count
        total_size += deleted_size

    if args.cloud in ("scheduled", "all", "onedrive"):
        count, deleted_size = cleanup_onedrive(
            clients, settings, args.days, args.dry_run, args.client
        )
        total_count += count
        total_size += deleted_size

    if args.cloud in ("scheduled", "all", "local"):
        count, deleted_size = cleanup_local_sent(
            clients, settings, args.local_days, args.dry_run, args.client
        )
        total_count += count
        total_size += deleted_size

    print("\n" + "=" * 60)
    print(f"✨ 全部清理完成，共删除 {total_count} 个文件，释放 {size_mb(total_size):.1f} MB")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
