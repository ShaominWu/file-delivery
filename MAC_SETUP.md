# Mac 运行配置指南

## 已完成的修改

### 1. 路径修改
- `config/clients.json`: 本地同步文件夹路径改为 `/Users/bear/Shared/绿联云同步`
- `tools/nas_email_sender.py`: NAS 文件夹路径改为 Mac 路径

### 2. Python 虚拟环境
- 已创建 `venv/` 虚拟环境
- 已安装 Google API 依赖包

### 3. 运行方式
使用 `./run.sh` 即可自动调用虚拟环境中的 Python

## 首次运行前需要准备的文件

### client_secrets.json
需要从 Google Cloud Console 下载 OAuth 2.0 凭证：
1. 访问 https://console.cloud.google.com/
2. 创建一个项目（或选择现有项目）
3. 启用 Google Drive API
4. 创建 OAuth 2.0 凭证（桌面应用类型）
5. 下载 JSON 文件，重命名为 `client_secrets.json`
6. 放入 `tools/` 文件夹

### token.pickle
首次运行 `delivery_agent.py` 时会自动生成：
1. 运行 `./run.sh`
2. 浏览器会弹出 Google 授权页面
3. 登录并授权后，token.pickle 会自动保存到 tools/ 文件夹

## 文件夹结构

```
/Users/bear/Shared/绿联云同步/
├── MM/                → Bert (CC: Kyle)
├── MIG/               → Serge
├── Ritchie/           → Serge
├── Simcon/            → David
├── Olsonfab/          → Chris
├── Carleton/          → Greg
├── Shao/              → Shaomin (自用备份)
├── WW/                → WangWei
├── KILMARNOCK/        → Shaun
├── Lemire/            → Bob
├── Alexander/         → Alex
├── JT/                → JT
└── LEE/               → Leo
```

## 使用方法

```bash
cd file-delivery

# 扫描所有客户文件夹
./run.sh

# 处理指定客户
./run.sh --client MM

# 清理云端文件
./run.sh --cleanup
```

## 注意事项

1. **绿联云同步**: 需要在 Mac 上安装绿联云客户端，并将同步文件夹设置为 `/Users/bear/Shared/绿联云同步`

2. **Gmail 密码**: 程序中使用了 Gmail 应用专用密码 `dolrcqvngwtvwsao`，请确认此密码仍然有效

3. **Google Drive 文件夹**: 首次运行时会自动创建 "客户文件交付" 文件夹

## 客户配置

如需添加/修改客户，编辑 `config/clients.json`
