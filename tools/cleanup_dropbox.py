#!/usr/bin/env python3
"""
Dropbox 清理工具
删除客户下载后的文件，释放空间
"""

import os
import sys
import json
from datetime import datetime, timedelta

# 导入 Dropbox 上传模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dropbox_uploader import DropboxUploader

def list_files_in_folder(uploader, folder_path):
    """列出 Dropbox 文件夹中的所有文件"""
    files = []
    
    try:
        result = uploader.dbx.files_list_folder(folder_path, recursive=True)
        
        for entry in result.entries:
            if isinstance(entry, type(uploader.dbx.files_list_folder(folder_path).entries[0])):
                # 检查是否是文件（不是文件夹）
                if hasattr(entry, 'content_hash'):  # 只有文件有 content_hash
                    files.append({
                        'path': entry.path_display,
                        'name': entry.name,
                        'client_modified': entry.client_modified,
                        'server_modified': entry.server_modified,
                        'size': entry.size
                    })
        
        # 处理分页
        while result.has_more:
            result = uploader.dbx.files_list_folder_continue(result.cursor)
            for entry in result.entries:
                if hasattr(entry, 'content_hash'):
                    files.append({
                        'path': entry.path_display,
                        'name': entry.name,
                        'client_modified': entry.client_modified,
                        'server_modified': entry.server_modified,
                        'size': entry.size
                    })
    
    except Exception as e:
        print(f"❌ 列出文件时出错: {e}")
    
    return files

def delete_file(uploader, file_path):
    """删除 Dropbox 上的文件"""
    try:
        uploader.dbx.files_delete_v2(file_path)
        return True
    except Exception as e:
        print(f"❌ 删除文件失败: {e}")
        return False

def cleanup_client_files(uploader, client_name, days_old=7, dry_run=False):
    """清理指定客户的旧文件"""
    folder_path = f"/客户文件交付/{client_name}"
    
    print(f"\n📁 清理客户: {client_name}")
    
    # 列出文件
    files = list_files_in_folder(uploader, folder_path)
    if not files:
        print(f"  ℹ️ 没有文件需要清理")
        return 0
    
    print(f"  找到 {len(files)} 个文件")
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    deleted_count = 0
    total_size = 0
    
    for file in files:
        file_path = file['path']
        file_name = file['name']
        # Dropbox 返回的是 UTC 时间
        modified_time = file['server_modified'].replace(tzinfo=None)
        file_size = file['size']
        
        # 检查是否超过保留天数
        if modified_time < cutoff_date:
            print(f"  🗑️  {file_name} (修改于 {modified_time.strftime('%Y-%m-%d')})")
            
            if not dry_run:
                if delete_file(uploader, file_path):
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
            print(f"  ⏳ {file_name} (保留，修改于 {modified_time.strftime('%Y-%m-%d')})")
    
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
    
    # 初始化 Dropbox
    uploader = DropboxUploader()
    if not uploader.is_authenticated():
        print("❌ Dropbox 未认证，请检查 DROPBOX_ACCESS_TOKEN")
        return
    
    print("✅ Dropbox 连接成功\n")
    
    print("=" * 60)
    print(f"🧹 Dropbox 清理 (保留 {days_old} 天内文件)")
    if dry_run:
        print("📋 模拟模式 (不会真正删除)")
    print("=" * 60)
    
    total_deleted = 0
    
    if specific_client:
        # 清理指定客户
        if specific_client in clients:
            total_deleted += cleanup_client_files(uploader, specific_client, days_old, dry_run)
        else:
            print(f"❌ 未知客户: {specific_client}")
    else:
        # 清理所有客户
        for client_key in clients:
            total_deleted += cleanup_client_files(uploader, client_key, days_old, dry_run)
    
    print("\n" + "=" * 60)
    print(f"✨ 清理完成，共删除 {total_deleted} 个文件")
    print("=" * 60)

# ================= 主程序 =================
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='清理 Dropbox 上的旧文件')
    parser.add_argument('--days', type=int, default=7, help='保留天数（默认7天）')
    parser.add_argument('--dry-run', action='store_true', help='模拟模式，不真正删除')
    parser.add_argument('--client', type=str, help='指定客户名称（如MM、MIG等）')
    
    args = parser.parse_args()
    
    cleanup_all_clients(
        days_old=args.days,
        dry_run=args.dry_run,
        specific_client=args.client
    )
