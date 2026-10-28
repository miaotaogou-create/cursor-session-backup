import React from 'react';
import { BackupItem } from '../types';
import { AlertTriangle, X, RotateCcw } from 'lucide-react';

interface RestoreConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  backup: BackupItem | null;
  processCount: number;
}

export const RestoreConfirmModal: React.FC<RestoreConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  backup,
  processCount,
}) => {
  if (!isOpen || !backup) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800">
            <div className="w-8 h-8 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm">确认一键恢复？</h3>
              <p className="text-xs text-slate-400">将还原选中的历史会话存档</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-3.5 text-xs text-slate-600">
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200/80 space-y-1.5 font-mono text-[11px]">
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">备份时间:</span>
              <strong className="text-slate-800">{backup.timestamp}</strong>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">占用大小:</span>
              <span className="text-slate-700">{backup.size}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Cursor 版本:</span>
              <span className="text-slate-700">v{backup.cursorVersion}</span>
            </div>
          </div>

          <p className="text-slate-500 leading-relaxed">
            注意：恢复操作会暂时终止当前运行中的 Cursor（<span className="font-semibold text-amber-600">{processCount} 个活动进程</span>），还原配置文件及 workspaceStorage 会话数据库后将自动重启 Cursor。
          </p>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            >
              取消
            </button>
            <button
              type="button"
              onClick={() => {
                onClose();
                onConfirm();
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-lg transition-colors shadow-2xs cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>确认恢复</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
