# 🫘 小豆豆 (Xiaodoudou) - 办公自动化助手

> "有事叫我，没事我不吵你~"

小豆豆是你的专属文件交付助手，活泼、细心、可靠，每天早上帮你检查文件、发送给客户，凌晨悄悄清理云端空间。

## 功能

- **自动扫描** - 每天检查客户文件夹中的新文件
- **自动上传** - 上传到 Google Drive 并生成分享链接
- **自动通知** - 发送邮件通知客户下载
- **自动归档** - 本地文件移动到"已发送"文件夹
- **定期清理** - 每周清理7天以上的云端文件

## 关于小豆豆 🫘

- **性格**: 活泼、细心、可靠、话不多但做事利索
- **工作时间**: 每天早上 8:00、10:00 和凌晨 1:00
- **特长**: 自动扫描文件、上传到 Google Drive、发送邮件通知客户

## 快速开始

### 1. 安装定时任务

```bash
cd /Users/bear/.openclaw/workspace/file-delivery
crontab crontab.txt
```

### 2. 召唤小豆豆

```bash
# 让小豆豆检查状态
./xiaodoudou.sh --status

# 小豆豆运行完整交付流程
./xiaodoudou.sh --run

# 小豆豆处理指定客户
./xiaodoudou.sh --client MM

# 小豆豆清理云端旧文件
./xiaodoudou.sh --cleanup
```

## 客户列表

| 客户 | 文件夹 | 联系人 | 邮箱 |
|------|--------|--------|------|
| MM | MM/ | Bert | bert@mmstructural.ca |
| MIG | MIG/ | Serge | SERGE@MIGSTEEL.COM |
| RITCHIE | Ritchie/ | Serge | sdionne@ritchieswelding.ca |
| simcon | Simcon/ | David | dscott.simcon@live.ca |
| olsonfab | Olsonfab/ | Chris | cglover@olsonfab.com |
| carleton | Carleton/ | Greg | greg@carletoniron.com |
| Shao | Shao/ | Shaomin | wushaomin69@163.com |
| WW | WW/ | WangWei | wwstrusteelengineering@gmail.com |
| KILMARNOCK | KILMARNOCK/ | Shaun | ssharpe@kilmarnock.ca |
| LEMIRE | Lemire/ | Bob | bob@lemire.on.ca |
| ALEXANDER | Alexander/ | Alex | alex@egesolutions.com |
| JT | JT/ | JT | jt@morissetconstruction.com |
| LEE | LEE/ | Leo | leodetailing@163.com |

## 文件夹结构

```
/Users/bear/Shared/绿联云同步/
├── MM/
│   ├── file1.pdf
│   ├── file2.dwg
│   └── 已发送/          ← 已发送的文件自动移到这里
├── MIG/
├── Ritchie/
└── ... (其他客户)
```

## 自动任务时间表（加拿大东部时间）

| 时间 | 任务 | 说明 |
|------|------|------|
| 每天 08:00 | 扫描+发送 | 第一次检查所有客户文件夹 |
| 每天 10:00 | 扫描+发送 | 第二次检查所有客户文件夹 |
| 每天 01:00 | 云端清理 | 删除7天以上的云端文件 |

## 日志

日志保存在 `logs/` 文件夹：
- `delivery-YYYYMMDD.log` - 每日发送日志
- `cleanup-YYYYMMDD.log` - 清理日志

## 配置

客户信息在 `config/clients.json` 中配置。

需要准备：
1. `tools/client_secrets.json` - Google OAuth 凭证
2. `tools/token.pickle` - 首次运行时自动生成

## 邮件

- **发件人**: wushaomin7777@gmail.com
- **SMTP**: smtp.gmail.com:465
- **安全**: Google Drive 私密链接
