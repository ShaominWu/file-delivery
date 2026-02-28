#!/usr/bin/env python3
"""
Google Drive 清理工具
删除客户下载后的文件，释放空间
"""

import os
import sys
import pickle
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 加载 Google Drive 授权
def get_credentials():
    """从token.pickle加载凭证"""
    token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
    if not os.path.exists(token_path):
        print(f"❌ 找不到 {token_path}")
        return None
    
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
    return creds

def list_files_in_folder(service, folder_id):
    """列出文件夹中的所有文件"""
    files = []
    page_token = None
    
    while True:
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='nextPageToken, files(id, name, createdTime, modifiedTime, size)',
                pageToken=page_token
            ).execute()
            
            files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            
            if not page_token:
                break
        except HttpError as e:
            print(f"❌ 列出文件时出错: {e}")
            break
    
    return files

def delete_file(service, file_id):
    """删除 Google Drive 上的文件"""
    try:
        service.files().delete(fileId=file_id).execute()
        return True
    except HttpError as e:
        print(f"❌ 删除文件失败: {e}")
        return False

def get_folder_id(service, folder_name, parent_id=None):
    """获取文件夹ID"""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    try:
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        
        if items:
            return items[0]['id']
    except HttpError as e:
        print(f"❌ 查找文件夹时出错: {e}")
    
    return None

def cleanup_client_files(service, client_name, days_old=7, dry_run=False):
    """清理指定客户的旧文件"""
    print(f"\n📁 清理客户: {client_name}")
    
    # 获取主文件夹ID
    main_folder_id = get_folder_id(service, "客户文件交付")
    if not main_folder_id:
        print(f"  ❌ 找不到主文件夹")
        return 0
    
    # 获取客户文件夹ID
    client_folder_id = get_folder_id(service, client_name, main_folder_id)
    if not client_folder_id:
        print(f"  ⚠️ 找不到客户文件夹 {client_name}")
        return 0
    
    # 列出文件
    files = list_files_in_folder(service, client_folder_id)
    if not files:
        print(f"  ℹ️ 没有文件需要清理")
        return 0
    
    print(f"  找到 {len(files)} 个文件")
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    deleted_count = 0
    total_size = 0
    
    for file in files:
        file_id = file['id']
        file_name = file['name']
        created_time = datetime.fromisoformat(file['createdTime'].replace('Z', '+00:00')).replace(tzinfo=None)
        file_size = int(file.get('size', 0))
        
        # 检查是否超过保留天数
        if created_time < cutoff_date:
            print(f"  🗑️  {file_name} (创建于 {created_time.strftime('%Y-%m-%d')})")
            
            if not dry_run:
                if delete_file(service, file_id):
                    deleted_count += 1
                    total_size += file_size
                    print(f"     ✅ 已删除")
                else:
                    print(f"     ❌ 删除失败")
            else:
                print(f"     [模拟删除]")
                deleted_count += 1
                total_size += file_size
        else:
            print(f"  ⏳ {file_name} (保留，创建于 {created_time.strftime('%Y-%m-%d')})")
    
    size_mb = total_size / (1024 * 1024)
    print(f"  📊 清理完成: {deleted_count} 个文件, 释放 {size_mb:.1f} MB")
    
    return deleted_count

def cleanup_all_clients(days_old=7, dry_run=False, specific_client=None):
    """清理所有客户的旧文件"""
    # 加载客户配置
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'clients.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        clients = config.get('clients', {})
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")
        return
    
    # 获取 Google Drive 授权
    creds = get_credentials()
    if not creds:
        print("❌ Google Drive 授权失败")
        return
    
    service = build('drive', 'v3', credentials=creds)
    print("✅ Google Drive 连接成功\n")
    
    print("=" * 60)
    print(f"🧹 Google Drive 清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)
    
    total_deleted = 0
    
    if specific_client:
        # 清理指定客户
        if specific_client in clients:
            total_deleted += cleanup_client_files(service, specific_client, days_old, dry_run)
        else:
            print(f"❌ 未知客户: {specific_client}")
    else:
        # 清理所有客户
        for client_key in clients:
            total_deleted += cleanup_client_files(service, client_key, days_old, dry_run)
    
    print("\n" + "=" * 60)
    print(f"✨ 清理完成，共删除 {total_deleted} 个文件")
    print("=" * 60)

# ================= 主程序 =================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='清理 Google Drive 上的旧文件')
    parser.add_argument('--days', type=int, default=7, help='保留天数（默认7天）')
    parser.add_argument('--dry-run', action='store_true', help='模拟模式，不真正删除')
    parser.add_argument('--client', type=str, help='指定客户名称（如MM、MIG等）')
    
    args = parser.parse_args()
    
    cleanup_all_clients(
        days_old=args.days,
        dry_run=args.dry_run,
        specific_client=args.client
    )
