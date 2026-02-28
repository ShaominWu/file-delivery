# File Delivery Skill - 工程文件自动交付

自动化将 Tekla/工程文件上传到 Google Drive 并发送给客户。

## 功能

- 监控本地文件夹（绿联云同步）
- 自动上传到 Google Drive（按客户隔离）
- 生成私密分享链接
- 发送英文邮件通知客户下载
- **自动清理：每周删除7天以上的云端文件，释放空间**

## 配置

### 1. 公司邮箱映射 (config/clients.json)

```json
{
  "MM": {
    "email": "bert@mmstructural.ca",
    "cc": "kyle@mmstructural.ca",
    "contact": "Bert",
    "folder": "MM"
  },
  "MIG": {
    "email": "SERGE@MIGSTEEL.COM",
    "contact": "Serge",
    "folder": "MIG"
  },
  "RITCHIE": {
    "email": "sdionne@ritchieswelding.ca",
    "contact": "Serge",
    "folder": "Ritchie"
  },
  "simcon": {
    "email": "david@simcon.ca",
    "contact": "David",
    "folder": "Simcon"
  },
  "olsonfab": {
    "email": "cglover@olsonfab.com",
    "contact": "Chris",
    "folder": "Olsonfab"
  },
  "carleton": {
    "email": "greg@carletoniron.com",
    "contact": "Greg",
    "folder": "Carleton"
  },
  "Shao": {
    "email": "wushaomin69@163.com",
    "contact": "Shaomin",
    "folder": "Shao"
  },
  "WW": {
    "email": "wwstrusteelengineering@gmail.com",
    "contact": "WangWei",
    "folder": "WW"
  },
  "KILMARNOCK": {
    "email": "ssharpe@kilmarnock.ca",
    "contact": "Shaun",
    "folder": "KILMARNOCK"
  }
}
```

### 2. 文件夹结构

```
C:\绿联云同步\
├── MM\                → Bert (CC: Kyle)
├── MIG\               → Serge
├── Ritchie\           → Serge
├── Simcon\            → David
├── Olsonfab\          → Chris
├── Carleton\          → Greg
├── Shao\              → Shaomin (自用备份)
├── WW\                → WangWei
└── KILMARNOCK\        → Shaun
```

## 使用

### 手动发送文件

```bash
# 扫描所有客户文件夹并发送
python3 tools/delivery_agent.py

# 处理指定客户
python3 tools/delivery_agent.py --client MM
```

### 自动运行（已配置定时任务）

| 时间 | 任务 | 说明 |
|:---|:---|:---|
| **每天 09:00** | 文件发送 | 扫描NAS → 上传Google Drive → 发送邮件 |
| **每周日 02:00** | **空间清理** | **删除7天以上文件，释放空间** |

### 手动清理 Google Drive

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

## 邮件模板

**发件人:** `wushaomin7777@gmail.com` (Gmail)

**主题:** `[Project Delivery] {Company} - Download Your Files`

**正文:**
```
Hey {Contact Name},

Your project files are ready for download.

Please click the link below to download your file:

📄 {filename}
🔗 {Google Drive link}

Note: This link is private and only accessible to you. 
Please download within 7 days.

After you download, the file will be automatically removed from our server.

Ferrum Drafting Team
```

## 工作流程

```
1. 放文件 → C:\绿联云同步\{客户文件夹}\
2. 自动检测 → 每天9点扫描
3. 上传云端 → Google Drive客户专属文件夹
4. 生成链接 → 私密分享链接
5. 发送邮件 → Gmail发送给客户
6. 本地归档 → 移动到"已发送"文件夹
7. 定期清理 → 每周日凌晨删除7天以上文件
```

## 技术细节

| 项目 | 配置 |
|:---|:---|
| **发件邮箱** | wushaomin7777@gmail.com (Gmail) |
| **SMTP** | smtp.gmail.com:465 (SSL) |
| **云存储** | Google Drive (客户文件夹隔离) |
| **本地同步** | 绿联云 NAS |
| **安全** | 私密链接 + 7天自动清理 |
| **定时** | Cron 自动运行 |

## 文件清单

```
skills/file-delivery/
├── SKILL.md                    # 本文件
├── README.md                   # 快速开始指南
├── run.sh                      # 快速入口脚本
├── config/
│   └── clients.json            # 9家公司配置
└── tools/
    ├── delivery_agent.py       # 主程序（上传+邮件）
    ├── nas_email_sender.py     # 邮件发送工具
    ├── cleanup_drive.py        # **云端清理工具**
    ├── token.pickle            # Google Drive授权
    └── client_secrets.json     # OAuth凭证
```

## 维护

- **新增客户**: 修改 `config/clients.json`
- **修改邮件**: 编辑 `tools/delivery_agent.py`
- **调整清理周期**: 修改 `cron/jobs.json`
- **查看日志**: 运行时的终端输出

## 限制

- Google Drive 免费版: **15GB** (自动清理管理空间)
- 单文件大小: 无限制 (通过Google Drive链接)
- 链接有效期: **7天** (之后自动删除)
- 邮件服务: Gmail (需要应用专用密码)

## 备份

完整备份: `file-delivery-backup-YYYYMMDD-HHMM.tar.gz`
- 包含: 配置、脚本、授权凭证
- 位置: `~/DOCUMENTS/` 和 `~/.openclaw/skills/`
- 恢复: 解压到 `~/.openclaw/` 即可
