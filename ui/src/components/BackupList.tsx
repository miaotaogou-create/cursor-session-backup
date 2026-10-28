import React from 'react';
import { BackupItem, OperationState } from '../types';
import { RotateCcw, Trash2, Calendar, HardDrive, CheckCircle2, FileText } from 'lucide-react';

interface BackupListProps {
  backups: BackupItem[];
  operationState: OperationState;
  onRestore: (item: BackupItem) => void;
  onDelete: (item: BackupItem) => void;
}

export const BackupList: React.FC<BackupListProps> = ({
  backups,
  operationState,
  onRestore,
  onDelete,
}) => {
  const isBusy =
    operationState === 'backing-up' ||
    operationState === 'restoring' ||
    operationState === 'deleting';

  return (
    <div className="space-y-2.5">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-800">历史对话备份</h2>
          <span className="text-xs text-slate-400">·</span>
          <span className="text-xs font-mono font-medium text-teal-700 bg-teal-50/80 px-2 py-0.5 rounded border border-teal-200/60">
            {backups.length} 份
          </span>
        </div>
        <p className="text-xs text-slate-400">每条可删除或一键恢复</p>
      </div>

      {/* Backups Container */}
      <div className="space-y-2.5">
        {backups.length === 0 ? (
          <div className="bg-white rounded-xl border border-dashed border-slate-300 p-8 text-center">
            <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-600 font-medium">暂无历史会话备份</p>
            <p className="text-xs text-slate-400 mt-1">点击上方「一键备份全部对话」生成第一份数据存档</p>
          </div>
        ) : (
          backups.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs hover:shadow-xs transition-shadow flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              {/* Left Details */}
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="text-base font-semibold font-mono tracking-tight text-slate-900 tabular-nums">
                    {item.timestamp}
                  </span>
                  {item.usable === false ? (
                    <span className="text-[11px] font-medium text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded inline-flex items-center gap-1 border border-rose-200/60">
                      不可用
                    </span>
                  ) : (
                    <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded inline-flex items-center gap-1 border border-emerald-200/60">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      已校验
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1 text-slate-700 font-mono">
                    <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                    {item.size}
                  </span>
                  <span className="text-slate-300">·</span>
                  <span className="font-mono text-slate-600">Cursor {item.cursorVersion}</span>
                  {item.chatCount && (
                    <>
                      <span className="text-slate-300">·</span>
                      <span>{item.chatCount} 个对话上下文</span>
                    </>
                  )}
                  {item.note && (
                    <>
                      <span className="text-slate-300">·</span>
                      <span className="text-slate-400">{item.note}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Right Action Buttons */}
              <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                <button
                  type="button"
                  onClick={() => onDelete(item)}
                  disabled={isBusy}
                  className="px-3.5 py-2 rounded-lg text-xs font-medium text-rose-600 bg-rose-50 hover:bg-rose-100/90 active:bg-rose-200/70 border border-rose-200/60 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1.5"
                  title="删除此条备份"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>删除</span>
                </button>

                <button
                  type="button"
                  onClick={() => onRestore(item)}
                  disabled={isBusy || item.usable === false}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 active:bg-teal-900 transition-colors shadow-2xs disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer inline-flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-1"
                  title="以此备份一键恢复 Cursor 会话数据"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>一键恢复</span>
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
