import React from 'react';
import { Minus, Square, Copy, X, Database, ShieldCheck } from 'lucide-react';
import { getApi } from '../bridge';

interface WindowHeaderProps {
  version: string;
  isMaximized?: boolean;
  onMinimize?: () => void;
  onMaximize?: () => void;
  onClose?: () => void;
}

/** 统一点击区旁的描边图标基准尺寸（14px） */
const ICON = 'w-3.5 h-3.5';
/** Lucide Square/Copy 在 viewBox 内占位比 X 大（约 18 vs 12），略缩小以光学对齐 */
const ICON_BOX = 'w-3 h-3';

export const WindowHeader: React.FC<WindowHeaderProps> = ({
  version,
  isMaximized = false,
  onMinimize,
  onMaximize,
  onClose,
}) => {
  const beginDrag = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    void getApi()?.window_begin_drag();
  };

  return (
    <header className="relative h-10 bg-teal-800 text-teal-100 flex items-center select-none border-b border-teal-900/40 shrink-0">
      {/* 左侧标题：可拖 */}
      <div
        className="relative z-10 flex-1 min-w-0 h-full px-4 flex items-center gap-2.5 cursor-default"
        onMouseDown={beginDrag}
      >
        <div className="w-5 h-5 rounded-md bg-teal-600/60 flex items-center justify-center text-teal-50 border border-teal-400/30 shadow-inner shrink-0">
          <Database className="w-3.5 h-3.5" />
        </div>
        <div className="flex items-baseline gap-2 min-w-0">
          <span className="font-semibold text-xs tracking-wide text-white truncate">
            Cursor 会话备份
          </span>
          <span className="text-[11px] font-mono text-teal-300/80 shrink-0">v{version}</span>
        </div>
      </div>

      {/* 正中提示：绝对居中；也可拖 */}
      <div
        className="hidden sm:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10 items-center gap-1.5 text-[11px] text-teal-200/70 font-medium whitespace-nowrap cursor-default"
        onMouseDown={beginDrag}
      >
        <ShieldCheck className="w-3.5 h-3.5 text-teal-300" />
        <span>本地安全存储 · 无网络上传</span>
      </div>

      {/* 窗控：不拖，图标统一尺寸 */}
      <div className="relative z-20 flex items-center h-full shrink-0">
        <button
          type="button"
          aria-label="最小化"
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-teal-700/60 hover:text-white transition-colors"
          title="最小化"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={onMinimize}
        >
          <Minus className={ICON} strokeWidth={2} />
        </button>
        <button
          type="button"
          aria-label={isMaximized ? '还原' : '最大化'}
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-teal-700/60 hover:text-white transition-colors"
          title={isMaximized ? '还原' : '最大化'}
          onMouseDown={(e) => e.stopPropagation()}
          onClick={onMaximize}
        >
          {isMaximized ? (
            <Copy className={ICON_BOX} strokeWidth={2} />
          ) : (
            <Square className={ICON_BOX} strokeWidth={2} />
          )}
        </button>
        <button
          type="button"
          aria-label="关闭"
          className="w-10 h-10 inline-flex items-center justify-center text-teal-200/80 hover:bg-rose-600 hover:text-white transition-colors"
          title="关闭"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={onClose}
        >
          <X className={ICON} strokeWidth={2} />
        </button>
      </div>
    </header>
  );
};
