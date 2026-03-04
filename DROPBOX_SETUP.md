# Dropbox API Token 配置说明

## 获取 Dropbox API Token

1. 访问 Dropbox App Console: https://www.dropbox.com/developers/apps
2. 点击 "Create app"
3. 选择:
   - Scoped access
   - Full Dropbox (或 App folder，推荐 Full Dropbox)
4. 给 app 起个名字，比如 "FerrumFileDelivery"
5. 在 Permissions 标签页，勾选以下权限:
   - `files.content.write`
   - `files.content.read`
   - `sharing.write`
   - `sharing.read`
6. 点击 "Submit"
7. 在 Settings 标签页，找到 "Generated access token"
8. 点击 "Generate" 复制 token

## 配置 Token

**方法一：环境变量（推荐）**
```bash
export DROPBOX_ACCESS_TOKEN="your_token_here"
```

添加到 `~/.zshrc` 或 `~/.bash_profile`:
```bash
echo 'export DROPBOX_ACCESS_TOKEN="your_token_here"' >> ~/.zshrc
source ~/.zshrc
```

**方法二：配置文件**
在 `file-delivery/config/` 目录下创建 `dropbox_token.txt`:
```bash
echo "your_token_here" > /Users/bear/.openclaw/workspace/file-delivery/config/dropbox_token.txt
```

## 安装依赖

```bash
cd /Users/bear/.openclaw/workspace/file-delivery
source venv/bin/activate
pip install dropbox
```

## 测试

```bash
cd /Users/bear/.openclaw/workspace/file-delivery/tools
python dropbox_uploader.py /path/to/test/file.zip
```

## 邮件效果

客户将收到包含两个下载链接的邮件:
```
Download links:
🔗 Google Drive: https://drive.google.com/...
🔗 Dropbox: https://www.dropbox.com/...
```
