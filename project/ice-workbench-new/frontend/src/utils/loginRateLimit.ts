/**
 * Client-side login rate limiter — defense-in-depth on top of the backend
 * `rate_limit_svc`. The backend is authoritative; this just spares the user
 * from staring at "failed" toasts while a script keeps hammering, and stops
 * a leaked tab from being abused for offline brute force against the same
 * account. State lives in localStorage so it survives reload but not the
 * browser profile boundary.
 *
 * Window: 5 attempts within 5 minutes → soft-lock for the rest of the
 * window. The backend's per-IP / per-email caps still apply unchanged.
 */
const KEY_PREFIX = "ice-login-attempts:";
const WINDOW_MS = 5 * 60 * 1000;
const MAX_ATTEMPTS = 5;

interface AttemptRecord {
  count: number;
  firstAt: number;
}

function load(email: string): AttemptRecord | null {
  try {
    const raw = localStorage.getItem(KEY_PREFIX + email.toLowerCase());
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AttemptRecord;
    if (typeof parsed.count !== "number" || typeof parsed.firstAt !== "number") return null;
    return parsed;
  } catch {
    return null;
  }
}

function save(email: string, rec: AttemptRecord): void {
  try {
    localStorage.setItem(KEY_PREFIX + email.toLowerCase(), JSON.stringify(rec));
  } catch {
    // localStorage quota / disabled — fail open (backend still gates)
  }
}

/** Returns seconds-until-allowed, or 0 if the next attempt is OK. */
export function checkLoginLimit(email: string): number {
  if (!email) return 0;
  const rec = load(email);
  if (!rec) return 0;
  const elapsed = Date.now() - rec.firstAt;
  if (elapsed > WINDOW_MS) {
    // window expired — fall through and allow
    localStorage.removeItem(KEY_PREFIX + email.toLowerCase());
    return 0;
  }
  if (rec.count >= MAX_ATTEMPTS) {
    return Math.ceil((WINDOW_MS - elapsed) / 1000);
  }
  return 0;
}

export function recordLoginFailure(email: string): void {
  if (!email) return;
  const rec = load(email);
  const now = Date.now();
  if (!rec || now - rec.firstAt > WINDOW_MS) {
    save(email, { count: 1, firstAt: now });
    return;
  }
  save(email, { count: rec.count + 1, firstAt: rec.firstAt });
}

export function clearLoginLimit(email: string): void {
  if (!email) return;
  try {
    localStorage.removeItem(KEY_PREFIX + email.toLowerCase());
  } catch {
    /* no-op */
  }
}
