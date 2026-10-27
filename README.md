# cursor-session-backup

本机备份与恢复 [Cursor](https://cursor.com) 会话数据的图形界面工具（Windows）。

适用场景：偶尔彻底卸载并重装 Cursor 后，把本地聊天 / Agent 会话恢复回来。

## 功能

- **一键备份全部对话**：保存到备份根目录（默认 `C:\ZYL\backup\cursor-sessions_<时间戳>`）
- **历史列表选择恢复**：按时间/体积/版本列出备份，点选后一键恢复或删除
- **自动关停与重启**：恢复前可自动关闭 Cursor，成功后可选自动再启动
- **安全**：覆盖前挪到 `OLD_*`；默认跳过巨型 `state.vscdb.backup`
- **不做**：换号、重置机器码等无关能力

需求与验收标准见 [`docs/requirements/20261027-cursor-session-backup.md`](docs/requirements/20261027-cursor-session-backup.md)。

## 环境

- Windows 10/11
- Python 3.10+（仅用标准库 + 系统自带 `robocopy` / `tasklist`）

## 便携版（推荐）

已打好的无安装包：

`release\CursorSessionBackup.exe`（约 12MB，依赖已打进单文件，**无终端黑框**）

双击即可；或运行 `启动便携版.bat`。

重新打包：

```bat
pip install pyinstaller
python build_portable.py
```

## 开发启动

```bat
run_gui.bat
```

（优先启动 `release\CursorSessionBackup.exe`；否则用 `pythonw` 以免弹出控制台）

## 备份包含什么（默认）

| 内容 | 路径 |
|------|------|
| 全局状态库 | `%APPDATA%\Cursor\User\globalStorage`（含 `state.vscdb`，默认不含 `state.vscdb.backup`） |
| 工作区存储 | `%APPDATA%\Cursor\User\workspaceStorage` |
| Agent 转录 | `%USERPROFILE%\.cursor\projects` |
| 可选 | `settings.json` / `keybindings.json` |
| 可选 | `C:\ZYL\.cursor` 规则与 project-notes（默认不勾选） |

## 推荐流程

1. **卸载前**：打开本工具 → 确认备份根目录与选项 →「开始备份」→ 确认生成了 `README-恢复说明.txt` 与 `manifest.json`。
2. **重装后**：安装 Cursor → 先打开一次再完全退出 → 确认任务管理器无 Cursor 进程 → 本工具选中备份 →「开始恢复」。
3. 重新打开 Cursor，用**备份时相同的工程文件夹路径**打开项目。

## 风险说明

- `state.vscdb` 可能达数十 GB，请预留磁盘空间与时间。
- Cursor 大版本若变更私有存储格式，恢复后可能无法完全兼容；工具会校验备份中是否存在关键文件，但无法保证上游格式不变。
- 本工具只做本机文件拷贝；云端同步的对话仍依赖同一账号登录。

## 自检

```bat
python tests\test_self_check.py
```

## 许可证

MIT（见 [LICENSE](LICENSE)）
