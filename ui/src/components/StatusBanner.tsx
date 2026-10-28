import React, { useState } from 'react';
import { SystemInfo } from '../types';
import { Folder, HardDrive, Copy, Check, Edit3, Activity } from 'lucide-react';

interface StatusBannerProps {
  systemInfo: SystemInfo;
  onEditBackupDir: () => void;
  onCopyPath: (path: string, type: string) => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  systemInfo,
  onEditBackupDir,
  onCopyPath,
}) => {
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [copiedBackup, setCopiedBackup] = useState(false);

  const handleCopyInstall = () => {
    onCopyPath(systemInfo.installPath, '程序路径');
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 1500);
  };

  const handleCopyBackup = () => {
    onCopyPath(systemInfo.backupDirectory, '备份目录');
    setCopiedBackup(true);
    setTimeout(() => setCopiedBackup(false), 1500);
  };

  return (
    <div className="space-y-4">
      {/* App Main Title & Quick Status */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-200/80 pb-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            Cursor 会话备份
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-teal-50 text-teal-700 border border-teal-200">
              Session Manager
            </span>
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            一键保存并快速还原 Cursor AI 历史会话对话、workspaceStorage 及配置
          </p>
        </div>

        {/* Live Running Badge */}
        <div className="flex items-center gap-2 self-start sm:self-auto bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200/90 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="font-medium text-slate-700">
              {systemInfo.isRunning ? 'Cursor 运行中' : 'Cursor 未运行'}
            </span>
          </div>
          <span className="text-slate-300">|</span>
          <span className="font-mono text-slate-600 tabular-nums">
            {systemInfo.processCount} 个活动进程
          </span>
        </div>
      </div>

      {/* Path & Metadata Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
        {/* Installed Path Card */}
        <div className="bg-slate-50/70 hover:bg-slate-50 p-3 rounded-xl border border-slate-200 transition-colors flex flex-col justify-between gap-1.5">
          <div className="flex items-center justify-between text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-teal-600" />
              已安装版本: <strong className="text-slate-800 font-mono">v{systemInfo.cursorVersion}</strong>
            </span>
            <button
              onClick={handleCopyInstall}
              className="text-slate-400 hover:text-slate-700 p-1 rounded transition-colors inline-flex items-center gap-1"
              title="复制完整路径"
            >
              {copiedInstall ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-[11px] text-emerald-600 font-medium">已复制</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[11px]">复制</span>
                </>
              )}
            </button>
          </div>
          <div className="font-mono text-[11px] text-slate-600 truncate bg-white px-2 py-1 rounded border border-slate-200/80" title={systemInfo.installPath}>
            {systemInfo.installPath}
          </div>
        </div>

        {/* Backup Target Directory Card */}
        <div className="bg-slate-50/70 hover:bg-slate-50 p-3 rounded-xl border border-slate-200 transition-colors flex flex-col justify-between gap-1.5">
          <div className="flex items-center justify-between text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <Folder className="w-3.5 h-3.5 text-amber-600" />
              备份目录: <span className="text-slate-500 font-normal">剩余空间 {systemInfo.diskFreeSpace}</span>
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={handleCopyBackup}
                className="text-slate-400 hover:text-slate-700 p-1 rounded transition-colors inline-flex items-center gap-1"
                title="复制备份路径"
              >
                {copiedBackup ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span className="text-[11px] text-emerald-600 font-medium">已复制</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span className="text-[11px]">复制</span>
                  </>
                )}
              </button>
              <button
                onClick={onEditBackupDir}
                className="text-teal-700 hover:text-teal-800 hover:bg-teal-50 px-1.5 py-0.5 rounded transition-colors inline-flex items-center gap-1 text-[11px] font-medium"
                title="更改备份目录"
              >
                <Edit3 className="w-3 h-3" />
                <span>更改</span>
              </button>
            </div>
          </div>
          <div className="font-mono text-[11px] text-slate-600 truncate bg-white px-2 py-1 rounded border border-slate-200/80 flex items-center justify-between" title={systemInfo.backupDirectory}>
            <span className="truncate">{systemInfo.backupDirectory}</span>
            <HardDrive className="w-3 h-3 text-slate-400 shrink-0 ml-1" />
          </div>
        </div>
      </div>
    </div>
  );
};
