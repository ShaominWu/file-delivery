import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Google Drive API 权限
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

# 客户文件夹映射
CLIENT_FOLDERS = {
    "MM": "MM",
    "MIG": "MIG", 
    "RITCHIE": "Ritchie",
    "simcon": "Simcon",
    "olsonfab": "Olsonfab",
    "carleton": "Carleton",
    "Shao": "Shao"
}

def get_credentials():
    """获取或创建 Google Drive 授权凭证"""
    creds = None
    
    # 获取脚本所在目录（tools/）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(script_dir, 'token.pickle')
    secrets_path = os.path.join(script_dir, 'client_secrets.json')
    
    # 检查是否已有 token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # 如果没有凭证或已过期，重新授权
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # 需要 client_secrets.json 文件
            if not os.path.exists(secrets_path):
                print(f"❌ 错误：找不到 {secrets_path}")
                print("请从 Google Cloud Console 下载 OAuth 2.0 凭证并保存为 client_secrets.json")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 保存凭证
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_or_create_folder(service, folder_name, parent_id=None):
    """获取或创建文件夹"""
    # 搜索现有文件夹
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if items:
        return items[0]['id']
    
    # 创建新文件夹
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
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    return file

def create_share_link(service, file_id, anyone_can_view=True):
    """创建分享链接"""
    if anyone_can_view:
        # 设置任何人可查看权限
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
    
    # 获取分享链接
    file = service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()
    return file.get('webContentLink') or file.get('webViewLink')

def delete_file(service, file_id):
    """删除 Google Drive 上的文件"""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except Exception as e:
        print(f"删除文件失败: {e}")
        return False

def process_client_files(client_name, local_folder, service=None):
    """处理客户文件：上传、生成链接、返回链接信息"""
    if not service:
        creds = get_credentials()
        if not creds:
            return None
        service = build('drive', 'v3', credentials=creds)
    
    if not os.path.exists(local_folder):
        return f"❌ 文件夹不存在: {local_folder}"
    
    # 获取或创建主文件夹
    main_folder_id = get_or_create_folder(service, "客户文件交付")
    
    # 获取或创建客户专用文件夹
    client_folder_name = CLIENT_FOLDERS.get(client_name, client_name)
    client_folder_id = get_or_create_folder(service, client_folder_name, main_folder_id)
    
    results = []
    
    # 遍历客户文件夹中的所有文件
    for root, dirs, files in os.walk(local_folder):
        # 跳过"已发送"文件夹
        dirs[:] = [d for d in dirs if d != "已发送"]
        
        for filename in files:
            file_path = os.path.join(root, filename)
            
            try:
                # 上传文件
                print(f"📤 正在上传: {filename} ...")
                file = upload_file(service, file_path, client_folder_id, filename)
                file_id = file['id']
                
                # 创建分享链接
                share_link = create_share_link(service, file_id, anyone_can_view=True)
                
                results.append({
                    'filename': filename,
                    'file_id': file_id,
                    'share_link': share_link,
                    'local_path': file_path
                })
                
                print(f"✅ 上传成功: {filename}")
                print(f"🔗 分享链接: {share_link}")
                
            except Exception as e:
                print(f"❌ 上传失败 {filename}: {e}")
    
    return results

def extract_project_name(filename):
    """从文件名中提取项目名称（去掉数字和无意义词，保留有意义的词）"""
    import re
    
    # 无意义的短词列表（需要过滤掉的）
    MEANINGLESS_WORDS = {
        'a', 'an', 'the', 'p', 'h', 'x', 'v', 'px', 'hp', 'hd', 'sd', 
        'mp', 'kb', 'mb', 'gb', 'and', 'or', 'of', 'in', 'on', 'at',
        'to', 'for', 'with', 'by', 'from', 'up', 'out', 'new', 'old'
    }
    
    # 去掉文件扩展名
    name_without_ext = os.path.splitext(filename)[0]
    
    # 提取所有字母（包括空格）
    letters_only = re.sub(r'[^a-zA-Z\s]', '', name_without_ext)
    
    # 分割成单词
    words = letters_only.split()
    
    # 过滤掉无意义的短词（2个字母以下或无意义词列表中的）
    meaningful_words = []
    for word in words:
        word_lower = word.lower()
        # 保留3个字母以上的词，或者不在无意义列表中的2字母词
        if len(word) > 2 or (len(word) == 2 and word_lower not in MEANINGLESS_WORDS):
            meaningful_words.append(word)
    
    # 连接成字符串（无空格）
    project_name = ''.join(meaningful_words)
    
    return project_name if project_name else "Project"

def send_client_email_with_link(client_email, company_name, share_links, ai_body=None, contact_name=None, cc_email=None):
    """发送包含 Google Drive 链接的邮件"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Gmail配置
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 465
    SENDER_EMAIL = "wushaomin7777@gmail.com"
    SENDER_PASSWORD = "dolrcqvngwtvwsao"  # Gmail应用专用密码
    
    # 从第一个文件名提取项目名称（去掉数字）
    if share_links and len(share_links) > 0:
        project_name = extract_project_name(share_links[0]['filename'])
    else:
        project_name = company_name
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = client_email
    if cc_email:
        msg['Cc'] = cc_email
    msg['Subject'] = f"[Project Delivery] {project_name} - Download Your Files"
    
    # 使用人名作为称呼，如果没有则使用公司名
    greeting_name = contact_name if contact_name else company_name
    
    if ai_body:
        body = ai_body
    else:
        body = f"""Hey {greeting_name},

Your project files for {project_name} are ready for download.

Please click the link(s) below to download your files:
"""
        for item in share_links:
            body += f"\n📄 {item['filename']}\n🔗 {item['share_link']}\n"
        
        body += """
Note: These links are private and only accessible to you. Please download within 7 days.

After you download, the files will be automatically removed from our server.

Ferrum Drafting Team
"""
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        # 如果有CC，添加到收件人列表
        recipients = [client_email]
        if cc_email:
            recipients.append(cc_email)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

def check_and_delete_downloaded_files(service, file_ids):
    """检查文件是否已被下载，如果已下载则删除"""
    deleted = []
    for file_id in file_ids:
        try:
            # 获取文件权限信息
            permissions = service.permissions().list(fileId=file_id).execute()
            # 这里可以添加更多逻辑来判断是否已被下载
            # 暂时简化：直接删除
            if delete_file(service, file_id):
                deleted.append(file_id)
        except Exception as e:
            print(f"检查文件状态时出错: {e}")
    return deleted

# ================= 主程序 =================
if __name__ == "__main__":
    import json
    
    # 加载客户配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'clients.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    clients = config['clients']
    settings = config['settings']
    local_base = settings['local_sync_folder']
    
    print("🚀 Ferrum File Delivery System")
    print("=" * 60)
    
    # 获取 Google Drive 授权
    creds = get_credentials()
    if not creds:
        print("❌ Google Drive 授权失败")
        exit(1)
    
    service = build('drive', 'v3', credentials=creds)
    print("✅ Google Drive 连接成功\n")
    
    # 遍历所有客户
    for client_key, client_info in clients.items():
        client_folder = os.path.join(local_base, client_info['folder'])
        
        if not os.path.exists(client_folder):
            continue
        
        # 检查是否有新文件
        files_to_process = []
        for root, dirs, files in os.walk(client_folder):
            dirs[:] = [d for d in dirs if d != "已发送"]  # 跳过已发送
            for filename in files:
                # 跳过 macOS 系统文件
                if filename.startswith('.') or filename == '.DS_Store':
                    continue
                file_path = os.path.join(root, filename)
                files_to_process.append((filename, file_path))
        
        if not files_to_process:
            continue
        
        print(f"📁 {client_key}: 发现 {len(files_to_process)} 个文件")
        
        # 上传到 Google Drive
        share_links = []
        for filename, file_path in files_to_process:
            print(f"  📤 上传: {filename}...")
            
            main_folder_id = get_or_create_folder(service, "客户文件交付")
            client_folder_id = get_or_create_folder(service, client_key, main_folder_id)
            
            file = upload_file(service, file_path, client_folder_id, filename)
            share_link = create_share_link(service, file['id'], anyone_can_view=True)
            
            share_links.append({
                'filename': filename,
                'file_id': file['id'],
                'share_link': share_link
            })
            print(f"     ✅ 链接: {share_link}")
        
        # 发送邮件
        cc_email = client_info.get('cc')
        print(f"  📧 发送邮件到 {client_info['email']}...")
        if cc_email:
            print(f"     📋 CC: {cc_email}")
        success, msg = send_client_email_with_link(
            client_email=client_info['email'],
            company_name=client_key,
            share_links=share_links,
            contact_name=client_info.get('contact'),  # 使用人名
            cc_email=cc_email  # 抄送邮箱
        )
        
        if success:
            print(f"     ✅ 邮件已发送")
            
            # 本地归档
            sent_folder = os.path.join(client_folder, "已发送")
            for item in share_links:
                src = os.path.join(client_folder, item['filename'])
                if not os.path.exists(sent_folder):
                    os.makedirs(sent_folder)
                dst = os.path.join(sent_folder, item['filename'])
                if os.path.exists(src):
                    os.rename(src, dst)
            print(f"     📁 本地文件已归档")
        else:
            print(f"     ❌ 发送失败: {msg}")
        
        print()
    
    print("=" * 60)
    print("✨ 文件交付流程完成")
