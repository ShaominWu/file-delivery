# 🫘 小豆豆 File Delivery Skill - 工程文件自动交付

> "有事叫我，没事我不吵你~"

小豆豆是你的专属文件交付助手，自动化将 Tekla/工程文件上传到 Google Drive 并发送给客户。

---

## ✨ 核心功能

| 功能 | 说明 |
|------|------|
| 🫘 **小豆豆助手** | 活泼可靠的自动化代理 |
| 📁 **智能监控** | 每天 8点、10点自动扫描绿联云同步文件夹 |
| ☁️ **自动上传** | 上传到 Google Drive（按客户隔离存储） |
| 🔗 **生成链接** | 私密分享链接，仅客户可见 |
| 📧 **智能邮件** | 自动提取项目名称（去数字）作为邮件主题 |
| 🧹 **自动清理** | 每天凌晨 1点清理7天以上云端文件 |
| 📂 **本地归档** | 已发送文件自动移动到"已发送"文件夹 |

---

## 🏗️ 系统架构

### Mac 适配配置

```
/Users/bear/Shared/绿联云同步/          ← 绿联云同步路径
├── MM/                                  → Bert (CC: Kyle)
├── MIG/                                 → Serge
├── Ritchie/                             → Serge
├── Simcon/                              → David
├── Olsonfab/                            → Chris (CC: 另一人)
├── Carleton/                            → Greg
├── Shao/                                → Shaomin (自用)
├── WW/                                  → WangWei
├── KILMARNOCK/                          → Shaun
├── LEMIRE/                              → Bob
├── ALEXANDER/                           → Alex
├── JT/                                  → JT
├── LEE/                                 → Leo
└── 各客户文件夹/已发送/                  ← 已发送文件归档
```

### Python 虚拟环境

```
file-delivery/
├── venv/                          ← Python 虚拟环境
│   └── bin/python3               ← 隔离的 Python 运行环境
```

---

## 👥 客户配置 (config/clients.json)

```json
{
  "clients": {
    "MM": {
      "email": "bert@mmstructural.ca",
      "cc": "kyle@mmstructural.ca",
      "contact": "Bert",
      "name": "M&M Structural",
      "folder": "MM"
    },
    "MIG": {
      "email": "SERGE@MIGSTEEL.COM",
      "contact": "Serge",
      "name": "MIG Steel",
      "folder": "MIG"
    },
    "RITCHIE": {
      "email": "sdionne@ritchieswelding.ca",
      "contact": "Serge",
      "name": "Ritchie Welding",
      "folder": "Ritchie"
    },
    "simcon": {
      "email": "dscott.simcon@live.ca",
      "contact": "David",
      "name": "Simcon",
      "folder": "Simcon"
    },
    "olsonfab": {
      "email": "cglover@olsonfab.com",
      "cc": "cmatheson@olsonfab.com",
      "contact": "Chris",
      "name": "Olson Fabrication",
      "folder": "Olsonfab"
    },
    "carleton": {
      "email": "greg@carletoniron.com",
      "contact": "Greg",
      "name": "Carleton Iron",
      "folder": "Carleton"
    },
    "Shao": {
      "email": "wushaomin69@163.com",
      "contact": "Shaomin",
      "name": "Shaomin Wu",
      "folder": "Shao",
      "note": "自用备份"
    },
    "WW": {
      "email": "wwstrusteelengineering@gmail.com",
      "contact": "WangWei",
      "name": "WW",
      "folder": "WW"
    },
    "KILMARNOCK": {
      "email": "ssharpe@kilmarnock.ca",
      "contact": "Shaun",
      "name": "Kilmarnock",
      "folder": "KILMARNOCK"
    },
    "LEMIRE": {
      "email": "bob@lemire.on.ca",
      "contact": "Bob",
      "name": "Lemire",
      "folder": "Lemire"
    },
    "ALEXANDER": {
      "email": "alex@egesolutions.com",
      "contact": "Alex",
      "name": "AlexEG",
      "folder": "Alexander"
    },
    "JT": {
      "email": "jt@morissetconstruction.com",
      "contact": "JT",
      "name": "JT",
      "folder": "JT",
      "signature": "Western Valley Design"
    },
    "LEE": {
      "email": "leodetailing@163.com",
      "contact": "Leo",
      "name": "Lee Detailing",
      "folder": "LEE"
    }
  },
  "settings": {
    "local_sync_folder": "/Users/bear/Shared/绿联云同步",
    "google_drive_folder": "客户文件交付",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 465,
    "sender_email": "wushaomin7777@gmail.com",
    "link_expiry_days": 7
  }
}
```

---

## 🫘 召唤小豆豆

### 手动使用

```bash
cd /Users/bear/.openclaw/workspace/file-delivery

# 让小豆豆检查状态
./xiaodoudou.sh --status

# 小豆豆运行完整交付流程
./xiaodoudou.sh --run

# 小豆豆处理指定客户
./xiaodoudou.sh --client MM

# 小豆豆清理云端旧文件
./xiaodoudou.sh --cleanup
```

### 自动定时任务（加拿大东部时间）

| 时间 | 任务 | 说明 |
|:---|:---|:---|
| **每天 08:00** ☕ | 文件发送 | 第一次扫描所有客户文件夹 |
| **每天 10:00** 🌞 | 文件发送 | 第二次扫描（防漏网之鱼） |
| **每天 01:00** 🌙 | 云端清理 | 清理7天以上文件，释放空间 |

安装定时任务：
```bash
crontab crontab.txt
```

---

## 🧠 智能项目名称提取

### 提取规则

小豆豆会自动从文件名中提取项目名称作为邮件主题：

| 原文件名 | 提取的项目名称 | 邮件主题 |
|---------|--------------|---------|
| `Fernbank North Elementary School.zip` | `FernbankNorthElementarySchool` | `[Project Delivery] FernbankNorthElementarySchool - Download Your Files` |
| `Toronto City Hall Renovation.dwg` | `TorontoCityHallRenovation` | `[Project Delivery] TorontoCityHallRenovation - Download Your Files` |
| `John Smith Residence.pdf` | `JohnSmithResidence` | `[Project Delivery] JohnSmithResidence - Download Your Files` |
| `Steel Beam 200x300 Type A.dwg` | `SteelBeamType` | `[Project Delivery] SteelBeamType - Download Your Files` |

### 过滤逻辑

1. **删除所有数字** - `M16` → `M`, `200x300` → `x`
2. **删除无意义短词** - `p`, `h`, `v`, `of`, `in`, `at`, `to`
3. **保留3个字母以上的词** - `Fernbank`, `Elementary`, `School`
4. **删除空格** - 连接成驼峰式

---

## 📧 邮件模板

**发件人:** `wushaomin7777@gmail.com` (Gmail)

**主题:** 
```
[Project Delivery] {ProjectName} - Download Your Files
```

**正文:**
```
Hey {Contact Name},

Your project files for {ProjectName} are ready for download.

Please click the link(s) below to download your files:

📄 {filename}
🔗 {Google Drive link}

Note: These links are private and only accessible to you. 
Please download within 7 days.

After you download, the files will be automatically removed from our server.

Ferrum Drafting Team
```

---

## 🧹 云端清理

### 手动清理

```bash
# 查看哪些文件会被删除（模拟模式）
python3 tools/cleanup_drive.py --days 7 --dry-run

# 清理所有客户的旧文件（7天以上）
python3 tools/cleanup_drive.py --days 7

# 只清理指定客户（如MM）
python3 tools/cleanup_drive.py --client MM --days 7

# 清理3天以上的文件（更严格）
python3 tools/cleanup_drive.py --days 3
```

### 自动清理

每天凌晨 1 点自动运行，删除7天以上的云端文件。

---

## 📁 文件清单

```
file-delivery/
├── SKILL.md                      # 本文件（完整方案）
├── README.md                     # 快速开始指南
├── XIAODOUDOU.md                 # 小豆豆身份档案
├── MAC_SETUP.md                  # Mac 配置指南
├── OFFICE_AUTOMA.md              # 办公自动化文档
├── run.sh                        # 基础运行脚本
├── xiaodoudou.sh                 # 🫘 小豆豆主程序
├── office-automa.sh              # 办公自动化入口
├── crontab.txt                   # 定时任务配置
├── config/
│   └── clients.json              # 13家公司配置
├── tools/
│   ├── delivery_agent.py         # 主程序（上传+邮件+智能提取）
│   ├── nas_email_sender.py       # 邮件发送工具
│   ├── cleanup_drive.py          # 云端清理工具
│   ├── first_auth.py             # 首次授权脚本
│   ├── token.pickle              # Google Drive授权（自动生成）
│   └── client_secrets.json       # OAuth凭证（需手动放置）
├── venv/                         # Python虚拟环境
└── logs/                         # 运行日志
    ├── delivery-YYYYMMDD-0800.log
    ├── delivery-YYYYMMDD-1000.log
    └── cleanup-YYYYMMDD.log
```

---

## 🔧 技术细节

| 项目 | 配置 |
|:---|:---|
| **操作系统** | macOS (Apple Silicon) |
| **Python** | 3.x (虚拟环境) |
| **发件邮箱** | wushaomin7777@gmail.com (Gmail) |
| **SMTP** | smtp.gmail.com:465 (SSL) |
| **云存储** | Google Drive (客户文件夹隔离) |
| **本地同步** | 绿联云 NAS |
| **定时任务** | Cron (加拿大东部时间) |
| **安全** | 私密链接 + 7天自动清理 |

---

## 🚀 首次设置

### 1. 安装依赖

```bash
cd file-delivery
python3 -m venv venv
source venv/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 2. 配置 Google Drive 授权

1. 确保 `tools/client_secrets.json` 存在
2. 运行授权脚本：
```bash
source venv/bin/activate
python3 tools/first_auth.py
```
3. 浏览器登录 Google 账号授权
4. `token.pickle` 会自动生成

### 3. 设置绿联云同步

将绿联云客户端的同步路径设为：
```
/Users/bear/Shared/绿联云同步
```

### 4. 安装定时任务

```bash
crontab crontab.txt
```

---

## 📝 维护指南

### 新增客户

编辑 `config/clients.json`，添加新客户配置：
```json
"NEWCLIENT": {
  "email": "client@example.com",
  "contact": "ContactName",
  "name": "Company Name",
  "folder": "NewClient"
}
```

然后创建对应文件夹：
```bash
mkdir "/Users/bear/Shared/绿联云同步/NewClient"
```

### 修改邮件内容

编辑 `tools/delivery_agent.py` 中的 `send_client_email_with_link()` 函数

### 调整定时任务

编辑 `crontab.txt`，然后重新加载：
```bash
crontab crontab.txt
```

### 查看日志

```bash
ls -la logs/
cat logs/delivery-20260301-0800.log
```

---

## ⚠️ 限制与注意事项

- **Google Drive 免费版**: 15GB (自动清理管理空间)
- **单文件大小**: 无限制 (通过 Google Drive 链接)
- **链接有效期**: 7天 (之后自动删除)
- **邮件服务**: Gmail (需要应用专用密码)
- **系统文件**: 自动过滤 `.DS_Store` 等 macOS 系统文件

---

## 💾 备份

完整备份命令：
```bash
tar -czf file-delivery-backup-$(date +%Y%m%d-%H%M).tar.gz \
  --exclude='venv' \
  --exclude='logs' \
  --exclude='*.pyc' \
  file-delivery/
```

**排除项**:
- `venv/` - 虚拟环境可重新创建
- `logs/` - 日志文件不需要备份
- `*.pyc` - Python 缓存文件

**重要文件** (必须备份):
- `config/clients.json`
- `tools/client_secrets.json`
- `tools/token.pickle`

---

## 🫘 小豆豆说

> "每天早上 8 点和 10 点我会检查文件，
> 凌晨 1 点我会悄悄清理云端空间。
> 有事叫我，没事我不吵你~"

---

*版本: 2026.03.01 | 作者: Shaomin Wu | 助手: 小豆豆 🫘*
