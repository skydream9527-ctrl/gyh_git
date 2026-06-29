/**
 * Reactive network status hook.
 *
 * Tracks `navigator.onLine` and dispatches online/offline transitions.
 * Used by useChatSocket to pause reconnect attempts when offline, and by
 * the UI to display an offline banner.
 *
 * Returns:
 *  - `online`: current connectivity state
 *  - `wasOffline`: true if the user was offline at any point this session
 *    (useful for showing "connection restored" messages)
 */
import { useCallback, useEffect, useRef, useState } from "react";

export interface NetworkStatus {
  online: boolean;
  /** True after at least one offline→online transition this mount. */
  wasOffline: boolean;
}

export function useNetworkStatus(): NetworkStatus {
  const [online, setOnline] = useState(() =>
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const wasOfflineRef = useRef(false);
  const [wasOffline, setWasOffline] = useState(false);

  const handleOnline = useCallback(() => {
    setOnline(true);
    if (wasOfflineRef.current) {
      setWasOffline(true);
    }
  }, []);

  const handleOffline = useCallback(() => {
    setOnline(false);
    wasOfflineRef.current = true;
  }, []);

  useEffect(() => {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [handleOnline, handleOffline]);

  return { online, wasOffline };
}
