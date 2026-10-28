import React, { useRef, useEffect, useState } from 'react';
import { LogEntry } from '../types';
import { Terminal, Copy, Trash2, Check, ArrowDownCircle } from 'lucide-react';

interface LogViewerProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  onCopyLogs: (text: string) => void;
}

export const LogViewer: React.FC<LogViewerProps> = ({
  logs,
  onClearLogs,
  onCopyLogs,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [copied, setCopied] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCopy = () => {
    const rawText = logs
      .map((l) => `[${l.time}] [${l.level.toUpperCase()}] ${l.message}`)
      .join('\n');
    onCopyLogs(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const getBadgeStyle = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return 'text-emerald-400 bg-emerald-950/60 border border-emerald-800/40';
      case 'skip':
        return 'text-amber-300 bg-amber-950/60 border border-amber-800/40';
      case 'error':
        return 'text-rose-400 bg-rose-950/60 border border-rose-800/40';
      case 'warn':
        return 'text-orange-300 bg-orange-950/60 border border-orange-800/40';
      case 'info':
      default:
        return 'text-sky-300 bg-sky-950/60 border border-sky-800/40';
    }
  };

  const getLevelLabel = (level: LogEntry['level']) => {
    switch (level) {
      case 'success':
        return '成功';
      case 'skip':
        return '跳过';
      case 'error':
        return '错误';
      case 'warn':
        return '警告';
      case 'info':
      default:
        return '信息';
    }
  };

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 shadow-sm overflow-hidden flex flex-col">
      {/* Terminal Title Bar */}
      <div className="px-3.5 py-2.5 bg-slate-950/70 border-b border-slate-800/90 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-teal-400" />
          <span className="font-medium text-slate-200">运行日志</span>
          <span className="text-[11px] font-mono text-slate-500 tabular-nums">
            ({logs.length} 行)
          </span>
        </div>

        {/* Action Tools */}
        <div className="flex items-center gap-1.5 text-slate-400">
          <button
            type="button"
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1 rounded text-[11px] font-medium transition-colors flex items-center gap-1 ${
              autoScroll ? 'text-teal-400 bg-teal-950/40' : 'text-slate-400 hover:text-slate-200'
            }`}
            title={autoScroll ? '自动滚动已开启' : '点击开启自动滚动'}
          >
            <ArrowDownCircle className="w-3 h-3" />
            <span className="hidden sm:inline">自动滚动</span>
          </button>

          <button
            type="button"
            onClick={handleCopy}
            className="p-1.5 hover:text-slate-200 hover:bg-slate-800/80 rounded transition-colors"
            title="复制全部日志"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>

          <button
            type="button"
            onClick={onClearLogs}
            className="p-1.5 hover:text-rose-400 hover:bg-slate-800/80 rounded transition-colors"
            title="清空日志"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Logs Content */}
      <div
        ref={containerRef}
        className="p-3.5 font-mono text-xs text-slate-300 leading-relaxed max-h-52 min-h-32 overflow-y-auto space-y-1.5 select-text"
      >
        {logs.length === 0 ? (
          <div className="text-slate-600 text-center py-6 italic font-sans text-xs">
            等待任务触发，运行日志将在此实时输出...
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex items-start gap-2 hover:bg-slate-800/40 px-1.5 py-0.5 rounded transition-colors">
              <span className="text-[11px] text-slate-500 shrink-0 tabular-nums select-none pt-0.5">
                {log.time}
              </span>
              <span className={`text-[10px] px-1 py-0.2 rounded font-sans font-medium uppercase shrink-0 ${getBadgeStyle(log.level)}`}>
                {getLevelLabel(log.level)}
              </span>
              <span className="text-slate-200 break-all select-text">
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
