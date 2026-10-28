import React from 'react';
import { getApi } from '../bridge';

type Edge = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw';

const EDGES: Array<{ edge: Edge; className: string; cursor: string }> = [
  { edge: 'n', className: 'top-0 left-2 right-2 h-1.5', cursor: 'ns-resize' },
  { edge: 's', className: 'bottom-0 left-2 right-2 h-1.5', cursor: 'ns-resize' },
  { edge: 'w', className: 'left-0 top-2 bottom-2 w-1.5', cursor: 'ew-resize' },
  { edge: 'e', className: 'right-0 top-2 bottom-2 w-1.5', cursor: 'ew-resize' },
  { edge: 'nw', className: 'top-0 left-0 w-3 h-3', cursor: 'nwse-resize' },
  { edge: 'ne', className: 'top-0 right-0 w-3 h-3', cursor: 'nesw-resize' },
  { edge: 'sw', className: 'bottom-0 left-0 w-3 h-3', cursor: 'nesw-resize' },
  { edge: 'se', className: 'bottom-0 right-0 w-3 h-3', cursor: 'nwse-resize' },
];

interface WindowResizeEdgesProps {
  disabled?: boolean;
}

/** 无边框窗口四边/四角拖拽缩放（最大化时隐藏）。 */
export const WindowResizeEdges: React.FC<WindowResizeEdgesProps> = ({ disabled = false }) => {
  if (disabled) return null;

  const onDown = (edge: Edge) => (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();
    void getApi()?.window_begin_resize(edge);
  };

  return (
    <>
      {EDGES.map(({ edge, className, cursor }) => (
        <div
          key={edge}
          className={`fixed z-50 ${className}`}
          style={{ cursor }}
          onMouseDown={onDown(edge)}
        />
      ))}
    </>
  );
};
