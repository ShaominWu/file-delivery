#!/usr/bin/env python3
"""
首次授权脚本 - 生成 token.pickle
"""
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file'
]

script_dir = os.path.dirname(os.path.abspath(__file__))
secrets_path = os.path.join(script_dir, 'client_secrets.json')
token_path = os.path.join(script_dir, 'token.pickle')

print("🔐 Google Drive 授权")
print("=" * 50)

if not os.path.exists(secrets_path):
    print(f"❌ 找不到 {secrets_path}")
    exit(1)

print(f"✅ 找到凭证文件: {secrets_path}")
print("\n正在启动授权流程...")
print("浏览器将会打开，请登录你的 Google 账号并授权\n")

flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
creds = flow.run_local_server(port=0, open_browser=True)

with open(token_path, 'wb') as token:
    pickle.dump(creds, token)

print(f"\n✅ 授权成功！")
print(f"📝 Token 已保存到: {token_path}")
print("\n现在可以运行 ./run.sh 了")
