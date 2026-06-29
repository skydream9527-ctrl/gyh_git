/**
 * Reactive mobile breakpoint hook.
 *
 * Returns `true` when viewport width ≤ 768px (standard tablet/phone threshold).
 * Uses matchMedia for efficient listening — no resize event polling.
 *
 * Usage:
 *   const isMobile = useIsMobile();
 *   if (isMobile) return <MobileLayout />;
 */
import { useEffect, useState } from "react";

const MOBILE_QUERY = "(max-width: 768px)";

export function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia(MOBILE_QUERY).matches;
  });

  useEffect(() => {
    const mql = window.matchMedia(MOBILE_QUERY);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    // Sync in case SSR hydration or lazy mount missed the initial value
    setIsMobile(mql.matches);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isMobile;
}
