import React from 'react';
import { OperationState, OperationType } from '../types';
import { CheckCircle2, Clock, Loader2, Sparkles } from 'lucide-react';

const TITLE_BY_OP: Record<OperationType, string> = {
  backup: '备份进度',
  restore: '恢复进度',
  delete: '删除进度',
};

interface ProgressCardProps {
  operationState: OperationState;
  progressPercent: number;
  statusMessage: string;
  operationType: OperationType;
  elapsedTime?: string;
}

export const ProgressCard: React.FC<ProgressCardProps> = ({
  operationState,
  progressPercent,
  statusMessage,
  operationType,
  elapsedTime = '18.4s',
}) => {
  const isCompleted = operationState === 'completed';
  const isBusy =
    operationState === 'backing-up' ||
    operationState === 'restoring' ||
    operationState === 'deleting';

  const title = TITLE_BY_OP[operationType] ?? '操作进度';

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-2xs space-y-3">
      {/* Top Header */}
      <div className="flex items-center justify-between text-xs font-semibold">
        <span className="text-slate-800 flex items-center gap-1.5">
          {title}
          {isBusy && <Loader2 className="w-3.5 h-3.5 text-teal-600 animate-spin" />}
        </span>
        <div>
          {isCompleted ? (
            <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium inline-flex items-center gap-1 border border-emerald-200/60">
              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
              完成
            </span>
          ) : isBusy ? (
            <span className="text-teal-700 bg-teal-50 px-2 py-0.5 rounded font-mono font-medium inline-flex items-center gap-1 border border-teal-200/60">
              <span className="tabular-nums">{Math.round(progressPercent)}%</span>
            </span>
          ) : (
            <span className="text-slate-500 bg-slate-100 px-2 py-0.5 rounded font-normal">
              就绪
            </span>
          )}
        </div>
      </div>

      {/* Modern Progress Bar */}
      <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden p-0.5 border border-slate-200/60">
        <div
          className={`h-full rounded-full transition-all duration-300 ease-out ${
            isCompleted
              ? 'bg-teal-600'
              : isBusy
              ? 'bg-gradient-to-r from-teal-500 to-teal-700 animate-pulse'
              : 'bg-slate-300'
          }`}
          style={{ width: `${Math.min(100, Math.max(0, progressPercent))}%` }}
        />
      </div>

      {/* Bottom Status Text */}
      <div className="flex items-center justify-between text-xs text-slate-600">
        <div className="flex items-center gap-1.5">
          {isCompleted && <Sparkles className="w-3.5 h-3.5 text-emerald-600" />}
          <span className={isCompleted ? 'text-slate-800 font-medium' : 'text-slate-600'}>
            {statusMessage}
          </span>
        </div>

        {isCompleted && (
          <div className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
            <Clock className="w-3 h-3" />
            <span>耗时 {elapsedTime}</span>
          </div>
        )}
      </div>
    </div>
  );
};
