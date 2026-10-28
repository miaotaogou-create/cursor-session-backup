# cursor-session-backup

本机备份与恢复 [Cursor](https://cursor.com) 会话数据的图形界面工具（Windows）。

适用场景：偶尔彻底卸载并重装 Cursor 后，把本地聊天 / Agent 会话恢复回来。

## 功能（刻意做少）

- **一键备份全部对话**
- **历史列表**：时间 / 体积 / 版本；**一键恢复**、**删除**
- 恢复时自动关 Cursor，成功后自动再开；覆盖前挪到 `OLD_*`
- **不做**：换号、重置机器码、一堆高级开关

需求与验收标准见 [`docs/requirements/20261027-cursor-session-backup.md`](docs/requirements/20261027-cursor-session-backup.md)。

## 环境

- Windows 10/11（需已安装 **Microsoft Edge WebView2 运行时**；Win11 一般自带）
- 便携 exe：无需本机 Python / Node
- 从源码跑：Python 3.10+，`pip install -r requirements.txt`；界面为 React（`ui/`）经 `pywebview` 承载；拷贝仍用系统 `robocopy` / `tasklist`

## 便携版（推荐）

真正的**单文件 exe**（带应用图标，换电脑也可双击运行，无终端黑框、无需 bat）。

**下载发布包**：GitHub Releases → [v0.6.2](https://github.com/miaotaogou-create/cursor-session-backup/releases/tag/v0.6.2)（附件 `CursorSessionBackup.exe`）。

本机构建产物路径：`release\CursorSessionBackup.exe`。直接双击即可；首次启动会稍慢（自解压）。目标机需已装 WebView2（Win11 一般自带）。

重新打包：

```bat
pip install -r requirements.txt pyinstaller
pip install pillow
python assets\generate_icon.py
npm --prefix ui install
python build_portable.py
```

（`build_portable.py` 会先 `npm run build` 再打 exe；`assets\app.ico` 会嵌进 exe。）

## 开发启动

先构建一次界面，再启动：

```bat
npm --prefix ui install
npm --prefix ui run build
pythonw run_gui.py
```

日常使用请双击 `release\CursorSessionBackup.exe`，不要依赖 `run_gui.bat`。

仅改 UI 时可 `npm --prefix ui run dev` 在浏览器预览（无桌面桥接时不会真正备份）。

## 备份包含什么（默认）

| 内容 | 路径 |
|------|------|
| 全局状态库 | `%APPDATA%\Cursor\User\globalStorage`（含 `state.vscdb`，默认不含 `state.vscdb.backup`） |
| 工作区存储 | `%APPDATA%\Cursor\User\workspaceStorage` |
| Agent 转录 | `%USERPROFILE%\.cursor\projects` |
| 可选 | `settings.json` / `keybindings.json` |
| 可选 | `C:\ZYL\.cursor` 规则与 project-notes（默认不勾选） |

## 推荐流程

1. **卸载前**：打开本工具 → 确认备份根目录 →「一键备份全部对话」→ 确认生成了说明与元数据。
2. **重装后**：安装 Cursor → 先打开一次再完全退出 → 确认任务管理器无 Cursor 进程 → 本工具选中备份 →「一键恢复」。
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

MIT（见 [LICENSE]）
