import React from 'react';
import { Minus, Square, Copy, X, Database, ShieldCheck } from 'lucide-react';

interface WindowHeaderProps {
  version: string;
  isMaximized?: boolean;
  onMinimize?: () => void;
  onMaximize?: () => void;
  onClose?: () => void;
}

export const WindowHeader: React.FC<WindowHeaderProps> = ({
  version,
  isMaximized = false,
  onMinimize,
  onMaximize,
  onClose,
}) => {
  return (
    <header className="pywebview-drag-region h-10 px-4 bg-teal-800 text-teal-100 flex items-center justify-between select-none border-b border-teal-900/40 shrink-0">
      <div className="flex items-center gap-2.5">
        <div className="w-5 h-5 rounded-md bg-teal-600/60 flex items-center justify-center text-teal-50 border border-teal-400/30 shadow-inner">
          <Database className="w-3.5 h-3.5" />
        </div>
        <div className="flex items-baseline gap-2">
          <span className="font-semibold text-xs tracking-wide text-white">Cursor 会话备份</span>
          <span className="text-[11px] font-mono text-teal-300/80">v{version}</span>
        </div>
      </div>

      <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-teal-200/70 font-medium">
        <ShieldCheck className="w-3.5 h-3.5 text-teal-300" />
        <span>本地安全存储 · 无网络上传</span>
      </div>

      <div className="flex items-center -mr-2">
        <button
          type="button"
          aria-label="最小化"
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-teal-700/60 hover:text-white transition-colors"
          title="最小化"
          onClick={onMinimize}
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          aria-label={isMaximized ? '还原' : '最大化'}
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-teal-700/60 hover:text-white transition-colors"
          title={isMaximized ? '还原' : '最大化'}
          onClick={onMaximize}
        >
          {isMaximized ? <Copy className="w-3 h-3" /> : <Square className="w-3 h-3" />}
        </button>
        <button
          type="button"
          aria-label="关闭"
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-rose-600 hover:text-white transition-colors"
          title="关闭"
          onClick={onClose}
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
