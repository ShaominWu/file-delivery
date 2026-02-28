# Ferrum File Delivery Skill

工程文件自动交付系统 - Tekla/钢结构图纸自动化发送

## 快速开始

```bash
# 运行完整流程（扫描所有客户文件夹）
./run.sh

# 处理指定客户
./run.sh --client MM

# 检查待发送文件状态
./run.sh --status

# 清理已下载的云端文件
./run.sh --cleanup
```

## 工作流程

1. **绿联云同步** ← 中国上传文件
2. **本地检测** ← 扫描 `C:\绿联云同步\各客户文件夹`
3. **Google Drive 上传** ← 按客户隔离存储
4. **生成分享链接** ← 私密链接，仅客户可见
5. **发送邮件** → 客户收到下载通知
6. **归档本地文件** → 移动到 `已发送` 文件夹
7. **定期清理** → 每周自动删除7天以上云端文件

## 客户列表（9家）

| 文件夹 | 联系人 | 邮箱 |
|:---|:---|:---|
| MM/ | Bert | bert@mmstructural.ca (CC: Kyle) |
| MIG/ | Serge | SERGE@MIGSTEEL.COM |
| Ritchie/ | Serge | sdionne@ritchieswelding.ca |
| Simcon/ | David | david@simcon.ca |
| Olsonfab/ | Chris | cglover@olsonfab.com |
| Carleton/ | Greg | greg@carletoniron.com |
| Shao/ | Shaomin | wushaomin69@163.com |
| WW/ | WangWei | wwstrusteelengineering@gmail.com |
| KILMARNOCK/ | Shaun | ssharpe@kilmarnock.ca |

## 清理 Google Drive 空间

```bash
cd tools/

# 模拟清理（查看会删哪些文件）
python3 cleanup_drive.py --days 7 --dry-run

# 真正清理（7天以上文件）
python3 cleanup_drive.py --days 7

# 清理指定客户
python3 cleanup_drive.py --client MM --days 7
```

## 自动化定时任务

| 时间 | 任务 | 说明 |
|:---|:---|:---|
| **每天 09:00** | 文件发送 | 扫描→上传→发邮件→归档 |
| **每周日 02:00** | 云端清理 | 删除7天以上文件，释放空间 |

## 配置

编辑 `config/clients.json` 添加新客户

## 邮件服务

- **发件人**: wushaomin7777@gmail.com (Gmail)
- **SMTP**: smtp.gmail.com:465
- **安全**: Google Drive私密链接，7天自动清理
