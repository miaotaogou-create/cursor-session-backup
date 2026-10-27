# cursor-session-backup

本机备份与恢复 [Cursor](https://cursor.com) 会话数据的图形界面工具。

适用场景：偶尔彻底卸载并重装 Cursor 后，希望把本地聊天 / Agent 会话恢复回来，而不必手敲脚本路径。

## 功能（规划）

- **备份**：把本机会话相关目录打包到指定备份根目录（默认 `C:\ZYL\backup\cursor-sessions_<时间戳>`）
- **恢复**：从已有备份覆盖回 Cursor 数据目录（恢复前须完全退出 Cursor）
- **安全提示**：检测 Cursor 进程、显示体积与耗时风险、默认跳过巨型 `state.vscdb.backup`

详细需求与验收标准见 [`docs/requirements/20261027-cursor-session-backup.md`](docs/requirements/20261027-cursor-session-backup.md)。

## 当前状态

仓库已建立，需求已入库。图形界面与命令行实现尚未交付（见需求文档「已确认 / 待确认」）。

本机已有可参考的脚本（不在本仓库内）：

- `C:\ZYL\scripts\backup-cursor-chats.ps1`
- `C:\ZYL\scripts\restore-cursor-chats.ps1`

实现阶段将把其中稳定逻辑收敛进本仓库的 `src/`，并加上 GUI。

## 运行环境（目标）

- Windows 10/11
- Python 3.10+（优先仅用标准库做 GUI，避免额外依赖）

## 重要说明

- 会话主库 `state.vscdb` 体积可能达数十 GB，备份前请确认磁盘空间。
- 恢复后请用**与备份时相同的工程路径**打开项目，否则会话可能无法自动关联。
- 本工具只做本机文件拷贝；云端同步的对话仍依赖同一 Cursor 账号登录。

## 许可证

MIT（见 [LICENSE](LICENSE)）
