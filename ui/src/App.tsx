/**
 * Cursor 会话备份 — 桌面端界面（经 pywebview 调用本机 Python API）
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BackupItem, LogEntry, OperationState, SystemInfo } from './types';
import { WindowHeader } from './components/WindowHeader';
import { StatusBanner } from './components/StatusBanner';
import { ActionBar } from './components/ActionBar';
import { BackupList } from './components/BackupList';
import { ProgressCard } from './components/ProgressCard';
import { LogViewer } from './components/LogViewer';
import { FolderModal } from './components/FolderModal';
import { PathEditModal } from './components/PathEditModal';
import { RestoreConfirmModal } from './components/RestoreConfirmModal';
import { DeleteConfirmModal } from './components/DeleteConfirmModal';
import { ApiSnapshot, getApi, waitForApi } from './bridge';

function mapBackup(b: ApiSnapshot['backups'][number]): BackupItem {
  return {
    id: b.id,
    path: b.path,
    timestamp: b.timestamp,
    size: b.size,
    cursorVersion: b.cursorVersion,
    chatCount: b.chatCount,
    note: b.note,
    usable: b.usable,
  };
}

function applySnapshot(
  snap: ApiSnapshot,
  setSystemInfo: (s: SystemInfo) => void,
  setBackups: (b: BackupItem[]) => void,
  setAppVersion: (v: string) => void,
) {
  setAppVersion(snap.appVersion);
  setSystemInfo(snap.systemInfo);
  setBackups(snap.backups.map(mapBackup));
}

export default function App() {
  const [appVersion, setAppVersion] = useState('…');
  const [systemInfo, setSystemInfo] = useState<SystemInfo>({
    cursorVersion: '…',
    installPath: '…',
    isRunning: false,
    processCount: 0,
    backupDirectory: '…',
    diskFreeSpace: '…',
  });
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [operationState, setOperationState] = useState<OperationState>('idle');
  const [operationType, setOperationType] = useState<'backup' | 'restore'>('backup');
  const [progressPercent, setProgressPercent] = useState(0);
  const [statusMessage, setStatusMessage] = useState('就绪');
  const [elapsedTime, setElapsedTime] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [folderModalOpen, setFolderModalOpen] = useState(false);
  const [pathModalOpen, setPathModalOpen] = useState(false);
  const [restoreModalOpen, setRestoreModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<BackupItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [apiReady, setApiReady] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);
  const pollRef = useRef<number | null>(null);

  const showToast = useCallback((msg: string) => {
    setToastMessage(msg);
    window.setTimeout(() => setToastMessage(null), 2500);
  }, []);

  const addLog = useCallback((level: LogEntry['level'], message: string) => {
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(
      now.getMinutes(),
    ).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
    setLogs((prev) => [
      ...prev,
      {
        id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        time: timeStr,
        level,
        message,
      },
    ]);
  }, []);

  const refreshSnapshot = useCallback(async () => {
    const api = getApi();
    if (!api) return;
    const snap = await api.get_snapshot();
    applySnapshot(snap, setSystemInfo, setBackups, setAppVersion);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const api = await waitForApi();
      if (cancelled) return;
      if (!api) {
        addLog('warn', '未检测到桌面桥接：请通过 CursorSessionBackup.exe 启动以执行真实备份。');
        showToast('当前为界面预览模式');
        return;
      }
      setApiReady(true);
      try {
        const snap = await api.get_snapshot();
        applySnapshot(snap, setSystemInfo, setBackups, setAppVersion);
        try {
          setIsMaximized(Boolean(await api.window_is_maximized()));
        } catch {
          /* 旧版桥接无此接口 */
        }
        addLog('info', '已连接本机备份引擎');
      } catch (e) {
        addLog('error', `读取状态失败: ${e}`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [addLog, showToast]);

  useEffect(() => {
    if (!apiReady) return;
    const tick = async () => {
      const api = getApi();
      if (!api) return;
      try {
        const events = await api.poll_events();
        for (const ev of events) {
          const kind = String(ev.kind || '');
          if (kind === 'log') {
            addLog(
              (ev.level as LogEntry['level']) || 'info',
              String(ev.message || ''),
            );
          } else if (kind === 'toast') {
            showToast(String(ev.message || ''));
          } else if (kind === 'op') {
            const state = (ev.state as OperationState) || 'idle';
            setOperationState(state);
            if (ev.op === 'restore' || ev.op === 'backup') {
              setOperationType(ev.op);
            }
            if (typeof ev.percent === 'number') {
              setProgressPercent(ev.percent);
            }
            if (ev.message) {
              setStatusMessage(String(ev.message));
            }
            if (ev.elapsed) {
              setElapsedTime(String(ev.elapsed));
            }
          } else if (kind === 'snapshot' && ev.snapshot) {
            applySnapshot(
              ev.snapshot as ApiSnapshot,
              setSystemInfo,
              setBackups,
              setAppVersion,
            );
          } else if (kind === 'windowMaximized') {
            setIsMaximized(Boolean(ev.maximized));
          }
        }
      } catch {
        /* 轮询失败时下一轮再试 */
      }
    };
    pollRef.current = window.setInterval(tick, 250);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [apiReady, addLog, showToast]);

  const handleBackupAll = async () => {
    if (operationState === 'backing-up' || operationState === 'restoring') return;
    const api = getApi();
    if (!api) {
      showToast('请用桌面程序启动后再备份');
      return;
    }
    setOperationType('backup');
    setElapsedTime('');
    const res = await api.start_backup();
    if (!res.ok) showToast(res.error || '无法开始备份');
  };

  const handleRequestRestore = (backup: BackupItem) => {
    setSelectedBackup(backup);
    setRestoreModalOpen(true);
  };

  const handleConfirmRestore = async () => {
    if (!selectedBackup?.path) return;
    setRestoreModalOpen(false);
    const api = getApi();
    if (!api) {
      showToast('请用桌面程序启动后再恢复');
      return;
    }
    setOperationType('restore');
    setElapsedTime('');
    const res = await api.start_restore(selectedBackup.path);
    if (!res.ok) {
      showToast(res.error || '无法开始恢复');
      addLog('error', res.error || '无法开始恢复');
    }
    setSelectedBackup(null);
  };

  const handleRequestDelete = (backup: BackupItem) => {
    setSelectedBackup(backup);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!selectedBackup?.path) return;
    const path = selectedBackup.path;
    setDeleteModalOpen(false);
    setSelectedBackup(null);
    const api = getApi();
    if (!api) {
      showToast('请用桌面程序启动后再删除');
      return;
    }
    const res = await api.delete_backup(path);
    if (!res.ok) showToast(res.error || '删除失败');
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    addLog('info', '正在检测 Cursor 运行状态及备份目录...');
    try {
      await refreshSnapshot();
      addLog('info', '检测完成');
      showToast('环境检测与目录状态已刷新');
    } catch (e) {
      addLog('error', `刷新失败: ${e}`);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    // 桌面无边框窗口：铺满客户区，不要网页式「居中卡片+四周灰边」
    <div className="h-screen w-screen overflow-hidden bg-slate-50 flex flex-col font-sans antialiased">
      {toastMessage && (
        <div className="fixed top-5 left-1/2 -translate-x-1/2 z-60 bg-slate-900/90 backdrop-blur-md text-white text-xs font-medium px-4 py-2.5 rounded-xl shadow-lg border border-slate-700/80 flex items-center gap-2">
          <span>{toastMessage}</span>
        </div>
      )}

      <WindowHeader
        version={appVersion}
        isMaximized={isMaximized}
        onMinimize={() => void getApi()?.window_minimize()}
        onMaximize={() => {
          void (async () => {
            const api = getApi();
            if (!api) return;
            const res = await api.window_toggle_maximize();
            if (res && typeof res.maximized === 'boolean') {
              setIsMaximized(res.maximized);
            }
          })();
        }}
        onClose={() => void getApi()?.window_close()}
      />

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="p-5 sm:p-7 space-y-6 bg-slate-50">
          <StatusBanner
            systemInfo={systemInfo}
            onEditBackupDir={() => {
              void (async () => {
                const api = getApi();
                if (api) {
                  const pick = await api.pick_backup_directory();
                  if (pick.ok && pick.snapshot) {
                    applySnapshot(pick.snapshot, setSystemInfo, setBackups, setAppVersion);
                    showToast('备份目录已更新');
                    return;
                  }
                  if (pick.cancelled) return;
                  showToast(pick.error || '更改失败');
                  return;
                }
                setPathModalOpen(true);
              })();
            }}
            onCopyPath={(path, label) => {
              navigator.clipboard?.writeText(path);
              showToast(`${label}已复制到剪贴板`);
            }}
          />

          <ActionBar
            operationState={operationState}
            onBackupAll={() => void handleBackupAll()}
            onOpenFolder={() => {
              const api = getApi();
              if (api) void api.open_backup_folder();
              else setFolderModalOpen(true);
            }}
            onRefresh={() => void handleRefresh()}
            isRefreshing={isRefreshing}
          />

          <BackupList
            backups={backups}
            operationState={operationState}
            onRestore={handleRequestRestore}
            onDelete={handleRequestDelete}
          />

          <ProgressCard
            operationState={operationState}
            progressPercent={progressPercent}
            statusMessage={statusMessage}
            operationType={operationType}
            elapsedTime={elapsedTime}
          />

          <LogViewer
            logs={logs}
            onClearLogs={() => {
              setLogs([]);
              showToast('运行日志已清空');
            }}
            onCopyLogs={(text) => {
              navigator.clipboard?.writeText(text);
              showToast('运行日志已复制到剪贴板');
            }}
          />
        </div>
      </div>

      <FolderModal
        isOpen={folderModalOpen}
        onClose={() => setFolderModalOpen(false)}
        folderPath={systemInfo.backupDirectory}
        onCopyPath={(p) => {
          navigator.clipboard?.writeText(p);
          showToast('备份目录已复制');
        }}
      />

      <PathEditModal
        isOpen={pathModalOpen}
        onClose={() => setPathModalOpen(false)}
        currentPath={systemInfo.backupDirectory}
        onSave={(newPath) => {
          void (async () => {
            const api = getApi();
            if (api) {
              const pick = await api.pick_backup_directory();
              if (pick.ok && pick.snapshot) {
                applySnapshot(pick.snapshot, setSystemInfo, setBackups, setAppVersion);
                showToast('备份目录已更新');
                return;
              }
              if (pick.cancelled) return;
              const res = await api.set_backup_directory(newPath);
              if (res.ok && res.snapshot) {
                applySnapshot(res.snapshot, setSystemInfo, setBackups, setAppVersion);
                showToast('备份目录已更新');
                return;
              }
              showToast(res.error || pick.error || '更改失败');
              return;
            }
            setSystemInfo((prev) => ({ ...prev, backupDirectory: newPath }));
            addLog('info', `备份目录已修改为: ${newPath}`);
            showToast('备份目录已更新');
          })();
        }}
      />

      <RestoreConfirmModal
        isOpen={restoreModalOpen}
        onClose={() => {
          setRestoreModalOpen(false);
          setSelectedBackup(null);
        }}
        onConfirm={() => void handleConfirmRestore()}
        backup={selectedBackup}
        processCount={systemInfo.processCount}
      />

      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setSelectedBackup(null);
        }}
        onConfirm={() => void handleConfirmDelete()}
        backup={selectedBackup}
      />
    </div>
  );
}
