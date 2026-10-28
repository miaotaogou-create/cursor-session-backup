import React from 'react';
import { X, Folder, FileArchive, FileCode, Database, Copy, Check, ExternalLink } from 'lucide-react';

interface FolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  folderPath: string;
  onCopyPath: (path: string) => void;
}

export const FolderModal: React.FC<FolderModalProps> = ({
  isOpen,
  onClose,
  folderPath,
  onCopyPath,
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    onCopyPath(folderPath);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const files = [
    { name: 'backup_20261028_115339.zip', size: '21.0 GB', type: 'archive', date: '2026-10-28 11:53' },
    { name: 'workspaceStorage', size: '20.8 GB', type: 'folder', date: '2026-10-28 11:53' },
    { name: 'globalStorage', size: '184 MB', type: 'folder', date: '2026-10-28 11:52' },
    { name: 'state.vscdb', size: '42.6 MB', type: 'db', date: '2026-10-28 11:52' },
    { name: 'settings.json', size: '14.2 KB', type: 'json', date: '2026-10-28 10:20' },
  ];

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800">
            <Folder className="w-5 h-5 text-amber-500 fill-amber-100" />
            <div>
              <h3 className="font-semibold text-sm">备份目录浏览器</h3>
              <p className="text-xs text-slate-400 font-mono">{folderPath}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Directory File List */}
        <div className="p-4 divide-y divide-slate-100 max-h-72 overflow-y-auto">
          {files.map((file, idx) => (
            <div key={idx} className="py-2.5 px-2 flex items-center justify-between text-xs hover:bg-slate-50/80 rounded-lg transition-colors">
              <div className="flex items-center gap-2.5">
                {file.type === 'archive' && <FileArchive className="w-4 h-4 text-teal-600" />}
                {file.type === 'folder' && <Folder className="w-4 h-4 text-amber-500" />}
                {file.type === 'db' && <Database className="w-4 h-4 text-indigo-500" />}
                {file.type === 'json' && <FileCode className="w-4 h-4 text-emerald-500" />}
                <div>
                  <div className="font-mono text-slate-800 font-medium">{file.name}</div>
                  <div className="text-[11px] text-slate-400">{file.date}</div>
                </div>
              </div>
              <span className="font-mono text-slate-500 tabular-nums">{file.size}</span>
            </div>
          ))}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs">
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-white transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? '已复制完整路径' : '复制目录路径'}</span>
          </button>

          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-teal-700 text-white font-medium hover:bg-teal-800 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};
