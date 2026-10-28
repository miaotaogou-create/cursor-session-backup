import React from 'react';
import { ArrowDownToLine, FolderOpen, RefreshCw, Loader2 } from 'lucide-react';
import { OperationState } from '../types';

interface ActionBarProps {
  operationState: OperationState;
  onBackupAll: () => void;
  onOpenFolder: () => void;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export const ActionBar: React.FC<ActionBarProps> = ({
  operationState,
  onBackupAll,
  onOpenFolder,
  onRefresh,
  isRefreshing,
}) => {
  const isBusy = operationState === 'backing-up' || operationState === 'restoring';

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
      {/* Primary Actions */}
      <div className="flex items-center gap-2.5">
        <button
          type="button"
          onClick={onBackupAll}
          disabled={isBusy}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-teal-700 hover:bg-teal-800 active:bg-teal-900 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-1 cursor-pointer"
        >
          {operationState === 'backing-up' ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>正在备份全部对话...</span>
            </>
          ) : (
            <>
              <ArrowDownToLine className="w-4 h-4" />
              <span>一键备份全部对话</span>
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onOpenFolder}
          className="inline-flex items-center gap-2 px-3.5 py-2.5 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-200/90 shadow-2xs transition-all focus:outline-none focus:ring-2 focus:ring-slate-300 cursor-pointer"
        >
          <FolderOpen className="w-4 h-4 text-slate-500" />
          <span>打开备份文件夹</span>
        </button>
      </div>

      {/* Right Action: Refresh */}
      <button
        type="button"
        onClick={onRefresh}
        disabled={isRefreshing || isBusy}
        className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100/80 hover:bg-slate-200/70 active:bg-slate-200 transition-colors cursor-pointer disabled:opacity-50"
        title="刷新当前进程及备份目录"
      >
        <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-teal-600' : 'text-slate-500'}`} />
        <span>刷新</span>
      </button>
    </div>
  );
};
