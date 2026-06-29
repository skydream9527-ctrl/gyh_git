#!/usr/bin/env python3
"""
Shared Mify API client module.

Provides HTTP helpers, auth management, config/state I/O, and multipart upload.
All HTTP via Python stdlib (urllib.request). No third-party dependencies.
"""

import hashlib
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Fix console encoding on Windows (GBK -> UTF-8)
# Without this, print() crashes on characters like emoji/CJK that GBK can't encode.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        if hasattr(_stream, "buffer"):
            setattr(
                sys,
                _stream_name,
                io.TextIOWrapper(_stream.buffer, encoding="utf-8", errors="replace"),
            )
    # Also set stdin to UTF-8 for consistent encoding
    if hasattr(sys.stdin, "buffer"):
        sys.stdin = io.TextIOWrapper(
            sys.stdin.buffer, encoding="utf-8", errors="replace"
        )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIFY_API_BASE = "https://service.mify.mioffice.cn/api/v1"
MIFY_CONSOLE_API_BASE = "https://service.mify.mioffice.cn/console/api"
MIFY_SETTINGS_URL = (
    "https://mify.mioffice.cn/datasets/create?show-accountsetting=data-source"
)

# Feishu OAuth constants (from Mify's registered Feishu app)
_FEISHU_MIFY_APP_ID = "cli_a784ec0ed578d063"
_FEISHU_AUTH_CALLBACK = "http://lark-auth.c5-cloudml.xiaomi.srv/v2/lark_auth/set_auth"

MIFY_DIR = ".mify"
CONFIG_FILE = "config.json"
REGISTRY_FILE = "kb-registry.json"
STATE_DIR = "state"

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".html", ".xlsx", ".docx", ".csv"}

# ---------------------------------------------------------------------------
# Project root (.mify always lives in cwd)
# ---------------------------------------------------------------------------

# Module-level active profile name — set by load_config(), used as default
# by path helpers that don't receive an explicit profile_name.
_current_profile = None


def _mify_dir():
    """Return the .mify/ directory path under cwd."""
    return Path.cwd() / MIFY_DIR


def _global_mify_dir():
    """Return the ~/.mify/ directory path (global user config)."""
    return Path.home() / MIFY_DIR


def _global_state_dir(profile_name=None):
    """Return ~/.mify/state/{profile_name}/ for space-level state files.

    Space-level data (registry, feishu crawl cache) lives here so it's
    shared across all projects using the same profile.
    Falls back to _current_profile, then '_legacy' if neither is set.
    """
    pname = profile_name or _current_profile or "_legacy"
    return _global_mify_dir() / STATE_DIR / pname


def _profile_state_dir(profile_name=None):
    """Return .mify/state/{profile_name}/ under cwd.

    Project-level data (local file tracking) lives here.
    Falls back to _current_profile, then '_legacy' if neither is set.
    """
    pname = profile_name or _current_profile or "_legacy"
    return _mify_dir() / STATE_DIR / pname


_NEW_GITIGNORE_CONTENT = "state/**/*.tmp\n"
_OLD_GITIGNORE_PATTERNS = {"state/", "state/\n"}


def _ensure_mify_dir():
    """Create .mify/ if needed; auto-write .gitignore on first creation.

    New projects get 'state/**/*.tmp' (only ignore temp files, allow local
    file tracking to be committed). Old projects with 'state/' are migrated.
    """
    mify = _mify_dir()
    mify.mkdir(parents=True, exist_ok=True)
    gitignore = mify / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(_NEW_GITIGNORE_CONTENT, encoding="utf-8")
    else:
        # Migrate old gitignore that blocked all state files
        content = gitignore.read_text(encoding="utf-8")
        if content.strip() in ("state/", "state"):
            gitignore.write_text(_NEW_GITIGNORE_CONTENT, encoding="utf-8")
    return mify


# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------


def load_global_config():
    """Load ~/.mify/config.json. Returns {} if missing (not an error)."""
    path = _global_mify_dir() / CONFIG_FILE
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_config(global_cfg, project_cfg):
    """Merge global and project configs. Project fields override global.

    Special rule: 'email' is always taken from global_cfg only — the
    project config's 'email' field (if any) is silently ignored.
    Returns merged dict.
    """
    merged = {**global_cfg, **project_cfg}
    # Email must come from global config only
    global_email = global_cfg.get("email", "").strip() or None
    merged["email"] = global_email
    return merged


def resolve_profile(profile_name=None, merged_cfg=None, silent=False):
    """Resolve a profile name to credentials {api_key, email, profile_name}.

    Reads the "profiles" dict from merged_cfg (loaded from ~/.mify/config.json)
    to find the api_key for the given profile name.
    Email comes from merged_cfg (ultimately from global ~/.mify/config.json).
    Legacy: if merged_cfg contains '_legacy_api_key', uses it as '_legacy' profile.

    When silent=True, no messages are printed to stdout/stderr.
    Returns None if profile is missing or api_key is invalid.
    """
    if merged_cfg is None:
        merged_cfg = {}

    # Legacy mode: api_key was in the project config directly
    legacy_api_key = merged_cfg.get("_legacy_api_key")
    if legacy_api_key:
        return {
            "api_key": legacy_api_key,
            "email": merged_cfg.get("email"),
            "profile_name": "_legacy",
        }

    pname = profile_name or merged_cfg.get("default_profile")
    if not pname:
        if not silent:
            print(
                "[ERROR] No profile configured.\n"
                "  Set 'default_profile' in .mify/config.json or ~/.mify/config.json\n"
                '  Example ~/.mify/config.json:\n'
                '  {"email": "you@example.com", "default_profile": "default-space",\n'
                '   "profiles": {"default-space": {"api_key": "dataset-xxx"}}}'
            )
        return None

    profiles = merged_cfg.get("profiles", {})
    profile_data = profiles.get(pname)
    if not profile_data:
        if not silent:
            print(
                f"[ERROR] Profile '{pname}' not found in ~/.mify/config.json\n"
                f"  Add it to the 'profiles' section:\n"
                f'  "profiles": {{"{pname}": {{"api_key": "dataset-xxx"}}}}'
            )
        return None

    api_key = profile_data.get("api_key", "").strip()
    if not api_key or not api_key.startswith("dataset-"):
        if not silent:
            print(
                f"[ERROR] Profile '{pname}' has invalid api_key in ~/.mify/config.json\n"
                "  api_key must start with 'dataset-'"
            )
        return None

    return {
        "api_key": api_key,
        "email": merged_cfg.get("email"),
        "profile_name": pname,
    }


def _emit_legacy_warning(config_path):
    """Print a one-time migration warning when legacy config format is detected."""
    warned_marker = _mify_dir() / ".legacy_warned"
    if warned_marker.exists():
        return
    print(
        f"[WARN] Legacy config format detected in {config_path}\n"
        "  'api_key' should be moved to ~/.mify/config.json under 'profiles'\n"
        "  See SKILL.md for migration steps.",
        file=sys.stderr,
    )
    try:
        _ensure_mify_dir()
        warned_marker.touch()
    except Exception:
        pass


def load_config(profile_name=None, silent=False):
    """Load and merge configuration from ~/.mify/config.json and .mify/config.json.

    Returns dict with:
        api_key (str)           - From resolved profile
        email (str|None)        - From global ~/.mify/config.json
        profile_name (str)      - Active profile name
        active_kbs (list|None)  - Active KBs for current profile (backward compat)
        active_kbs_map (dict)   - Full per-profile active_kbs map
        default_profile (str)   - Resolved default profile name
        search_profiles (list)  - Profiles to search across

    When silent=True, no messages are printed to stdout/stderr.
    Returns None if configuration is missing or invalid.
    """
    global _current_profile

    global_cfg = load_global_config()
    project_cfg_path = _mify_dir() / CONFIG_FILE

    project_cfg = {}
    if project_cfg_path.exists():
        with open(project_cfg_path, "r", encoding="utf-8") as f:
            project_cfg = json.load(f)

    if not project_cfg and not global_cfg:
        if not silent:
            print(
                "[ERROR] No configuration found.\n"
                "  Create ~/.mify/config.json with your email and profiles:\n"
                '    {"email": "you@example.com", "default_profile": "default-space",\n'
                '     "profiles": {"default-space": {"api_key": "dataset-xxx"}}}'
            )
        return None

    # Detect legacy format: api_key directly in project config
    legacy_api_key = project_cfg.get("api_key", "").strip()
    if legacy_api_key:
        if not silent:
            _emit_legacy_warning(project_cfg_path)
        merged = merge_config(global_cfg, project_cfg)
        merged["_legacy_api_key"] = legacy_api_key
        creds = resolve_profile(merged_cfg=merged, silent=silent)
        if creds is None:
            return None
        _current_profile = "_legacy"

        # Normalize active_kbs
        raw_active = project_cfg.get("active_kbs")
        if isinstance(raw_active, list):
            active_kbs = raw_active
            active_kbs_map = {"_legacy": raw_active}
        elif isinstance(raw_active, dict):
            active_kbs_map = raw_active
            active_kbs = raw_active.get("_legacy")
        else:
            active_kbs = None
            active_kbs_map = {}

        return {
            "api_key": creds["api_key"],
            "email": creds["email"],
            "profile_name": "_legacy",
            "active_kbs": active_kbs,
            "active_kbs_map": active_kbs_map,
            "default_profile": "_legacy",
            "search_profiles": ["_legacy"],
        }

    # New format: profile-based
    merged = merge_config(global_cfg, project_cfg)
    creds = resolve_profile(profile_name=profile_name, merged_cfg=merged, silent=silent)
    if creds is None:
        return None
    _current_profile = creds["profile_name"]

    # Normalize active_kbs_map
    raw_active = merged.get("active_kbs")
    if isinstance(raw_active, dict):
        active_kbs_map = raw_active
    elif isinstance(raw_active, list):
        # Old flat list at top level — treat as current profile's list
        active_kbs_map = {_current_profile: raw_active}
    else:
        active_kbs_map = {}

    # Per-profile active_kbs for backward compat (None means all allowed)
    profile_active = active_kbs_map.get(_current_profile)
    search_profiles = merged.get("search_profiles") or [_current_profile]

    return {
        "api_key": creds["api_key"],
        "email": creds["email"],
        "profile_name": _current_profile,
        "active_kbs": profile_active,
        "active_kbs_map": active_kbs_map,
        "default_profile": merged.get("default_profile", _current_profile),
        "search_profiles": search_profiles,
    }


def save_config_field(field, value):
    """Update a single field in .mify/config.json (project-level), preserving others."""
    _ensure_mify_dir()
    config_path = _mify_dir() / CONFIG_FILE
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}
    config[field] = value
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def remove_config_field(field):
    """Remove a field from .mify/config.json (project-level), preserving others."""
    config_path = _mify_dir() / CONFIG_FILE
    if not config_path.exists():
        return
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    config.pop(field, None)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def is_kb_active(config, kb):
    """Check if a KB is active (allowed for search) based on active_kbs config.

    Supports per-profile map format {"profile-name": ["KB"] | null} and
    legacy list format (auto-mapped to {"_legacy": [...]}).

    Semantics (per-profile value):
      - None (key absent or null)  → all KBs allowed
      - []   (empty list)          → NO KBs allowed (search disabled)
      - [...]                      → only listed KBs allowed
    """
    profile_name = config.get("profile_name", "_legacy")
    active_kbs_map = config.get("active_kbs_map", {})
    active_kbs = active_kbs_map.get(profile_name)

    if active_kbs is None:
        return True  # not configured → all allowed
    if not active_kbs:
        return False  # empty list → search disabled
    return kb.get("id") in active_kbs or kb.get("name") in active_kbs


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def mify_request(method, path, config, body=None, require_email=False, timeout=180):
    """
    Make an authenticated HTTP request to the Mify API.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., '/datasets')
        config: Config dict from load_config()
        body: Optional dict to send as JSON body
        require_email: If True, include X-MI-EMAIL header (raises error if not configured)
        timeout: Request timeout in seconds (default 180)

    Returns:
        Parsed JSON response dict.
    """
    url = f"{MIFY_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    if require_email:
        if not config.get("email"):
            print(
                "[ERROR] Email is required for this operation.\n"
                "  Set 'email' in .mify/config.json"
            )
            return None
        headers["X-MI-EMAIL"] = config["email"]

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(
            f"[ERROR] Mify API {method} {path}: {e.code} {e.reason}",
            file=sys.stderr,
        )
        if error_body:
            print(f"  Response: {error_body[:500]}", file=sys.stderr)
        raise
    except urllib.error.URLError as e:
        print(f"[ERROR] Mify API connection: {e.reason}", file=sys.stderr)
        raise


def upload_file(path, file_path, config, data_json=None):
    """
    Upload a file via multipart/form-data POST.

    Args:
        path: API path (e.g., '/datasets/{id}/document/create-by-file')
        file_path: Local file path to upload
        config: Config dict from load_config()
        data_json: Optional JSON string for the 'data' form field

    Returns:
        Parsed JSON response dict.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    boundary = f"----MifyUpload{os.urandom(16).hex()}"
    content_type = f"multipart/form-data; boundary={boundary}"

    body_parts = []

    # File part
    file_content = file_path.read_bytes()
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    )
    body_parts.append(file_content)
    body_parts.append(b"\r\n")

    # Data part (optional)
    if data_json is not None:
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="data"\r\n\r\n'
            f"{data_json}\r\n"
        )

    body_parts.append(f"--{boundary}--\r\n")

    # Encode all parts to bytes
    encoded = b""
    for part in body_parts:
        if isinstance(part, str):
            encoded += part.encode("utf-8")
        else:
            encoded += part

    url = f"{MIFY_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": content_type,
    }

    req = urllib.request.Request(url, data=encoded, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(
            f"[ERROR] Upload {file_path.name}: {e.code} {e.reason}",
            file=sys.stderr,
        )
        if error_body:
            print(f"  Response: {error_body[:500]}", file=sys.stderr)
        raise


# ---------------------------------------------------------------------------
# Feishu binding check & auth URL
# ---------------------------------------------------------------------------


def _console_request(method, path, config, timeout=15):
    """
    Make a request to the Mify Console API.

    NOTE: The console API requires CAS session auth (web login cookies).
    The dataset API key is NOT accepted — the server returns the CAS login
    page (HTML) instead of JSON. This function is kept as a best-effort
    probe; callers must handle None returns gracefully.

    Returns parsed JSON or None on failure.
    """
    url = f"{MIFY_CONSOLE_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            # Console API returns HTML (CAS login page) when auth fails
            if body.lstrip().startswith("<!"):
                return None
            return json.loads(body)
    except Exception:
        return None


def check_feishu_data_source(config):
    """
    Check if Feishu is bound as a data source in the current Mify workspace.

    Returns:
        True  — Feishu is bound (data source integrates list is non-empty)
        False — Feishu is NOT bound (integrates list is empty)
        None  — Could not determine (console API requires CAS session auth)
    """
    result = _console_request("GET", "/data-source/integrates", config)
    if result is None:
        return None
    data = result.get("data")
    if isinstance(data, list):
        return len(data) > 0
    return None


def build_feishu_auth_url(redirect_url=None):
    """
    Construct the Feishu OAuth authorization URL for binding Mify.

    This builds the URL directly using Mify's registered Feishu app ID
    and OAuth callback service, without needing console API access.

    Args:
        redirect_url: Where to redirect after auth (default: Mify settings page)

    Returns:
        The Feishu OAuth URL string.
    """
    if redirect_url is None:
        redirect_url = MIFY_SETTINGS_URL
    final_redirect = urllib.request.quote(redirect_url, safe="")
    callback = (
        f"{_FEISHU_AUTH_CALLBACK}"
        f"?app_id={_FEISHU_MIFY_APP_ID}"
        f"&final_redirect_url={final_redirect}"
    )
    return (
        f"https://open.feishu.cn/open-apis/authen/v1/index"
        f"?app_id={_FEISHU_MIFY_APP_ID}"
        f"&redirect_uri={urllib.request.quote(callback, safe='')}"
    )


def get_feishu_auth_url(config, redirect_url=None):
    """
    Get the Feishu OAuth authorization URL.

    First tries the console API (requires CAS session). If that fails,
    constructs the URL directly from known constants.

    Args:
        config: Config dict from load_config()
        redirect_url: URL to redirect to after auth (default: Mify settings page)

    Returns:
        The auth URL string (always returns a URL, never None).
    """
    if redirect_url is None:
        redirect_url = MIFY_SETTINGS_URL
    # Try console API first (works if user has web session)
    encoded = urllib.request.quote(redirect_url, safe="")
    result = _console_request("GET", f"/feishu/auth?redirect_url={encoded}", config)
    if result and result.get("auth_url"):
        return result["auth_url"]
    # Fallback: construct directly from known constants
    return build_feishu_auth_url(redirect_url)


# ---------------------------------------------------------------------------
# KB registry persistence
# ---------------------------------------------------------------------------


def read_kb_registry(profile_name=None):
    """Read kb-registry.json for the given profile.

    Global path: ~/.mify/state/{profile_name}/kb-registry.json
    Fallback 1: .mify/state/{profile_name}/kb-registry.json (old project path)
    Fallback 2: .mify/kb-registry.json (legacy path)
    Returns empty list if none exists.
    """
    global_path = _global_state_dir(profile_name) / REGISTRY_FILE
    if global_path.exists():
        with open(global_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback: old project-level path
    project_path = _profile_state_dir(profile_name) / REGISTRY_FILE
    if project_path.exists():
        with open(project_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Legacy fallback
    legacy_path = _mify_dir() / REGISTRY_FILE
    if legacy_path.exists():
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def write_kb_registry(registry, profile_name=None):
    """Write kb-registry.json to global state dir. Creates directories if needed."""
    state_dir = _global_state_dir(profile_name)
    state_dir.mkdir(parents=True, exist_ok=True)
    registry_path = state_dir / REGISTRY_FILE
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def refresh_registry(config):
    """Fetch latest KB list from API and update local registry. Returns the registry list."""
    result = mify_request("GET", "/datasets?page=1&limit=100", config)
    datasets = result.get("data", [])
    registry = [
        {
            "id": ds.get("id", ""),
            "name": ds.get("name", ""),
            "description": ds.get("description", ""),
            "provider": ds.get("provider", "vendor"),
            "document_count": ds.get("document_count", 0),
            "word_count": ds.get("word_count", 0),
        }
        for ds in datasets
    ]
    write_kb_registry(registry, profile_name=config.get("profile_name"))
    return registry


# ---------------------------------------------------------------------------
# Per-KB state persistence
# ---------------------------------------------------------------------------


def read_kb_state(kb_id, profile_name=None):
    """Read per-KB state file for the given profile.

    New path: .mify/state/{profile_name}/{kb_id}.json
    Legacy fallback: .mify/state/{kb_id}.json
    Returns default empty state if neither exists.
    """
    new_path = _profile_state_dir(profile_name) / f"{kb_id}.json"
    if new_path.exists():
        with open(new_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Legacy fallback (read-only)
    legacy_path = _mify_dir() / STATE_DIR / f"{kb_id}.json"
    if legacy_path.exists():
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"kb_id": kb_id, "kb_name": "", "documents": {}}


def write_kb_state(kb_id, state, profile_name=None):
    """Write per-KB state file atomically via temp file + rename.

    Always writes to new per-profile path: .mify/state/{profile_name}/{kb_id}.json
    Creates directories if needed.
    """
    state_dir = _profile_state_dir(profile_name)
    state_dir.mkdir(parents=True, exist_ok=True)
    _ensure_mify_dir()
    target = state_dir / f"{kb_id}.json"

    fd, tmp_path = tempfile.mkstemp(dir=str(state_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        # On Windows, remove target first if it exists (rename doesn't overwrite)
        if target.exists():
            target.unlink()
        os.rename(tmp_path, str(target))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Feishu URL helpers
# ---------------------------------------------------------------------------

# Regex to extract URL type and token from Feishu URLs
# Matches: https://*.feishu.cn/{type}/{token}  where type is wiki/docx/doc/etc.
_FEISHU_URL_RE = re.compile(
    r"https?://[^/]*feishu\.cn/(?P<url_type>wiki|docx|doc|drive/folder)/(?P<token>[A-Za-z0-9_-]+)"
)

# Doc types that the Mify create-by-feishu-url API supports
FEISHU_SUPPORTED_DOC_TYPES = {"docx", "doc"}

# Max depth for recursive wiki container expansion
MAX_WIKI_CRAWL_DEPTH = 4

# Regex to extract the Feishu domain (e.g., https://xxx.feishu.cn)
_FEISHU_DOMAIN_RE = re.compile(r"(https?://[^/]*feishu\.cn)")


def extract_feishu_domain(url):
    """
    Extract the Feishu domain from a URL.

    Returns domain string (e.g., 'https://xxx.feishu.cn') or None.
    """
    m = _FEISHU_DOMAIN_RE.search(url)
    return m.group(1) if m else None


def build_wiki_url(base_url, token):
    """
    Construct a Feishu wiki URL from a base URL and wiki node token.

    Returns URL string or None if domain cannot be extracted.
    """
    domain = extract_feishu_domain(base_url)
    if domain:
        return f"{domain}/wiki/{token}"
    return None


def extract_feishu_token(url):
    """
    Extract URL type and token from a Feishu URL.

    Returns (url_type, token) or (None, None) if not a valid Feishu URL.
    url_type is one of: wiki, docx, doc, drive/folder
    """
    m = _FEISHU_URL_RE.search(url)
    if not m:
        return None, None
    return m.group("url_type"), m.group("token")


def feishu_crawl_state_path(token, profile_name=None):
    """Return path to feishu crawl state file (global).

    Global path: ~/.mify/state/{profile_name}/feishu-{token}.json
    """
    return _global_state_dir(profile_name) / f"feishu-{token}.json"


def _feishu_crawl_state_project_path(token, profile_name=None):
    """Return old project-level path .mify/state/{profile_name}/feishu-{token}.json."""
    return _profile_state_dir(profile_name) / f"feishu-{token}.json"


def _feishu_crawl_state_legacy_path(token):
    """Return legacy path .mify/state/feishu-{token}.json."""
    return _mify_dir() / STATE_DIR / f"feishu-{token}.json"


def read_feishu_crawl_state(token, profile_name=None):
    """Read feishu crawl state for the given profile.

    Global path: ~/.mify/state/{profile_name}/feishu-{token}.json
    Fallback 1: .mify/state/{profile_name}/feishu-{token}.json (old project path)
    Fallback 2: .mify/state/feishu-{token}.json (legacy path)
    Returns the state dict or None if not found.
    """
    global_path = feishu_crawl_state_path(token, profile_name)
    if global_path.exists():
        with open(global_path, "r", encoding="utf-8") as f:
            return json.load(f)
    project_path = _feishu_crawl_state_project_path(token, profile_name)
    if project_path.exists():
        with open(project_path, "r", encoding="utf-8") as f:
            return json.load(f)
    legacy_path = _feishu_crawl_state_legacy_path(token)
    if legacy_path.exists():
        with open(legacy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_feishu_crawl_state(token, state, profile_name=None):
    """Write feishu crawl state atomically to the global state dir.

    Always writes to: ~/.mify/state/{profile_name}/feishu-{token}.json
    Creates directories if needed.
    """
    state_dir = _global_state_dir(profile_name)
    state_dir.mkdir(parents=True, exist_ok=True)
    target = feishu_crawl_state_path(token, profile_name)

    fd, tmp_path = tempfile.mkstemp(dir=str(state_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        if target.exists():
            target.unlink()
        os.rename(tmp_path, str(target))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Crawl cache expiration & diff
# ---------------------------------------------------------------------------

# Crawl cache expires after 3 days (72 hours)
CRAWL_CACHE_MAX_AGE_SECONDS = 3 * 24 * 3600


def is_crawl_cache_expired(state):
    """Check if a feishu crawl cache has expired (older than 3 days).

    Args:
        state: Crawl state dict (must have 'crawled_at' ISO timestamp).

    Returns:
        (expired: bool, age_days: int|None)
    """
    crawled_at = state.get("crawled_at") if state else None
    if not crawled_at:
        return True, None
    try:
        from datetime import datetime, timezone
        crawl_time = datetime.fromisoformat(crawled_at)
        if crawl_time.tzinfo is None:
            crawl_time = crawl_time.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - crawl_time).total_seconds()
        age_days = int(age / 86400)
        return age > CRAWL_CACHE_MAX_AGE_SECONDS, age_days
    except (ValueError, TypeError):
        return True, None


def compute_crawl_diff(old_docs, new_docs):
    """Compare two crawl doc lists by doc_token and return a diff summary.

    Returns dict: {added: int, removed: int, unchanged: int}
    """
    def _token_set(docs):
        tokens = set()
        for d in docs:
            t = d.get("doc_token") or d.get("token")
            if t:
                tokens.add(t)
        return tokens

    old_tokens = _token_set(old_docs)
    new_tokens = _token_set(new_docs)
    return {
        "added": len(new_tokens - old_tokens),
        "removed": len(old_tokens - new_tokens),
        "unchanged": len(old_tokens & new_tokens),
    }


def clean_crawl_docs(docs):
    """
    Filter crawl results: keep only supported doc types, strip null values.
    Returns (clean_docs, skipped, auth_errors) tuple.
    Skipped items include url/token for potential re-crawling of wiki containers.
    Auth errors are docs with unauthorized_in_saas_feishu or status=fail.
    """
    clean = []
    skipped = []
    auth_errors = []
    for d in docs:
        # Check for SaaS authorization failures first
        if d.get("unauthorized_in_saas_feishu") or d.get("status") == "fail":
            auth_errors.append(
                {
                    "url": d.get("url", ""),
                    "error": d.get("error", "unknown error"),
                    "view_permission": d.get("view_permission", False),
                    "unauthorized_in_saas_feishu": d.get(
                        "unauthorized_in_saas_feishu", False
                    ),
                }
            )
            continue

        if d.get("doc_type") in FEISHU_SUPPORTED_DOC_TYPES:
            clean.append({k: v for k, v in d.items() if v is not None})
        else:
            entry = {
                "title": d.get("title", ""),
                "doc_type": d.get("doc_type", "unknown"),
                "reason": "unsupported type",
            }
            # Preserve URL and token for re-crawling wiki container children
            if d.get("url"):
                entry["url"] = d["url"]
            tok = d.get("token") or d.get("doc_token")
            if tok:
                entry["token"] = tok
            skipped.append(entry)
    return clean, skipped, auth_errors


# ---------------------------------------------------------------------------
# KB resolution
# ---------------------------------------------------------------------------


def resolve_kb(name_or_id, profile_name=None):
    """Look up a KB by name or ID from the registry.

    Returns dict with id, name, provider, or None if not found.
    """
    registry = read_kb_registry(profile_name)
    for kb in registry:
        if kb.get("id") == name_or_id or kb.get("name") == name_or_id:
            return kb
    print(
        f"[ERROR] Knowledge base '{name_or_id}' not found in registry.\n"
        f"  Run list_knowledge_bases.py first to refresh the registry."
    )
    return None


# ---------------------------------------------------------------------------
# Remote document management
# ---------------------------------------------------------------------------


def list_remote_documents(kb_id, config):
    """Fetch all documents in a KB from the remote API, handling pagination.

    Calls GET /datasets/{kb_id}/documents with limit=100, looping until
    has_more is False. Returns a list of document dicts with at minimum:
      id, name, indexing_status, data_source_type, created_at
    """
    docs = []
    page = 1
    while True:
        result = mify_request(
            "GET",
            f"/datasets/{kb_id}/documents?page={page}&limit=100",
            config,
        )
        batch = result.get("data", [])
        docs.extend(batch)
        if not result.get("has_more", False):
            break
        page += 1
    return docs


def delete_document(kb_id, doc_id, config):
    """Delete a document from a KB via DELETE /datasets/{kb_id}/documents/{doc_id}.

    Returns True on success (204). Raises on error.
    """
    url = f"{MIFY_API_BASE}/datasets/{kb_id}/documents/{doc_id}"
    headers = {"Authorization": f"Bearer {config['api_key']}"}
    req = urllib.request.Request(url, headers=headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            # 204 No Content — success
            _ = resp.read()
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Document '{doc_id}' not found in KB '{kb_id}'") from e
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(
            f"[ERROR] Delete document {doc_id}: {e.code} {e.reason}",
            file=sys.stderr,
        )
        if error_body:
            print(f"  Response: {error_body[:500]}", file=sys.stderr)
        raise


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------


def compute_file_hash(file_path):
    """Compute SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Indexing status polling
# ---------------------------------------------------------------------------

POLL_INTERVAL = 3  # seconds
POLL_TIMEOUT = 300  # 5 minutes


def poll_indexing_status(config, kb_id, batch, doc_name=""):
    """
    Poll indexing status until completed, error, or timeout.

    Args:
        config: Config dict from load_config()
        kb_id: Knowledge base ID
        batch: Batch number from upload response (not document ID)
        doc_name: Human-readable label for progress output

    Returns final status string.
    """
    label = doc_name or batch
    start = time.time()

    while time.time() - start < POLL_TIMEOUT:
        try:
            result = mify_request(
                "GET",
                f"/datasets/{kb_id}/documents/{batch}/indexing-status",
                config,
            )
            data = result.get("data", [])
            if data:
                status = data[0].get("indexing_status", "")
            else:
                status = result.get("indexing_status", "unknown")

            if status == "completed":
                print(f"  [OK] {label}: indexing completed")
                return "completed"
            elif status == "error":
                err = data[0].get("error", "") if data else "unknown"
                print(f"  [ERROR] {label}: indexing failed — {err}")
                return "error"
            else:
                elapsed = int(time.time() - start)
                print(f"  ... {label}: {status} ({elapsed}s)", end="\r")
                time.sleep(POLL_INTERVAL)
        except Exception as e:
            print(f"  [WARN] {label}: poll error — {e}")
            time.sleep(POLL_INTERVAL)

    print(f"\n  [WARN] {label}: polling timeout after {POLL_TIMEOUT}s")
    return "timeout"


# ---------------------------------------------------------------------------
# Feishu SaaS authorization error detection
# ---------------------------------------------------------------------------

# Keywords in HTTP error response bodies that indicate authorization issues
_AUTH_ERROR_KEYWORDS = [
    "no permission",
    "not authorized",
    "tenant not authorized",
    "permission denied",
    "access denied",
]


def is_feishu_auth_error(http_error):
    """
    Check if an urllib.error.HTTPError indicates a Feishu SaaS authorization failure.

    Returns (True, status_code, response_body) if auth error, else (False, None, None).
    """
    if not isinstance(http_error, urllib.error.HTTPError):
        return False, None, None

    status = http_error.code
    body = ""
    if http_error.fp:
        try:
            body = http_error.fp.read().decode("utf-8", errors="replace")
        except Exception:
            pass

    if status in (401, 403):
        return True, status, body

    if status == 400:
        body_lower = body.lower()
        if any(kw in body_lower for kw in _AUTH_ERROR_KEYWORDS):
            return True, status, body

    return False, None, None


# Placeholder URL for binding check — doesn't need to point to a real document.
# The crawl API returns unauthorized_in_saas_feishu when binding is missing.
# When binding IS valid, the API returns a "not found" error (code 131005)
# because the probe URL doesn't exist — this is the expected success signal.
_FEISHU_BINDING_PROBE_URL = "https://mi.feishu.cn/wiki/feishu_binding_probe"

# Error codes/messages that indicate "document not found" (NOT auth failure).
# Receiving these from the probe URL means auth succeeded — the API was able
# to query Feishu but the fake document simply doesn't exist.
_NOT_FOUND_INDICATORS = ["not found", "131005", "node not exist"]


def verify_feishu_auth(config):
    """
    Verify Feishu authorization by attempting a test crawl.

    Performs a lightweight crawl request to check if the Mify workspace
    has valid Feishu data-source binding. Uses a placeholder URL:
    - If binding is MISSING: the API returns unauthorized_in_saas_feishu → bound=False
    - If binding is VALID: the API returns "not found" (code 131005)
      because the probe URL doesn't exist → bound=True

    Args:
        config: Config dict from load_config()

    Returns:
        dict with keys:
            bound (bool): True if auth works, False if auth error
            error (str|None): Error description if not bound
            auth_url (str|None): OAuth URL to fix binding if not bound
    """
    test_url = _FEISHU_BINDING_PROBE_URL
    try:
        result = mify_request(
            "POST",
            "/datasets/feishu/crawl",
            config,
            body={"urls": [test_url]},
            require_email=True,
            timeout=30,
        )
        # Check for inline auth errors in crawl results
        raw_docs = result.get("docs", [])
        for d in raw_docs:
            # Explicit SaaS auth failure → binding is missing
            if d.get("unauthorized_in_saas_feishu"):
                auth_url = get_feishu_auth_url(config)
                error_msg = d.get("error", "unauthorized in SaaS Feishu")
                return {"bound": False, "error": error_msg, "auth_url": auth_url}

            # status "fail" needs further inspection
            if d.get("status") == "fail":
                error_str = str(d.get("error", ""))
                error_lower = error_str.lower()
                # "not found" / 131005 → auth succeeded, probe URL just doesn't exist
                if any(ind in error_lower for ind in _NOT_FOUND_INDICATORS):
                    # This is the expected response — auth is working
                    return {"bound": True, "error": None, "auth_url": None}
                # Other failures may indicate auth issues
                auth_url = get_feishu_auth_url(config)
                return {"bound": False, "error": error_str, "auth_url": auth_url}

        # No auth errors at all → binding works
        return {"bound": True, "error": None, "auth_url": None}
    except urllib.error.HTTPError as e:
        is_auth, status, body = is_feishu_auth_error(e)
        if is_auth:
            auth_url = get_feishu_auth_url(config)
            return {
                "bound": False,
                "error": f"HTTP {status}: {body[:200]}",
                "auth_url": auth_url,
            }
        # Non-auth HTTP errors (e.g., 500 with "not found") may also indicate
        # that auth works but the probe URL is invalid
        body = ""
        if e.fp:
            try:
                body = e.fp.read().decode("utf-8", errors="replace")
            except Exception:
                pass
        body_lower = body.lower()
        if any(ind in body_lower for ind in _NOT_FOUND_INDICATORS):
            return {"bound": True, "error": None, "auth_url": None}
        return {
            "bound": False,
            "error": f"HTTP {e.code}: {body[:200]}" if body else str(e),
            "auth_url": get_feishu_auth_url(config),
        }
    except Exception as e:
        return {
            "bound": False,
            "error": str(e),
            "auth_url": get_feishu_auth_url(config),
        }


def print_feishu_auth_guidance(url, status_or_error, response_body="", config=None):
    """
    Print structured guidance for resolving Feishu SaaS authorization errors.

    Uses the Feishu OAuth URL (which completes binding via redirect chain) as
    primary action. Falls back to the Mify settings page if OAuth URL cannot
    be generated.

    Args:
        url: The Feishu URL that triggered the error
        status_or_error: HTTP status code (int) or error message string
        response_body: Optional response body for additional context
        config: Config dict — used to generate the OAuth URL
    """
    # Primary: Feishu OAuth URL (redirect chain completes binding automatically)
    auth_url = None
    if config:
        try:
            auth_url = get_feishu_auth_url(config)
        except Exception:
            pass
    # Fallback: Mify settings page (manual binding via UI)
    action_url = auth_url or MIFY_SETTINGS_URL

    debug_line = f"\n  Debug info: {status_or_error}" + (
        f"\n  Response: {response_body[:500]}"
        if response_body and response_body != str(status_or_error)
        else ""
    )

    print(
        f"\n  [AUTH] Feishu authorization required for: {url}\n"
        f"  The Mify app does not have access to this Feishu tenant's documents.\n"
        f"\n"
        f"  === Method 1: OAuth URL (recommended) ===\n"
        f"  Step 1: Open the following link in your browser:\n"
        f"  {action_url}\n"
        f"  Step 2: On the Feishu page, click '授权' to authorize.\n"
        f"  Step 3: Wait for the page to redirect back to Mify.\n"
        f"  Step 4: Re-run the crawl command to continue.\n"
        f"\n"
        f"  === Method 2: Mify settings page (fallback) ===\n"
        f"  Step 1: Open: {MIFY_SETTINGS_URL}\n"
        f"  Step 2: In the '飞书文档' section, click '添加工作空间'.\n"
        f"  Step 3: A popup will appear — click '同意' to grant access.\n"
        f"  Step 4: You will be redirected to the Feishu OAuth page — click '授权'.\n"
        f"  Step 5: Wait for the page to redirect back to Mify.\n"
        f"  Step 6: Re-run the crawl command to continue.\n"
        f"{debug_line}",
        flush=True,
    )
