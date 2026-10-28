/** 与 Python pywebview DesktopApi 的桥接。 */

export type ApiSnapshot = {
  appVersion: string;
  systemInfo: {
    cursorVersion: string;
    installPath: string;
    isRunning: boolean;
    processCount: number;
    backupDirectory: string;
    diskFreeSpace: string;
  };
  backups: Array<{
    id: string;
    path: string;
    timestamp: string;
    size: string;
    cursorVersion: string;
    chatCount?: number;
    note?: string;
    usable: boolean;
  }>;
  busy: boolean;
};

type DesktopApi = {
  get_snapshot: () => Promise<ApiSnapshot>;
  poll_events: () => Promise<Array<Record<string, unknown>>>;
  start_backup: () => Promise<{ ok: boolean; error?: string }>;
  start_restore: (path: string) => Promise<{ ok: boolean; error?: string }>;
  delete_backup: (path: string) => Promise<{ ok: boolean; error?: string }>;
  open_backup_folder: () => Promise<{ ok: boolean; error?: string }>;
  pick_backup_directory: () => Promise<{
    ok: boolean;
    cancelled?: boolean;
    path?: string;
    snapshot?: ApiSnapshot;
    error?: string;
  }>;
  set_backup_directory: (path: string) => Promise<{
    ok: boolean;
    snapshot?: ApiSnapshot;
    error?: string;
  }>;
  window_minimize: () => Promise<void>;
  window_toggle_maximize: () => Promise<{ ok: boolean; maximized: boolean }>;
  window_is_maximized: () => Promise<boolean>;
  window_begin_drag: () => Promise<void>;
  window_begin_resize: (edge: string) => Promise<void>;
  window_close: () => Promise<void>;
};

declare global {
  interface Window {
    pywebview?: { api: DesktopApi };
  }
}

export function hasDesktopApi(): boolean {
  return Boolean(window.pywebview?.api);
}

export async function waitForApi(timeoutMs = 8000): Promise<DesktopApi | null> {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (window.pywebview?.api) {
      return window.pywebview.api;
    }
    await new Promise((r) => setTimeout(r, 50));
  }
  return window.pywebview?.api ?? null;
}

export function getApi(): DesktopApi | null {
  return window.pywebview?.api ?? null;
}
