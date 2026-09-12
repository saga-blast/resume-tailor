import { ReactNode } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface SplitPaneProps {
  left: ReactNode;
  right: ReactNode;
}

export default function SplitPane({ left, right }: SplitPaneProps) {
  return (
    <PanelGroup direction="horizontal" className="min-h-0 flex-1">
      <Panel defaultSize={50} minSize={25}>
        {left}
      </Panel>
      <PanelResizeHandle className="w-1 cursor-col-resize bg-gray-200 hover:bg-indigo-400" />
      <Panel defaultSize={50} minSize={25}>
        {right}
      </Panel>
    </PanelGroup>
  );
}
