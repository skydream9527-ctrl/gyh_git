#!/usr/bin/env python3
"""
Create documents in a Mify knowledge base from local files or Feishu URLs.

Usage:
    python create_documents.py local --kb "My KB" --dir ./docs
    python create_documents.py crawl --urls "https://..." "https://..."
    python create_documents.py feishu --kb "My KB" --urls "https://..." "https://..."
"""

import argparse
import json
import socket
import sys
import time
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mify_client import (
    MAX_WIKI_CRAWL_DEPTH,
    SUPPORTED_EXTENSIONS,
    build_wiki_url,
    clean_crawl_docs,
    compute_crawl_diff,
    compute_file_hash,
    extract_feishu_token,
    feishu_crawl_state_path,
    is_crawl_cache_expired,
    is_feishu_auth_error,
    list_remote_documents,
    load_config,
    mify_request,
    print_feishu_auth_guidance,
    read_feishu_crawl_state,
    read_kb_state,
    refresh_registry,
    resolve_kb,
    upload_file,
    write_feishu_crawl_state,
    write_kb_state,
)

# Max timeout allowed via CLI (1 hour)
MAX_TIMEOUT = 3600

PROCESS_RULE_CUSTOM = {
    "mode": "custom",
    "rules": {
        "pre_processing_rules": [],
        "segmentation": {
            "separator": '["#", "##", "###", "```\\n", "\\n---\\n", "\\n\\n", "\\n"]',
            "max_tokens": 1024,
        },
    },
}

# ---------------------------------------------------------------------------
# Local file upload
# ---------------------------------------------------------------------------


def cmd_local(args, config):
    """Upload local files to a knowledge base."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return
    kb_id = kb["id"]
    dir_path = Path(args.dir)

    if not dir_path.is_dir():
        print(f"[ERROR] Directory not found: {dir_path}")
        return

    # Scan for supported files
    files = sorted(
        f
        for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print(f"No supported files found in {dir_path}")
        print(f"  Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        return

    print(f"Uploading {len(files)} file(s) to KB '{kb['name']}' ({kb_id})...\n")

    state = read_kb_state(kb_id, profile_name)
    state["kb_name"] = kb["name"]

    successes = 0
    failures = 0
    data_json = json.dumps(
        {
            "indexing_technique": "high_quality",
            "doc_form": "text_model",
            "process_rule": PROCESS_RULE_CUSTOM,
        }
    )

    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f.name}...")
        try:
            result = upload_file(
                f"/datasets/{kb_id}/document/create-by-file",
                f,
                config,
                data_json=data_json,
            )
            doc = result.get("document", result)
            doc_id = doc.get("id", "")
            file_hash = compute_file_hash(f)

            state["documents"][f.name] = {
                "doc_id": doc_id,
                "source_type": "local",
                "file_hash": file_hash,
                "status": "uploaded",
            }
            write_kb_state(kb_id, state, profile_name)
            print(f"  Uploaded (doc_id: {doc_id})")
            successes += 1

            # TODO: re-enable when indexing polling timeout is resolved
            # poll_indexing_status(config, kb_id, doc_id, f.name)
        except Exception as e:
            print(f"  [ERROR] {e}")
            failures += 1

    print(f"\nDone: {successes} uploaded, {failures} failed")
    if successes > 0:
        refresh_registry(config)


# ---------------------------------------------------------------------------
# Feishu URL — create documents from crawl state
# ---------------------------------------------------------------------------


def _crawl_and_save(urls, config, timeout=180, max_depth=MAX_WIKI_CRAWL_DEPTH, profile_name=None):
    """
    Crawl Feishu URLs and save state for each URL token.
    Recursively expands unsupported wiki container nodes to find importable
    child documents (up to max_depth levels).
    Returns list of (token, state) tuples.
    """
    results = []
    total_urls = len(urls)

    for url_idx, url in enumerate(urls, 1):
        url_type, token = extract_feishu_token(url)
        if not token:
            print(f"[WARN] Cannot parse Feishu URL, skipping: {url}", flush=True)
            continue

        # Per-URL progress header
        if total_urls > 1:
            print(f"[{url_idx}/{total_urls}] Crawling {url} ...", flush=True)
        else:
            print(f"Crawling {url} ...", flush=True)

        url_start = time.time()
        all_clean_docs = []
        all_skipped_final = []
        seen_tokens = set()
        pending_urls = [url]
        crawl_round = 0

        while pending_urls:
            next_urls = []

            for crawl_url in pending_urls:
                try:
                    crawl_result = mify_request(
                        "POST",
                        "/datasets/feishu/crawl",
                        config,
                        body={"urls": [crawl_url]},
                        require_email=True,
                        timeout=timeout,
                    )
                except urllib.error.HTTPError as e:
                    is_auth, status, body = is_feishu_auth_error(e)
                    if is_auth:
                        print_feishu_auth_guidance(
                            crawl_url, status, body, config=config
                        )
                    else:
                        print(
                            f"  [ERROR] Crawl failed for {crawl_url}: {e}",
                            file=sys.stderr,
                            flush=True,
                        )
                    continue
                except (socket.timeout, urllib.error.URLError) as e:
                    reason = str(getattr(e, "reason", e))
                    if "timed out" in reason.lower() or isinstance(e, socket.timeout):
                        print(
                            f"  [WARN] Request timed out after {timeout}s for {crawl_url}. "
                            f"Try: --timeout {timeout * 2}",
                            flush=True,
                        )
                    else:
                        print(
                            f"  [ERROR] Crawl failed for {crawl_url}: {e}",
                            file=sys.stderr,
                            flush=True,
                        )
                    continue
                except Exception as e:
                    print(
                        f"  [ERROR] Crawl failed for {crawl_url}: {e}",
                        flush=True,
                    )
                    continue

                if crawl_result is None:
                    continue

                raw_docs = crawl_result.get("docs", [])
                if not raw_docs:
                    continue

                clean_docs, skipped, auth_errors = clean_crawl_docs(raw_docs)

                # Handle SaaS authorization errors
                if auth_errors:
                    for ae in auth_errors:
                        print_feishu_auth_guidance(
                            ae.get("url", crawl_url),
                            ae.get("error", ""),
                            ae.get("error", ""),
                            config=config,
                        )
                    # Don't try to re-crawl children of an unauthorized node
                    continue

                # Add new clean docs (deduplicate by token)
                for d in clean_docs:
                    t = d.get("doc_token") or d.get("token")
                    if t and t not in seen_tokens:
                        seen_tokens.add(t)
                        all_clean_docs.append(d)
                    elif not t:
                        all_clean_docs.append(d)

                # Check skipped items for wiki containers to expand
                for s in skipped:
                    t = s.get("token")
                    if t and t in seen_tokens:
                        continue  # Already processed
                    if t:
                        seen_tokens.add(t)

                    # Try to construct a wiki URL for re-crawling children
                    child_url = build_wiki_url(url, t) if t else None
                    if child_url:
                        next_urls.append(child_url)
                    else:
                        all_skipped_final.append(s)

            pending_urls = next_urls
            crawl_round += 1

            if not next_urls:
                break

            if crawl_round >= max_depth:
                print(
                    f"  [WARN] Max crawl depth ({max_depth}) reached, "
                    f"{len(next_urls)} container(s) not expanded. "
                    f"Try: --max-depth {max_depth * 2} to crawl deeper",
                    flush=True,
                )
                for child_url in next_urls:
                    all_skipped_final.append(
                        {
                            "url": child_url,
                            "doc_type": "unknown",
                            "reason": "max crawl depth reached",
                        }
                    )
                break

            elapsed = int(time.time() - url_start)
            print(
                f"  Round {crawl_round}/{max_depth}: expanding {len(next_urls)} container(s), "
                f"{len(all_clean_docs)} doc(s) found so far (elapsed: {elapsed}s)",
                flush=True,
            )

        # Per-URL summary
        elapsed = int(time.time() - url_start)
        if not all_clean_docs:
            print("  No supported documents found.", flush=True)
            if all_skipped_final:
                print(
                    f"  ({len(all_skipped_final)} unsupported node(s) could not be expanded)",
                    flush=True,
                )
            continue

        state = {
            "url": url,
            "url_type": url_type or "unknown",
            "token": token,
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "docs": all_clean_docs,
            "stats": {
                "total_crawled": len(all_clean_docs) + len(all_skipped_final),
                "supported": len(all_clean_docs),
                "skipped": all_skipped_final,
                "crawl_depth": crawl_round,
            },
        }
        write_feishu_crawl_state(token, state, profile_name)
        print(
            f"  Done: {len(all_clean_docs)} doc(s) found, "
            f"{len(all_skipped_final)} skipped, "
            f"depth {crawl_round}/{max_depth}, {elapsed}s elapsed",
            flush=True,
        )
        print(
            f"  Saved to .mify/state/feishu-{token}.json",
            flush=True,
        )
        results.append((token, state))

    return results


def cmd_feishu(args, config):
    """Create documents from Feishu URLs. Reads crawl state or auto-crawls."""
    profile_name = config.get("profile_name")
    kb = resolve_kb(args.kb, profile_name)
    if kb is None:
        return
    kb_id = kb["id"]
    crawl_timeout = getattr(args, "timeout", 180)
    crawl_max_depth = getattr(args, "max_depth", MAX_WIKI_CRAWL_DEPTH)

    all_docs = []

    for url in args.urls:
        url_type, token = extract_feishu_token(url)
        if not token:
            print(f"[WARN] Cannot parse Feishu URL, skipping: {url}", flush=True)
            continue

        # Check for existing crawl state
        state = read_feishu_crawl_state(token, profile_name)
        if state and state.get("docs"):
            # Check cache expiration
            expired, age_days = is_crawl_cache_expired(state)
            if expired:
                age_str = f"crawled {age_days} days ago" if age_days is not None else "unknown age"
                print(
                    f"Cache expired ({age_str}), re-crawling {url}...",
                    flush=True,
                )
                old_docs = state.get("docs", [])
                results = _crawl_and_save(
                    [url], config, timeout=crawl_timeout, max_depth=crawl_max_depth,
                    profile_name=profile_name,
                )
                for _token, st in results:
                    new_docs = st.get("docs", [])
                    diff = compute_crawl_diff(old_docs, new_docs)
                    if diff["added"] == 0 and diff["removed"] == 0:
                        print(
                            f"  Diff: no changes ({diff['unchanged']} documents)",
                            flush=True,
                        )
                    else:
                        print(
                            f"  Diff: +{diff['added']} added, -{diff['removed']} removed, "
                            f"{diff['unchanged']} unchanged",
                            flush=True,
                        )
                    all_docs.extend(new_docs)
            else:
                print(
                    f"Using cached crawl state for {url} "
                    f"({len(state['docs'])} doc(s), crawled at {state.get('crawled_at', '?')})",
                    flush=True,
                )
                all_docs.extend(state["docs"])
        else:
            # Auto-crawl if no saved state
            print(f"No cached crawl state for {url}, crawling now...", flush=True)
            results = _crawl_and_save(
                [url], config, timeout=crawl_timeout, max_depth=crawl_max_depth,
                profile_name=profile_name,
            )
            for _token, st in results:
                all_docs.extend(st.get("docs", []))

    if not all_docs:
        print("No documents to create.")
        return

    # Deduplicate: skip documents already in the KB (matched by doc_token)
    try:
        existing_docs = list_remote_documents(kb_id, config)
        existing_tokens = {
            d["data_source_info"]["doc_token"]
            for d in existing_docs
            if d.get("data_source_type") == "feishu_import"
            and d.get("data_source_info", {}).get("doc_token")
        }
    except Exception:
        existing_tokens = set()

    if existing_tokens:
        before = len(all_docs)
        all_docs = [d for d in all_docs if d.get("doc_token") not in existing_tokens]
        skipped = before - len(all_docs)
        if skipped:
            print(f"  Skipped {skipped} already-existing document(s).", flush=True)

    if not all_docs:
        print("All documents already exist in KB, nothing to create.")
        return

    print(f"\nCreating {len(all_docs)} document(s) in KB '{kb['name']}' ({kb_id})...")

    try:
        result = mify_request(
            "POST",
            f"/datasets/{kb_id}/documents/create-by-feishu-url",
            config,
            body={
                "indexing_technique": "high_quality",
                "doc_form": "text_model",
                "frequency": 3,
                "process_rule": PROCESS_RULE_CUSTOM,
                "docs": all_docs,
            },
            require_email=True,
        )
    except Exception as e:
        print(f"[ERROR] {e}")
        return

    if result is None:
        return

    created = result.get("document", [])
    if isinstance(created, list):
        for doc in created:
            doc_id = doc.get("id", "")
            name = doc.get("name", "")
            print(f"  Created: {name} (doc_id: {doc_id})")
        print(
            f"\nDone: {len(created)} document(s) created (auto-sync every 3 days)"
        )
    else:
        print("  Documents created (auto-sync every 3 days).")
    refresh_registry(config)


# ---------------------------------------------------------------------------
# Crawl Feishu URLs — save state only, no KB creation
# ---------------------------------------------------------------------------


def cmd_crawl(args, config):
    """Crawl Feishu URLs and save document info to state dir.

    If cached state exists and is expired (>3 days), re-crawls and shows diff.
    """
    profile_name = config.get("profile_name")

    # Check for expired caches first and show diff
    urls_to_crawl = []
    for url in args.urls:
        url_type, token = extract_feishu_token(url)
        if not token:
            urls_to_crawl.append(url)
            continue

        state = read_feishu_crawl_state(token, profile_name)
        if state and state.get("docs"):
            expired, age_days = is_crawl_cache_expired(state)
            if expired:
                age_str = f"crawled {age_days} days ago" if age_days is not None else "unknown age"
                print(f"Cache expired ({age_str}) for {url}, re-crawling...", flush=True)
                old_docs = state.get("docs", [])
                new_results = _crawl_and_save(
                    [url], config, timeout=args.timeout, max_depth=args.max_depth,
                    profile_name=profile_name,
                )
                for _token, st in new_results:
                    new_docs = st.get("docs", [])
                    diff = compute_crawl_diff(old_docs, new_docs)
                    if diff["added"] == 0 and diff["removed"] == 0:
                        print(
                            f"  Diff: no changes ({diff['unchanged']} documents)",
                            flush=True,
                        )
                    else:
                        print(
                            f"  Diff: +{diff['added']} added, -{diff['removed']} removed, "
                            f"{diff['unchanged']} unchanged",
                            flush=True,
                        )
            else:
                print(
                    f"Cache still valid for {url} "
                    f"({len(state['docs'])} doc(s), crawled at {state.get('crawled_at', '?')}). "
                    f"Use purge-feishu --token {token} to force re-crawl.",
                    flush=True,
                )
                continue  # skip — cache is fresh
        urls_to_crawl.append(url)

    results = []
    if urls_to_crawl:
        results = _crawl_and_save(
            urls_to_crawl, config, timeout=args.timeout, max_depth=args.max_depth,
            profile_name=profile_name,
        )

    if not results:
        print("\nNo new documents crawled.")
        return

    total = sum(len(st.get("docs", [])) for _, st in results)
    print(f"\nCrawl complete: {total} document(s) saved across {len(results)} URL(s).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_profile_arg(parser):
    """Add --profile optional argument to a subparser."""
    parser.add_argument(
        "--profile", default=None, help="Profile name (default: from config)"
    )


def cmd_purge_feishu(args, config):
    """Delete local Feishu crawl state file for a given token."""
    profile_name = config.get("profile_name")
    state_path = feishu_crawl_state_path(args.token, profile_name)
    if not state_path.exists():
        print(
            f"No Feishu crawl state found for token '{args.token}' "
            f"(profile: {profile_name}). Nothing to purge."
        )
        return
    state_path.unlink()
    print(f"Purged Feishu crawl state for token '{args.token}' (profile: {profile_name}).")


def cmd_status(args, config):
    """Show cached crawl state for a Feishu token or URL."""
    profile_name = config.get("profile_name")
    token = getattr(args, "token", None)
    if not token and getattr(args, "url", None):
        _, token = extract_feishu_token(args.url)
    if not token:
        print("[ERROR] Provide --token TOKEN or --url URL")
        return

    state = read_feishu_crawl_state(token, profile_name)
    if not state:
        print(f"No cached crawl state for token '{token}' (profile: {profile_name}).")
        print(f"Run: crawl --urls <url>  to crawl first.")
        return

    docs = state.get("docs", [])
    crawled_at = state.get("crawled_at", "unknown")
    expired, age_days = is_crawl_cache_expired(state)
    cache_status = "EXPIRED" if expired else "valid"
    age_str = f" ({age_days} day(s) ago)" if age_days is not None else ""

    print(f"Token:      {token}")
    print(f"URL:        {state.get('url', 'unknown')}")
    print(f"Crawled at: {crawled_at}")
    print(f"Cache:      {cache_status}{age_str}")
    print(f"Docs:       {len(docs)}")
    if docs:
        print("\nDocuments:")
        for i, d in enumerate(docs, 1):
            title = d.get("title", "(no title)")
            doc_type = d.get("doc_type", "")
            print(f"  {i:3}. [{doc_type}] {title}")


def main():
    parser = argparse.ArgumentParser(
        description="Create documents in a Mify knowledge base"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # local
    p_local = sub.add_parser("local", help="Upload local files from a directory")
    p_local.add_argument("--kb", required=True, help="KB name or ID")
    p_local.add_argument("--dir", required=True, help="Local directory path")
    _add_profile_arg(p_local)

    # feishu
    p_feishu = sub.add_parser("feishu", help="Create from Feishu URLs")
    p_feishu.add_argument("--kb", required=True, help="KB name or ID")
    p_feishu.add_argument(
        "--urls", required=True, nargs="+", help="Feishu document URLs"
    )
    p_feishu.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="HTTP timeout per crawl request in seconds (default: 180, max: 3600)",
    )
    p_feishu.add_argument(
        "--max-depth",
        type=int,
        default=MAX_WIKI_CRAWL_DEPTH,
        help=f"Max recursive wiki container expansion depth (default: {MAX_WIKI_CRAWL_DEPTH})",
    )
    _add_profile_arg(p_feishu)

    # crawl
    p_crawl = sub.add_parser(
        "crawl", help="Crawl Feishu URLs and save state (no KB needed)"
    )
    p_crawl.add_argument(
        "--urls", required=True, nargs="+", help="Feishu URLs to crawl"
    )
    p_crawl.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="HTTP timeout per crawl request in seconds (default: 180, max: 3600)",
    )
    p_crawl.add_argument(
        "--max-depth",
        type=int,
        default=MAX_WIKI_CRAWL_DEPTH,
        help=f"Max recursive wiki container expansion depth (default: {MAX_WIKI_CRAWL_DEPTH})",
    )
    _add_profile_arg(p_crawl)

    # purge-feishu
    p_purge = sub.add_parser("purge-feishu", help="Delete Feishu crawl state file")
    p_purge.add_argument("--token", required=True, help="Feishu token to purge state for")
    _add_profile_arg(p_purge)

    # status
    p_status = sub.add_parser(
        "status", help="Show cached crawl state for a Feishu token or URL"
    )
    p_status_group = p_status.add_mutually_exclusive_group(required=True)
    p_status_group.add_argument("--token", help="Feishu token")
    p_status_group.add_argument("--url", help="Feishu URL (token extracted automatically)")
    _add_profile_arg(p_status)

    args = parser.parse_args()

    # Validate and clamp timeout
    if hasattr(args, "timeout") and args.timeout > MAX_TIMEOUT:
        print(
            f"[WARN] --timeout {args.timeout} exceeds maximum ({MAX_TIMEOUT}), clamping to {MAX_TIMEOUT}",
            flush=True,
        )
        args.timeout = MAX_TIMEOUT

    config = load_config(profile_name=args.profile)
    if config is None:
        return

    if args.command == "local":
        cmd_local(args, config)
    elif args.command == "feishu":
        cmd_feishu(args, config)
    elif args.command == "crawl":
        cmd_crawl(args, config)
    elif args.command == "purge-feishu":
        cmd_purge_feishu(args, config)
    elif args.command == "status":
        cmd_status(args, config)


if __name__ == "__main__":
    main()
