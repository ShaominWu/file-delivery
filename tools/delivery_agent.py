#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ferrum File Delivery System - Mac版
自动扫描绿联云同步文件夹，上传到Google Drive + Dropbox，发送邮件给客户
"""

import os
import sys
import pickle
import json
import re
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from html import escape
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# 导入 Dropbox 上传模块
try:
    from dropbox_uploader import DropboxUploader
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

# Google Drive API 权限
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

SCRIPT_DIR = Path(__file__).resolve().parent


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(SCRIPT_DIR / ".env")


def env(name, default=""):
    return os.environ.get(name, default).strip()

# ===================== 日志设置 =====================
def setup_logging(log_folder):
    """设置日志，同时输出到文件和控制台"""
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, f"delivery-{datetime.now().strftime('%Y%m%d-%H%M')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file

# ===================== Google Drive =====================
def get_credentials(tools_dir):
    """获取或刷新 Google Drive 授权凭证"""
    creds = None
    token_path = os.path.join(tools_dir, 'token.pickle')
    secrets_path = os.path.join(tools_dir, 'client_secrets.json')

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(secrets_path):
                logging.error(f"找不到 {secrets_path}")
                logging.error("请从 Google Cloud Console 下载 OAuth 2.0 凭证并保存为 client_secrets.json")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def get_or_create_folder(service, folder_name, parent_id=None):
    """获取或创建 Google Drive 文件夹"""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']

    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']

def upload_file(service, file_path, folder_id, filename=None):
    """上传文件到 Google Drive"""
    if not filename:
        filename = os.path.basename(file_path)

    file_metadata = {'name': filename, 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    return file

def create_share_link(service, file_id):
    """创建公开分享链接"""
    permission = {'type': 'anyone', 'role': 'reader'}
    service.permissions().create(fileId=file_id, body=permission).execute()
    file = service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()
    return file.get('webContentLink') or file.get('webViewLink')

# ===================== 邮件 =====================
def extract_project_name(filename):
    """从文件名提取项目名称"""
    MEANINGLESS_WORDS = {
        'a', 'an', 'the', 'p', 'h', 'x', 'v', 'px', 'hp', 'hd', 'sd',
        'mp', 'kb', 'mb', 'gb', 'and', 'or', 'of', 'in', 'on', 'at',
        'to', 'for', 'with', 'by', 'from', 'up', 'out', 'new', 'old'
    }
    name_without_ext = os.path.splitext(filename)[0]
    letters_only = re.sub(r'[^a-zA-Z\s]', '', name_without_ext)
    words = letters_only.split()
    meaningful_words = [
        w for w in words
        if len(w) > 2 or (len(w) == 2 and w.lower() not in MEANINGLESS_WORDS)
    ]
    return ''.join(meaningful_words) if meaningful_words else "Project"

def send_email(client_email, company_name, share_links, contact_name=None, cc_email=None, signature=None):
    """发送包含下载链接的邮件"""
    SMTP_SERVER = env("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(env("SMTP_PORT", "465"))
    SENDER_EMAIL = env("SENDER_EMAIL") or env("GMAIL_ADDRESS")
    SENDER_PASSWORD = env("SENDER_PASSWORD") or env("GMAIL_APP_PASSWORD")

    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return False, "缺少 SENDER_EMAIL/SENDER_PASSWORD 或 GMAIL_ADDRESS/GMAIL_APP_PASSWORD"

    project_name = extract_project_name(share_links[0]['filename']) if share_links else company_name
    greeting_name = contact_name if contact_name else company_name

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = client_email
    if cc_email:
        msg['Cc'] = cc_email
    msg['Subject'] = f"[Project Delivery] {project_name} - Download Your Files"

    body = f"Hey {greeting_name},\n\nYour project files for {project_name} are ready for download.\n\nPlease choose your preferred download method:\n"

    for item in share_links:
        body += f"\n📄 {item['filename']}\n"
        if 'gdrive_link' in item:
            body += f"🔗 Google Drive: {item['gdrive_link']}\n"
        if 'dropbox_link' in item:
            body += f"🔗 Dropbox: {item['dropbox_link']}\n"
        if 'dropbox_error' in item and 'dropbox_link' not in item:
            body += f"   (Dropbox temporarily unavailable)\n"

    team_name = signature if signature else "Ferrum Drafting Team"
    body += f"\nNote: These links are private and only accessible to you. Please download within 7 days.\n\nAfter you download, the files will be automatically removed from our server.\n\n{team_name}\n"

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        recipients = [client_email]
        if cc_email:
            recipients.append(cc_email)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)


# ===================== 日报 =====================
def send_daily_report(report_items):
    """发送每日发送汇总报告给老板"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    SMTP_SERVER = env("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(env("SMTP_PORT", "465"))
    SENDER_EMAIL = env("SENDER_EMAIL") or env("GMAIL_ADDRESS")
    SENDER_PASSWORD = env("SENDER_PASSWORD") or env("GMAIL_APP_PASSWORD")
    REPORT_TO = env("REPORT_TO", SENDER_EMAIL)

    if not SENDER_EMAIL or not SENDER_PASSWORD or not REPORT_TO:
        logging.error("发送报告失败: 缺少邮箱配置")
        return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = REPORT_TO
    msg['Subject'] = f"[Ferrum Delivery Report] {datetime.now().strftime('%Y-%m-%d')} - {len(report_items)} 个客户"

    body = f"Ferrum File Delivery - 发送报告\n"
    body += f"时间：{now}\n"
    body += "=" * 50 + "\n\n"

    for item in report_items:
        body += f"✅ 客户：{item['client']}\n"
        body += f"   邮箱：{item['email']}\n"
        for f in item['files']:
            body += f"   📄 {f}\n"
        body += "\n"

    body += "=" * 50 + "\n"
    body += f"共发送 {sum(len(i['files']) for i in report_items)} 个文件给 {len(report_items)} 个客户\n"

    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, REPORT_TO, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        logging.error(f"发送报告失败: {e}")
        return False


# ===================== Telegram 通知 =====================
def send_telegram(message):
    """发送Telegram通知"""
    import urllib.request
    import urllib.parse

    TELEGRAM_TOKEN = env("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = env("TELEGRAM_CHAT_ID")

    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("⚠️ Telegram未配置，跳过通知")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        logging.error(f"Telegram发送失败: {e}")
        return False


def is_sync_temp_file(filename):
    """判断是否为绿联云/Syncthing 同步临时文件。"""
    return filename.startswith('.syncthing.') or filename.endswith('.tmp')


def load_sync_alert_state(log_dir):
    state_path = os.path.join(log_dir, 'sync-alert-state.json')
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return state_path, json.load(f)
    except Exception:
        return state_path, {'notified': []}


def save_sync_alert_state(state_path, state):
    try:
        state['notified'] = state.get('notified', [])[-500:]
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"保存绿联云提醒状态失败: {e}")


def collect_sync_alerts(local_base, recent_hours=24):
    """收集同步未完成、还不能自动发送的近期文件。"""
    alerts = []
    cutoff = datetime.now().timestamp() - recent_hours * 3600

    for root, dirs, files in os.walk(local_base):
        dirs[:] = [d for d in dirs if d not in {'#SyncVersion', '已发送'}]
        rel_root = os.path.relpath(root, local_base)
        parts = [] if rel_root == '.' else rel_root.split(os.sep)
        client_name = parts[0] if parts else '绿联云同步'

        for filename in files:
            if filename in {'desktop.ini', 'Thumbs.db', '.DS_Store'}:
                continue

            if not is_sync_temp_file(filename):
                continue

            file_path = os.path.join(root, filename)
            try:
                st = os.stat(file_path)
            except OSError:
                continue

            if st.st_mtime < cutoff:
                continue

            rel_path = os.path.relpath(file_path, local_base)
            alerts.append({
                'key': f"{rel_path}|{int(st.st_mtime)}|{st.st_size}",
                'client': client_name,
                'filename': filename,
                'reason': '同步还没完成，是临时文件',
                'mtime': datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                'size': st.st_size,
            })

    return alerts


def send_sync_alert_if_needed(log_dir, local_base):
    alerts = collect_sync_alerts(local_base)
    if not alerts:
        return 0

    state_path, state = load_sync_alert_state(log_dir)
    notified = set(state.get('notified', []))
    fresh_alerts = [item for item in alerts if item['key'] not in notified]
    if not fresh_alerts:
        return 0

    preview = fresh_alerts[:8]
    msg = "⚠️ <b>绿联云扫描提醒</b>\n"
    msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    msg += "Mac mini 看到了还在同步中的临时文件，所以暂时没有自动发送给客户：\n"
    for item in preview:
        msg += f"• <b>{escape(item['client'])}</b>: {escape(item['filename'])}\n"
        msg += f"  {escape(item['reason'])}（{escape(item['mtime'])}）\n"
    if len(fresh_alerts) > len(preview):
        msg += f"\n还有 {len(fresh_alerts) - len(preview)} 个类似文件。\n"
    msg += "\n请等同步完成，正式文件出现后程序会自动发送。"

    if send_telegram(msg):
        notified.update(item['key'] for item in fresh_alerts)
        state['notified'] = list(notified)
        save_sync_alert_state(state_path, state)
        return len(fresh_alerts)
    return 0

# ===================== 主程序 =====================
def main():
    # 确定目录
    tools_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(tools_dir)
    log_dir = os.path.join(base_dir, 'logs')

    log_file = setup_logging(log_dir)

    logging.info("=" * 60)
    logging.info("🚀 Ferrum File Delivery System (Windows)")
    logging.info(f"📋 日志文件: {log_file}")
    logging.info("=" * 60)

    # 加载客户配置
    config_path = os.path.join(base_dir, 'config', 'clients.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        logging.error(f"❌ 加载配置失败: {e}")
        sys.exit(1)

    clients = config['clients']
    settings = config['settings']
    # Windows路径：优先用配置文件里的windows_sync_folder，否则用local_sync_folder
    local_base = settings.get('windows_sync_folder', settings.get('local_sync_folder', ''))

    if not os.path.exists(local_base):
        logging.error(f"❌ 同步文件夹不存在: {local_base}")
        logging.error("请检查 config/clients.json 里的 windows_sync_folder 路径")
        sys.exit(1)

    # 连接 Google Drive
    creds = get_credentials(tools_dir)
    if not creds:
        logging.error("❌ Google Drive 授权失败")
        sys.exit(1)

    service = build('drive', 'v3', credentials=creds)
    logging.info("✅ Google Drive 连接成功")

    # 检查 Dropbox
    dropbox_ok = False
    if DROPBOX_AVAILABLE:
        dbx_uploader = DropboxUploader()
        if dbx_uploader.is_authenticated():
            logging.info("✅ Dropbox 连接成功")
            dropbox_ok = True
        else:
            logging.warning("⚠️ Dropbox 未认证，将只使用 Google Drive")
    else:
        logging.warning("⚠️ Dropbox 模块未安装，将只使用 Google Drive")

    logging.info("")

    # 遍历所有客户
    processed_count = 0
    report_items = []

    for client_key, client_info in clients.items():
        client_folder = os.path.join(local_base, client_info['folder'])

        if not os.path.exists(client_folder):
            continue

        # 收集待处理文件（跳过"已发送"子文件夹和隐藏文件）
        files_to_process = []
        for root, dirs, files in os.walk(client_folder):
            dirs[:] = [d for d in dirs if d != '已发送']
            for filename in files:
                if filename.startswith('.') or filename == 'desktop.ini' or filename == 'Thumbs.db':
                    continue
                file_path = os.path.join(root, filename)
                files_to_process.append((filename, file_path))

        if not files_to_process:
            continue

        logging.info(f"📁 {client_key}: 发现 {len(files_to_process)} 个文件")

        # 上传文件
        share_links = []
        main_folder_id = get_or_create_folder(service, "客户文件交付")
        client_folder_id = get_or_create_folder(service, client_key, main_folder_id)

        for filename, file_path in files_to_process:
            logging.info(f"  📤 上传: {filename}...")

            try:
                # Google Drive
                file = upload_file(service, file_path, client_folder_id, filename)
                gdrive_link = create_share_link(service, file['id'])
                link_info = {
                    'filename': filename,
                    'file_id': file['id'],
                    'gdrive_link': gdrive_link
                }
                logging.info(f"     ✅ Google Drive OK")

                # Dropbox
                if dropbox_ok:
                    result = dbx_uploader.upload_and_share(file_path, client_key)
                    if result.get('share_link'):
                        link_info['dropbox_link'] = result['share_link']
                        logging.info(f"     ✅ Dropbox OK")
                    else:
                        link_info['dropbox_error'] = result.get('error', '未知错误')
                        logging.warning(f"     ⚠️ Dropbox 失败: {link_info['dropbox_error']}")

                share_links.append(link_info)

            except Exception as e:
                logging.error(f"  ❌ 上传失败 {filename}: {e}")

        if not share_links:
            continue

        # 发送邮件
        cc_email = client_info.get('cc')
        logging.info(f"  📧 发送邮件到 {client_info['email']}...")

        success, msg = send_email(
            client_email=client_info['email'],
            company_name=client_key,
            share_links=share_links,
            contact_name=client_info.get('contact'),
            cc_email=cc_email,
            signature=client_info.get('signature')
        )

        if success:
            logging.info(f"     ✅ 邮件已发送")

            # 归档到"已发送"文件夹
            sent_folder = os.path.join(client_folder, '已发送')
            os.makedirs(sent_folder, exist_ok=True)

            for item in share_links:
                src = os.path.join(client_folder, item['filename'])
                if os.path.exists(src):
                    dst = os.path.join(sent_folder, item['filename'])
                    # 如果目标已存在，加时间戳
                    if os.path.exists(dst):
                        name, ext = os.path.splitext(item['filename'])
                        dst = os.path.join(sent_folder, f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")
                    os.rename(src, dst)

            logging.info(f"     📁 本地文件已归档到「已发送」")
            processed_count += 1
            report_items.append({
                'client': client_key,
                'email': client_info['email'],
                'files': [item['filename'] for item in share_links]
            })
        else:
            logging.error(f"     ❌ 发送邮件失败: {msg}")

        logging.info("")

    logging.info("=" * 60)
    if processed_count > 0:
        logging.info(f"✨ 完成！共处理 {processed_count} 个客户的文件")
        # 发送日报邮件
        if send_daily_report(report_items):
            logging.info("📊 日报已发送")

        # 发送Telegram通知
        total_files = sum(len(i['files']) for i in report_items)
        tg_msg = f"📦 <b>Ferrum 文件发送报告</b>\n"
        tg_msg += f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for item in report_items:
            tg_msg += f"✅ <b>{item['client']}</b>\n"
            for f in item['files']:
                tg_msg += f"   📄 {f}\n"
            tg_msg += "\n"
        tg_msg += f"共 {total_files} 个文件 → {len(report_items)} 个客户"
        if send_telegram(tg_msg):
            logging.info("📱 Telegram通知已发送")
        logging.info("=" * 60)
    else:
        logging.info("ℹ️ 没有发现新文件，无需处理")
        alert_count = send_sync_alert_if_needed(log_dir, local_base)
        if alert_count:
            logging.info(f"📱 绿联云扫描提醒已发送（{alert_count} 个文件）")
        logging.info("=" * 60)

if __name__ == "__main__":
    main()
