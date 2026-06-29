/**
 * Mobile-only bottom 3-segment tab bar for workspace.
 * Switches between files / chat / execution views.
 */
interface Props {
  mobileTab: "files" | "chat" | "right";
  onTabChange: (tab: "files" | "chat" | "right") => void;
}

export function WorkspaceMobileSegments({ mobileTab, onTabChange }: Props) {
  return (
    <div className="ws-mobile-segs" role="tablist" aria-label="工作区面板">
      <button
        role="tab"
        aria-selected={mobileTab === "files"}
        className={mobileTab === "files" ? "active" : ""}
        onClick={() => onTabChange("files")}
      >
        📂 文件
      </button>
      <button
        role="tab"
        aria-selected={mobileTab === "chat"}
        className={mobileTab === "chat" ? "active" : ""}
        onClick={() => onTabChange("chat")}
      >
        💬 对话
      </button>
      <button
        role="tab"
        aria-selected={mobileTab === "right"}
        className={mobileTab === "right" ? "active" : ""}
        onClick={() => onTabChange("right")}
      >
        ◎ 执行
      </button>
    </div>
  );
}
