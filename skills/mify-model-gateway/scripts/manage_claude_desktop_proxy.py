#!/usr/bin/env python3
"""Install and operate the local Claude Desktop proxy for non-Claude Mify models."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


LABEL = "com.local.mify-claude-desktop-proxy"
SCRIPT_DIR = Path(__file__).resolve().parent
PROXY_SCRIPT = SCRIPT_DIR / "claude_desktop_proxy.py"
INSTALL_COWORK = SCRIPT_DIR / "install_cowork_config.py"
CONFIG_DIR = Path.home() / ".config/mify/claude-desktop-proxy"
TLS_DIR = CONFIG_DIR / "tls"
MODELS_FILE = CONFIG_DIR / "models.json"
STATE_FILE = CONFIG_DIR / "state.json"
PLIST_PATH = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
LOG_DIR = Path.home() / "Library/Logs/mify-claude-desktop-proxy"
DEFAULT_PORT = 41414
DEFAULT_SCHEME = "http"
GATEWAY_PLACEHOLDER_KEY = "local-proxy-placeholder"

PUBLIC_MODELS = [
    {"name": "ppio/pa/claude-opus-4-7", "supports1m": True},
    {"name": "ppio/pa/claude-opus-4-6", "supports1m": True},
    {"name": "ppio/pa/claude-sonnet-4-6", "supports1m": True},
    {"name": "ppio/pa/claude-haiku-4-5", "supports1m": True},
    {"name": "xisheng/claude-opus-4-7", "supports1m": True},
    {"name": "xisheng/claude-sonnet-4-6", "supports1m": True},
    {"name": "xisheng/claude-haiku-4-5", "supports1m": True},
]


def public_model_names(model_maps: list[str] | None = None) -> list[str]:
    names = [item["name"] for item in PUBLIC_MODELS]
    for item in model_maps or []:
        if "=" not in item:
            raise SystemExit(f"Invalid --model-map {item!r}; expected external=upstream")
        external = item.split("=", 1)[0].strip()
        if external and external not in names:
            names.append(external)
    return names


def public_model_entries(model_maps: list[str] | None = None) -> list[dict[str, object]]:
    by_name = {item["name"]: dict(item) for item in PUBLIC_MODELS}
    for name in public_model_names(model_maps):
        by_name.setdefault(name, {"name": name, "supports1m": True})
    return [by_name[name] for name in public_model_names(model_maps)]


def run(cmd: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if check and result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("MIFY_API_KEY", None)
    return run(["launchctl", *args], check=False, env=env)


def base_url(port: int, scheme: str = DEFAULT_SCHEME) -> str:
    return f"{scheme}://localhost:{port}"


def read_state_port(default: int = DEFAULT_PORT) -> int:
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        port = int(data.get("port", default))
        if 1 <= port <= 65535:
            return port
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return default


def read_state_scheme(default: str = DEFAULT_SCHEME) -> str:
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        scheme = data.get("scheme")
        if scheme in {"http", "https"}:
            return scheme
    except (OSError, TypeError, json.JSONDecodeError):
        pass

    # Legacy state files only stored base_url. Prefer the actual LaunchAgent
    # args when present so a manual HTTP migration is not masked by stale state.
    try:
        if PLIST_PATH.exists():
            plist = plistlib.loads(PLIST_PATH.read_bytes())
            program = plist.get("ProgramArguments", [])
            if isinstance(program, list):
                if "--cert-file" in program or "--key-file" in program:
                    return "https"
                if any(str(item).endswith("claude_desktop_proxy.py") for item in program):
                    return "http"
    except (OSError, plistlib.InvalidFileException, TypeError):
        pass

    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        url = str(data.get("base_url", ""))
        if url.startswith("http://"):
            return "http"
        if url.startswith("https://"):
            return "https"
    except (OSError, TypeError, json.JSONDecodeError):
        pass
    return default


def write_state(port: int, scheme: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"port": port, "scheme": scheme, "base_url": base_url(port, scheme)}, indent=2) + "\n",
        encoding="utf-8",
    )
    STATE_FILE.chmod(0o600)


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def select_port(preferred: int) -> int:
    if port_available(preferred):
        return preferred
    for port in range(preferred + 1, preferred + 101):
        if port_available(port):
            return port
    raise SystemExit(f"No available localhost port found in {preferred}-{preferred + 100}")


def ensure_tls(trust: bool) -> None:
    TLS_DIR.mkdir(parents=True, exist_ok=True)
    ca_key = TLS_DIR / "ca.key"
    ca_crt = TLS_DIR / "ca.crt"
    server_key = TLS_DIR / "server.key"
    server_csr = TLS_DIR / "server.csr"
    server_crt = TLS_DIR / "server.crt"
    ca_conf = TLS_DIR / "ca.cnf"
    server_conf = TLS_DIR / "server.cnf"
    ext = TLS_DIR / "server.ext"

    def verifies(cert: Path) -> bool:
        if not ca_crt.exists() or not cert.exists():
            return False
        return run(["openssl", "verify", "-CAfile", str(ca_crt), str(cert)], check=False).returncode == 0

    regenerate_server = False
    if not ca_key.exists() or not verifies(ca_crt):
        ca_conf.write_text(
            "[ req ]\n"
            "prompt = no\n"
            "distinguished_name = dn\n"
            "x509_extensions = v3_ca\n"
            "\n"
            "[ dn ]\n"
            "CN = Mify Claude Desktop Local Proxy CA\n"
            "\n"
            "[ v3_ca ]\n"
            "subjectKeyIdentifier = hash\n"
            "authorityKeyIdentifier = keyid:always,issuer\n"
            "basicConstraints = critical, CA:true, pathlen:0\n"
            "keyUsage = critical, keyCertSign, cRLSign\n",
            encoding="utf-8",
        )
        run(["openssl", "genrsa", "-out", str(ca_key), "4096"])
        run(
            [
                "openssl",
                "req",
                "-x509",
                "-new",
                "-nodes",
                "-key",
                str(ca_key),
                "-sha256",
                "-days",
                "3650",
                "-config",
                str(ca_conf),
                "-out",
                str(ca_crt),
            ]
        )
        regenerate_server = True

    if regenerate_server or not verifies(server_crt):
        server_conf.write_text(
            "[ req ]\n"
            "prompt = no\n"
            "distinguished_name = dn\n"
            "req_extensions = v3_req\n"
            "\n"
            "[ dn ]\n"
            "CN = localhost\n"
            "\n"
            "[ v3_req ]\n"
            "subjectAltName = @alt_names\n"
            "\n"
            "[ alt_names ]\n"
            "DNS.1 = localhost\n"
            "IP.1 = 127.0.0.1\n",
            encoding="utf-8",
        )
        ext.write_text(
            "authorityKeyIdentifier=keyid,issuer\n"
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            "subjectAltName=DNS:localhost,IP:127.0.0.1\n",
            encoding="utf-8",
        )
        run(["openssl", "genrsa", "-out", str(server_key), "2048"])
        run(["openssl", "req", "-new", "-key", str(server_key), "-config", str(server_conf), "-out", str(server_csr)])
        run(
            [
                "openssl",
                "x509",
                "-req",
                "-in",
                str(server_csr),
                "-CA",
                str(ca_crt),
                "-CAkey",
                str(ca_key),
                "-CAcreateserial",
                "-out",
                str(server_crt),
                "-days",
                "825",
                "-sha256",
                "-extfile",
                str(ext),
            ]
        )
        if not verifies(server_crt):
            raise SystemExit("Generated localhost TLS certificate failed verification")
    ca_key.chmod(0o600)
    server_key.chmod(0o600)

    if trust:
        run(
            [
                "security",
                "add-trusted-cert",
                "-d",
                "-r",
                "trustRoot",
                "-k",
                str(Path.home() / "Library/Keychains/login.keychain-db"),
                str(ca_crt),
            ]
        )


def write_models_file(model_maps: list[str] | None = None) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_FILE.write_text(json.dumps(public_model_entries(model_maps), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MODELS_FILE.chmod(0o600)


def write_plist(port: int, scheme: str, model_maps: list[str] | None = None) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    program = [
        "/usr/bin/env",
        "-u",
        "MIFY_API_KEY",
        sys.executable,
        str(PROXY_SCRIPT),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if scheme == "https":
        program.extend(["--cert-file", str(TLS_DIR / "server.crt"), "--key-file", str(TLS_DIR / "server.key")])
    for model_name in public_model_names(model_maps):
        program.extend(["--public-model", model_name])
    for item in model_maps or []:
        program.extend(["--model-map", item])

    plist = {
        "Label": LABEL,
        "ProgramArguments": program,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(LOG_DIR / "proxy.out.log"),
        "StandardErrorPath": str(LOG_DIR / "proxy.err.log"),
        "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")},
        "WorkingDirectory": str(SCRIPT_DIR),
    }
    PLIST_PATH.write_bytes(plistlib.dumps(plist, sort_keys=False))


def configure_desktop(apply: bool, port: int, scheme: str, model_maps: list[str] | None = None) -> None:
    write_models_file(model_maps)
    cmd = [
        sys.executable,
        str(INSTALL_COWORK),
        "--base-url",
        base_url(port, scheme),
        "--api-key",
        GATEWAY_PLACEHOLDER_KEY,
        "--models-file",
        str(MODELS_FILE),
    ]
    if apply:
        cmd.append("--apply")
    result = run(cmd, check=False)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def health(port: int, scheme: str) -> tuple[bool, str]:
    # Liveness check only: the proxy is loopback-only, and older generated CA
    # certs may be trusted by Keychain/curl but rejected by Python's stricter
    # key-usage validation.
    context = ssl._create_unverified_context()
    try:
        url = f"{base_url(port, scheme)}/healthz"
        if scheme == "https":
            response_ctx = {"context": context}
        else:
            response_ctx = {}
        with urllib.request.urlopen(url, timeout=3, **response_ctx) as response:
            return True, response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def start(port: int | None = None, scheme: str | None = None) -> None:
    port = read_state_port() if port is None else port
    scheme = read_state_scheme() if scheme is None else scheme
    if not PLIST_PATH.exists():
        raise SystemExit(f"No plist found at {PLIST_PATH}. Run install --apply first.")
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode != 0:
        result = launchctl("bootstrap", f"gui/{os.getuid()}", str(PLIST_PATH))
        if result.returncode != 0:
            print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
            raise SystemExit(result.returncode)
    result = launchctl("kickstart", "-k", f"gui/{os.getuid()}/{LABEL}")
    if result.returncode != 0:
        print(result.stderr.strip() or result.stdout.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    for _ in range(10):
        ok, _detail = health(port, scheme)
        if ok:
            print(f"started: {LABEL}")
            print(f"healthz: ok {base_url(port, scheme)}/healthz")
            return
        time.sleep(0.5)
    ok, detail = health(port, scheme)
    print(f"started: {LABEL}")
    print(f"healthz: {'ok' if ok else 'failed'} {base_url(port, scheme)}/healthz")
    if detail.strip():
        print(detail.strip())


def stop() -> None:
    launchctl("bootout", f"gui/{os.getuid()}", str(PLIST_PATH))
    print(f"stopped: {LABEL}")


def restart(port: int | None = None, scheme: str | None = None) -> None:
    stop()
    time.sleep(0.5)
    start(port, scheme)


def status(port: int | None = None, scheme: str | None = None) -> None:
    port = read_state_port() if port is None else port
    scheme = read_state_scheme() if scheme is None else scheme
    print(f"label: {LABEL}")
    print(f"plist: {PLIST_PATH} ({'exists' if PLIST_PATH.exists() else 'missing'})")
    print(f"base_url: {base_url(port, scheme)}")
    result = launchctl("print", f"gui/{os.getuid()}/{LABEL}")
    if result.returncode == 0:
        print("launchd: loaded")
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith(("path =", "state =", "pid =", "job state =")):
                print(f"  {stripped}")
    else:
        print("launchd: not loaded")
    ok, detail = health(port, scheme)
    print(f"healthz: {'ok' if ok else 'failed'} {base_url(port, scheme)}/healthz")
    if ok and result.returncode != 0:
        print("note: this port responds, but this LaunchAgent label is not loaded; it may be another local proxy.")
    if detail.strip():
        print(detail.strip())


def install(args: argparse.Namespace) -> None:
    preferred_port = args.port or read_state_port()
    scheme = args.scheme or read_state_scheme()
    if not args.apply:
        print("dry-run: would write LaunchAgent, start proxy, and write Claude Desktop config")
        if scheme == "https":
            print("dry-run: would also generate/trust localhost TLS certs")
        selected_port = preferred_port
        if not port_available(preferred_port):
            if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
                print(f"note: localhost:{preferred_port} is occupied by the current {LABEL}; install --apply will restart it and try to reuse this port.")
            else:
                selected_port = select_port(preferred_port)
                print(f"note: localhost:{preferred_port} is occupied; install --apply would use localhost:{selected_port}")
        configure_desktop(apply=False, port=selected_port, scheme=scheme, model_maps=args.model_map)
        print("\nRe-run with: manage_claude_desktop_proxy.py install --apply")
        return
    if launchctl("print", f"gui/{os.getuid()}/{LABEL}").returncode == 0:
        stop()
        time.sleep(0.5)
    selected_port = select_port(preferred_port)
    if scheme == "https":
        ensure_tls(trust=not args.no_trust_ca)
    write_plist(selected_port, scheme, args.model_map)
    write_state(selected_port, scheme)
    start(selected_port, scheme)
    configure_desktop(apply=True, port=selected_port, scheme=scheme, model_maps=args.model_map)


def uninstall() -> None:
    stop()
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        print(f"removed: {PLIST_PATH}")
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print(f"removed: {STATE_FILE}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--apply", action="store_true", help="write files and mutate Claude Desktop config")
    install_parser.add_argument("--no-trust-ca", action="store_true", help="generate certs but do not trust CA")
    install_parser.add_argument("--port", type=int, help="preferred localhost port; defaults to 41414 or prior state")
    install_parser.add_argument(
        "--scheme",
        choices=("http", "https"),
        help="localhost proxy scheme; defaults to prior state or http to avoid Electron localhost CA warnings",
    )
    install_parser.add_argument(
        "--model-map",
        action="append",
        help="optional custom map external=upstream, e.g. xisheng/claude-opus-4-7=xiaomi/mimo-v2.5-pro",
    )
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--port", type=int, help="override health-check port")
    status_parser.add_argument("--scheme", choices=("http", "https"), help="override health-check scheme")
    sub.add_parser("start")
    sub.add_parser("restart")
    sub.add_parser("stop")
    sub.add_parser("uninstall")
    sub.add_parser("configure-desktop")
    args = parser.parse_args()

    if args.command == "install":
        install(args)
    elif args.command == "status":
        status(args.port, args.scheme)
    elif args.command == "start":
        start()
    elif args.command == "restart":
        restart()
    elif args.command == "stop":
        stop()
    elif args.command == "uninstall":
        uninstall()
    elif args.command == "configure-desktop":
        configure_desktop(apply=True, port=read_state_port(), scheme=read_state_scheme())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
