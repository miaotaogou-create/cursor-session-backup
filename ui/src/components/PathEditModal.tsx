import React, { useState } from 'react';
import { X, FolderEdit } from 'lucide-react';

interface PathEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPath: string;
  onSave: (newPath: string) => void;
}

export const PathEditModal: React.FC<PathEditModalProps> = ({
  isOpen,
  onClose,
  currentPath,
  onSave,
}) => {
  const [val, setVal] = useState(currentPath);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (val.trim()) {
      onSave(val.trim());
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800">
            <FolderEdit className="w-5 h-5 text-teal-600" />
            <h3 className="font-semibold text-sm">修改备份目录</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">
              目标本地目录路径
            </label>
            <input
              type="text"
              value={val}
              onChange={(e) => setVal(e.target.value)}
              className="w-full px-3 py-2 text-xs font-mono border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-600/30 focus:border-teal-600"
              placeholder="例如: D:\CursorBackup"
              autoFocus
            />
            <p className="text-[11px] text-slate-400 mt-1.5">
              提示：请确保目标磁盘拥有足够空间（建议 25 GB 以上）。
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
            >
              取消
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded-lg transition-colors"
            >
              保存修改
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
