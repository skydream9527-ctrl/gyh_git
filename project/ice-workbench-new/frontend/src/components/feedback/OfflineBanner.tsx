/**
 * Offline/online status banner.
 *
 * Renders a fixed banner at the top of the viewport when the browser is offline.
 * Auto-hides when connectivity is restored (with a brief "back online" message).
 */
import { useEffect, useState } from "react";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";

export function OfflineBanner() {
  const { online, wasOffline } = useNetworkStatus();
  const [showRestored, setShowRestored] = useState(false);

  useEffect(() => {
    if (online && wasOffline) {
      setShowRestored(true);
      const t = setTimeout(() => setShowRestored(false), 3000);
      return () => clearTimeout(t);
    }
  }, [online, wasOffline]);

  if (online && !showRestored) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        padding: "8px 16px",
        textAlign: "center",
        fontSize: 13,
        fontWeight: 500,
        color: "#fff",
        backgroundColor: online ? "#22c55e" : "#ef4444",
        transition: "background-color 0.3s ease",
      }}
    >
      {online ? "网络已恢复" : "网络已断开，等待重新连接..."}
    </div>
  );
}
