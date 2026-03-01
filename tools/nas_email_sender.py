import os
import smtplib
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Google Drive API
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ================= 配置区 =================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "wushaomin7777@gmail.com"
SENDER_PASSWORD = os.environ.get("GMAIL_PASSWORD", "dolrcqvngwtvwsao")  # Gmail应用专用密码

# 绿联云同步文件夹路径
NAS_FOLDER = "/Users/bear/Shared/绿联云同步"

# Gmail 附件限制 (MB)
GMAIL_SIZE_LIMIT_MB = 20
GMAIL_SIZE_LIMIT_BYTES = GMAIL_SIZE_LIMIT_MB * 1024 * 1024

# Google Drive 文件夹 ID (客户文件交付)
GDRIVE_FOLDER_ID = "1Hw1s2Xbktm2DQxwPSGQmE9NOt7syviCV"

# 公司邮箱映射表（文件夹名 → 邮箱）
CLIENT_MAP = {
    "MM": "bert@mmstructural.ca",
    "MIG": "SERGE@MIGSTEEL.COM",
    "RITCHIE": "sdionne@ritchieswelding.ca",
    "simcon": "dscott.simcon@live.ca",
    "olsonfab": "cglover@olsonfab.com",
    "carleton": "greg@carletoniron.com",
    "Shao": "wushaomin69@163.com",
    "WW": "wwstrusteelengineering@gmail.com",
    "KILMARNOCK": "ssharpe@kilmarnock.ca",
    "LEMIRE": "bob@lemire.on.ca",
    "ALEXANDER": "alex@egesolutions.com",
    "JT": "jt@morissetconstruction.com",
}
# ==========================================

def get_google_drive_service():
    """获取 Google Drive API 服务"""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            import pickle
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # 保存刷新后的 token
            with open(token_path, 'wb') as token:
                import pickle
                pickle.dump(creds, token)
        else:
            return None
    
    return build('drive', 'v3', credentials=creds)

def upload_to_google_drive(file_path: str, filename: str) -> str:
    """上传文件到 Google Drive 并返回分享链接"""
    try:
        service = get_google_drive_service()
        if not service:
            return None
        
        file_metadata = {
            'name': filename,
            'parents': [GDRIVE_FOLDER_ID]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        
        # 设置文件为任何人可查看
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # 返回分享链接
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    except Exception as e:
        print(f"Google Drive 上传失败: {e}")
        return None

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

def send_client_email(client_email: str, company_name: str, file_path: str = None, download_link: str = None, ai_generated_body: str = None, cc_email: str = None, signature: str = None, use_drive_for_large_files: bool = True, contact_name: str = None) -> str:
    """
    向客户发送邮件，可带附件或下载链接
    大文件自动使用 Google Drive 链接
    contact_name: 联系人名字，用于邮件称呼 (如 "Greg")，不传则使用 company_name
    """
    # 提取项目名称（从文件名中去掉数字）
    if file_path:
        filename = os.path.basename(file_path)
        project_name = extract_project_name(filename)
    else:
        project_name = company_name
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = client_email
    if cc_email:
        msg['Cc'] = cc_email
    msg['Subject'] = f"[Project Delivery] {project_name} - Latest Drawings & Models"
    
    # 检查文件大小
    file_size = 0
    use_drive_link = False
    drive_link = None
    
    if file_path and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        # 如果文件超过限制，上传到 Google Drive
        if use_drive_for_large_files and file_size > GMAIL_SIZE_LIMIT_BYTES:
            print(f"  文件 {filename} ({file_size/1024/1024:.1f}MB) 超过 {GMAIL_SIZE_LIMIT_MB}MB，使用 Google Drive 链接...")
            drive_link = upload_to_google_drive(file_path, filename)
            if drive_link:
                use_drive_link = True
                print(f"  ✓ 已上传至 Google Drive: {drive_link}")
    
    # 邮件正文 - 英文版（适配加拿大客户）
    if ai_generated_body:
        full_body = ai_generated_body
    else:
        # 使用自定义签名或默认签名
        sig = signature if signature else "Ferrum Drafting Team"
        filename = os.path.basename(file_path) if file_path else 'See attachment'
        # 称呼：优先使用 contact_name，否则用 company_name
        greeting_name = contact_name if contact_name else company_name
        
        if use_drive_link and drive_link:
            full_body = f"""Hey {greeting_name},

Please find the latest project files for {project_name}.

File: {filename}
Size: {file_size/1024/1024:.1f}MB

Due to file size, please download from this link:
{drive_link}

Kindly download and check the files. If you have any questions, please feel free to contact us.

{sig}"""
        else:
            full_body = f"Hey {greeting_name},\n\nPlease find attached the latest project files for {project_name}.\n\nFile: {filename}\n\nKindly download and check the files. If you have any questions, please feel free to contact us.\n\n{sig}"
    
    msg.attach(MIMEText(full_body, 'plain', 'utf-8'))
    
    # 如果有本地文件且不太大，作为附件添加
    if file_path and os.path.exists(file_path) and not use_drive_link:
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
        encoders.encode_base64(attachment)
        attachment.add_header('Content-Disposition', f'attachment; filename={filename}')
        msg.attach(attachment)
    
    try:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        # 如果有CC，添加到收件人列表
        recipients = [client_email]
        if cc_email:
            recipients.append(cc_email)
        server.sendmail(SENDER_EMAIL, recipients, msg.as_string())
        server.quit()
        
        if use_drive_link:
            return f"✓ 成功：已发送 Google Drive 链接至 {client_email}" + (f" (CC: {cc_email})" if cc_email else "")
        else:
            return f"✓ 成功：已将文件发送至 {client_email}" + (f" (CC: {cc_email})" if cc_email else "")
    except Exception as e:
        return f"✗ 错误：邮件发送失败 - {str(e)}"

def cleanup_nas_folder(folder_path: str, days_old: int = 7, move_to: str = None) -> str:
    """
    清理NAS文件夹里的旧文件
    - days_old: 超过多少天的文件
    - move_to: 如果指定，移动到该文件夹而不是删除
    """
    if not os.path.exists(folder_path):
        return f"✗ 错误：找不到路径 {folder_path}"
    
    deleted_files = []
    moved_files = []
    current_time = time.time()
    
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            # 检查文件修改时间
            if (current_time - os.path.getmtime(file_path)) > (days_old * 86400):
                try:
                    if move_to:
                        # 移动到备份文件夹
                        if not os.path.exists(move_to):
                            os.makedirs(move_to)
                        new_path = os.path.join(move_to, filename)
                        os.rename(file_path, new_path)
                        moved_files.append(filename)
                    else:
                        # 直接删除
                        os.remove(file_path)
                        deleted_files.append(filename)
                except Exception as e:
                    print(f"处理 {filename} 时出错: {e}")
    
    result = []
    if deleted_files:
        result.append(f"已删除 {len(deleted_files)} 个旧文件")
    if moved_files:
        result.append(f"已移动 {len(moved_files)} 个文件到备份区")
    
    return "；".join(result) if result else "无需清理：没有超期文件"

def auto_send_by_company_folder(folder_path: str, move_sent: bool = True) -> str:
    """
    根据文件夹名识别公司，递归搜索该文件夹下所有文件并发送
    文件夹名对应公司: MM/, MIG/, Ritchie/, simcon/, olsonfab/, carleton/, Shao/
    """
    if not os.path.exists(folder_path):
        return f"✗ 错误：路径不存在 {folder_path}"
    
    # 读取客户配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'clients.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        clients = config.get('clients', {})
    except:
        clients = {}
    
    results = []
    
    # 遍历所有公司文件夹
    for company_key in CLIENT_MAP:
        company_folder = os.path.join(folder_path, company_key)
        
        if not os.path.exists(company_folder):
            continue
        
        # 递归搜索该文件夹下所有文件
        files_to_send = []
        for root, dirs, files in os.walk(company_folder):
            # 跳过"已发送"文件夹
            dirs[:] = [d for d in dirs if d != "已发送"]
            
            for filename in files:
                # 跳过 macOS 系统文件
                if filename.startswith('.') or filename == '.DS_Store':
                    continue
                file_path = os.path.join(root, filename)
                files_to_send.append((filename, file_path))
        
        if not files_to_send:
            continue
        
        client_email = CLIENT_MAP[company_key]
        # 从JSON配置获取CC邮箱和联系人信息
        client_info = clients.get(company_key, {})
        cc_email = client_info.get('cc')
        contact_name = client_info.get('contact')  # 联系人名字
        
        sent_folder = os.path.join(company_folder, "已发送")
        
        for filename, file_path in files_to_send:
            # 发送邮件（支持自定义签名、联系人名字、大文件自动用Google Drive）
            custom_signature = client_info.get('signature')
            result = send_client_email(
                client_email=client_email,
                company_name=company_key,
                file_path=file_path,
                cc_email=cc_email,
                signature=custom_signature,
                use_drive_for_large_files=True,
                contact_name=contact_name
            )
            results.append(f"✓ {company_key}/{filename} → {client_email}: {result}")
            
            # 移动文件到已发送文件夹
            if move_sent and "成功" in result:
                if not os.path.exists(sent_folder):
                    os.makedirs(sent_folder)
                
                # 保持相对路径结构
                rel_path = os.path.relpath(file_path, company_folder)
                new_path = os.path.join(sent_folder, rel_path)
                
                # 创建目标目录
                new_dir = os.path.dirname(new_path)
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir)
                
                os.rename(file_path, new_path)
                results.append(f"  已移动到: {new_path}")
    
    return "\n".join(results) if results else "没有可处理的文件"

# ================= 主程序 =================
if __name__ == "__main__":
    import sys
    
    # 检查是否有 --report 参数（生成报告模式）
    if "--report" in sys.argv:
        generate_report = True
    else:
        generate_report = False
    
    # 自动根据文件夹名识别公司并发送
    print("正在扫描NAS文件夹并自动发送...")
    print(f"文件夹: {NAS_FOLDER}")
    print(f"已配置公司: {', '.join(CLIENT_MAP.keys())}")
    print("-" * 50)
    
    result = auto_send_by_company_folder(NAS_FOLDER, move_sent=True)
    print(result)
    
    # 统计成功/失败 - 按公司分组
    from collections import defaultdict
    company_stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'files': []})
    
    for line in result.split('\n'):
        if '✓' in line and '→' in line:
            # 解析公司名
            company = line.split('/')[0].replace('✓ ', '').strip()
            if '成功' in line:
                company_stats[company]['success'] += 1
                # 提取文件名
                file_part = line.split('→')[0].split('/')[-1].strip()
                company_stats[company]['files'].append(file_part)
            elif '错误' in line or '失败' in line:
                company_stats[company]['failed'] += 1
    
    total_success = sum(s['success'] for s in company_stats.values())
    total_failed = sum(s['failed'] for s in company_stats.values())
    
    # 生成格式化的报告摘要
    report_lines = [
        f"📧 绿联云每日发送报告 ({time.strftime('%Y-%m-%d %H:%M')})",
        "",
        f"📊 总计: 成功 {total_success} | 失败 {total_failed}",
        ""
    ]
    
    if company_stats:
        report_lines.append("📁 按公司统计:")
        report_lines.append("-" * 40)
        for company, stats in sorted(company_stats.items()):
            status = "✅" if stats['failed'] == 0 else "⚠️"
            report_lines.append(f"{status} {company}: {stats['success']} 个文件")
            for f in stats['files']:
                report_lines.append(f"   └─ {f}")
        report_lines.append("")
    else:
        report_lines.append("📭 今天没有文件需要发送")
        report_lines.append("")
    
    if total_failed > 0:
        report_lines.append("⚠️ 失败详情:")
        for line in result.split('\n'):
            if '✗ 错误' in line or '失败' in line:
                report_lines.append(f"  {line}")
        report_lines.append("")
    
    report_summary = '\n'.join(report_lines)
    
    # 保存报告到文件
    report_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'memory', f'nas_report_{time.strftime("%Y%m%d")}.txt')
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_summary)
    except:
        pass
    
    # 如果是报告模式，输出生成的报告内容（供调用者使用）
    if generate_report:
        print("\n" + "=" * 50)
        print(report_summary)
    
    # 每周六清理7天前的旧文件（可以在cron里设置）
    import datetime
    if datetime.datetime.now().weekday() == 5:  # 周六
        print("\n[周六清理任务]")
        for company_key in CLIENT_MAP:
            company_folder = os.path.join(NAS_FOLDER, company_key)
            if os.path.exists(company_folder):
                cleanup_result = cleanup_nas_folder(company_folder, days_old=7)
                print(f"{company_key}: {cleanup_result}")
