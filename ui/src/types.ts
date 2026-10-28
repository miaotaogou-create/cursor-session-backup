export interface BackupItem {
  id: string;
  timestamp: string;
  size: string;
  cursorVersion: string;
  chatCount?: number;
  note?: string;
  path?: string;
  usable?: boolean;
}

export interface LogEntry {
  id: string;
  time: string;
  level: 'info' | 'success' | 'skip' | 'warn' | 'error';
  message: string;
}

export type OperationState =
  | 'idle'
  | 'backing-up'
  | 'restoring'
  | 'deleting'
  | 'completed'
  | 'error';

export type OperationType = 'backup' | 'restore' | 'delete';

export interface SystemInfo {
  cursorVersion: string;
  installPath: string;
  isRunning: boolean;
  processCount: number;
  backupDirectory: string;
  diskFreeSpace: string;
}
