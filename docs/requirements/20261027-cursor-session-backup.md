# Cursor 会话本机备份 / 恢复（图形界面）

- 状态：已实现（首版 GUI + 核心逻辑）
- 背景：用户会偶尔彻底卸载并重装 Cursor；AppData 下会话数据可能被清掉，需要可重复、可手点的本机备份与恢复，而不是每次找脚本路径或依赖对话里粘贴提示词。
- 目标：提供 Windows 图形界面，一键备份与一键恢复本机会话相关数据；过程有明确进度与失败提示；恢复前强制确认 Cursor 已退出。
- 非目标：
  - 不做云端同步、不做跨机器账号迁移向导
  - 不保证 Cursor 大版本升级后私有库格式 100% 兼容（若格式变更，工具应提示校验失败，而不是 silently 写坏）
  - 不备份 Cache / GPUCache / 日志等可再生垃圾目录
  - 首版不做自动定时备份、不做增量差分算法
  - 不替代「仅恢复规则笔记」的独立快捷方式逻辑（可勾选附带，但不强制绑死）

## 用户故事

1. 作为本机开发者，我希望在卸载 Cursor 前点「备份」，把会话相关文件存到固定备份根目录，以便重装后还能找回历史对话。
2. 作为本机开发者，我希望在重装并生成过一次数据目录后，退出 Cursor，点「恢复」选中某次备份，把数据覆盖回去，以便侧边栏重新看到历史会话。
3. 作为本机开发者，我希望工具明确警告体积与进程占用，以免拷到一半磁盘满或锁文件失败。

## 已确认（首版）

| 项 | 结论 |
|----|------|
| 平台 | Windows 10/11 |
| UI | Python 标准库 GUI（如 tkinter），尽量无第三方依赖 |
| 默认备份根目录 | `C:\ZYL\backup\`，每次备份子目录名 `cursor-sessions_<yyyyMMdd_HHmmss>`；界面可改根目录 |
| 会话范围（默认勾选） | `%APPDATA%\Cursor\User\globalStorage`（见下方大文件策略）、`workspaceStorage`、`%USERPROFILE%\.cursor\projects`、可选 `settings.json` / `keybindings.json` |
| 规则笔记 | 可选勾选：`C:\ZYL\.cursor`（rules / project-notes / hooks）；默认不勾选，与现有「恢复规则」流程解耦 |
| 大文件策略 | 默认**跳过** `state.vscdb.backup`；必须备份 `state.vscdb`；界面显示预估体积 |
| 恢复前置 | 检测到 Cursor 相关进程则禁止恢复，并提示先退出（含任务管理器） |
| 恢复安全 | 覆盖前把当前目标关键文件/目录挪到同级 `OLD_<时间戳>`，禁止无回退直接删除 |
| 工程路径 | 恢复后文档/界面提示：须用备份时相同的文件夹路径打开项目 |
| 开源 | GitHub 公开仓库，MIT |
| 与旧脚本关系 | 逻辑可参考 `C:\ZYL\scripts\backup-cursor-chats.ps1` 与 `restore-cursor-chats.ps1`，稳定后收敛进本仓库 `src/` |

## 验收标准

- [x] 启动 GUI 后可见「备份」「恢复」两个主操作，以及备份根目录选择。
- [x] 备份：在 Cursor 运行或退出时均可尝试；若文件被锁，界面给出可读错误，不静默成功。
- [x] 备份完成后目录内有 README/说明文本，列出拷了哪些源路径。
- [x] 默认备份结果中**不含** `state.vscdb.backup`（除非用户显式勾选「包含 .backup」）。
- [x] 恢复：若 Cursor 进程存在，点按后立即中止并提示。
- [x] 恢复：覆盖前存在 `OLD_<时间戳>_*` 回退副本（至少覆盖到的关键项）。
- [x] 恢复：可将选定备份中的 `globalStorage` / `workspaceStorage` / `.cursor\projects` 写回对应本机路径。
- [x] 可选勾选恢复/备份 `settings.json`、`keybindings.json`、`C:\ZYL\.cursor`。
- [x] 界面展示本次操作涉及的大致体积（备份前预估；备份后 README 含统计）。
- [x] README 含：安装/启动方式、风险说明、许可证。

## 影响范围

- 新仓库：`cursor-session-backup`（本目录）
- 读路径：Cursor AppData User 目录、用户 `.cursor\projects`、可选 `C:\ZYL\.cursor`
- 写路径：用户选定的备份根目录；恢复时写回上述读路径

## 风险与依赖

- `state.vscdb` 可达数十 GB，磁盘与耗时是主要体验风险。
- Cursor 升级可能改变存储布局；工具需对「备份清单缺失关键文件」给出失败而非假成功。
- 彻底卸载是否删除 `%USERPROFILE%\.cursor` 取决于卸载方式；工具不应假设该目录一定被删。

## 待确认（不阻塞首版开工）

- [ ] 公开仓库默认显示名 / 简介文案是否还要改（当前：`cursor-session-backup`）
- [ ] 是否需要附带「导出可读聊天索引 JSON」（旧脚本有 `export-cursor-chats.py`）——首版可后置
- [ ] 是否做便携绿色版（PyInstaller 单文件）——首版可后置

## 建议下一手

1. 资深软件工程师：按本文实现 `src/` 备份/恢复核心 + 最小 GUI。
2. 测试工程师：按验收标准写手测清单（含进程占用、缺盘、缺备份关键文件）。
