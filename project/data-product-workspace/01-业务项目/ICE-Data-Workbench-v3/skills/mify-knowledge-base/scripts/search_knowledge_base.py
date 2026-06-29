#!/usr/bin/env python3
"""
Search a Mify knowledge base.

Usage:
    python search_knowledge_base.py --kb "My KB" --query "how to use CLI"
    python search_knowledge_base.py --kb "My KB" --query "docs" --top-k 10 --no-rerank
    python search_knowledge_base.py --kb "My KB" --query "docs" --profile oss-kb
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mify_client import (
    is_kb_active,
    load_config,
    mify_request,
    read_kb_registry,
)

# ---------------------------------------------------------------------------
# MifyRAG search (vendor provider)
# ---------------------------------------------------------------------------


def search_mifyrag(config, kb_id, query, top_k=5, score_threshold=0.1, rerank=True):
    """Search using MifyRAG retrieve endpoint."""
    # Workaround: API returns ~2x results with reranking, so request 2x and trim
    api_top_k = top_k * 2 if rerank else top_k

    body = {
        "query": query,
        "retrieval_model": {
            "search_method": "hybrid_search",
            "reranking_enable": rerank,
            "top_k": api_top_k,
            "score_threshold": score_threshold,
            "score_threshold_enabled": bool(score_threshold),
        },
    }

    if rerank:
        body["retrieval_model"]["reranking_mode"] = "reranking_model"
        body["retrieval_model"]["reranking_model"] = {
            "reranking_provider_name": "langgenius/siliconflow/siliconflow",
            "reranking_model_name": "BAAI/bge-reranker-v2-m3_mi_sys",
        }

    result = mify_request("POST", f"/datasets/{kb_id}/retrieve", config, body=body)

    records = []
    for record in result.get("records", []):
        segment = record.get("segment", {})
        document = segment.get("document", {})

        # Detect source type and URL
        data_source_type = document.get("data_source_type", "")
        if data_source_type == "feishu_import":
            data_source_info = document.get("data_source_info", {})
            doc_url = data_source_info.get("url") or document.get("doc_url", "")
            source_type = "feishu"
        else:
            doc_url = document.get("doc_url", "")
            source_type = "local"

        records.append(
            {
                "content": segment.get("content", ""),
                "score": record.get("score"),
                "document_name": document.get("name", ""),
                "document_url": doc_url,
                "source_type": source_type,
            }
        )

    # Trim to requested top_k (workaround for reranking 2x bug)
    return records[:top_k]


# ---------------------------------------------------------------------------
# MiBRAG search
# ---------------------------------------------------------------------------


def _parse_mibrag_records(result, top_k):
    """Parse records from MiBRAG retrieve response (shared by v1 and v2)."""
    records = []
    for record in result.get("records", []):
        metadata = record.get("metadata", {})
        records.append(
            {
                "content": record.get("content", ""),
                "score": record.get("score"),
                "document_name": record.get("title", ""),
                "document_url": metadata.get("path", ""),
                "source_type": "mibrag",
            }
        )
    return records[:top_k]


def search_mibrag(config, kb_id, query, top_k=5, score_threshold=0.1):
    """Search using MiBRAG v1 retrieve endpoint (nested external_retrieval_model)."""
    body = {
        "query": query,
        "external_retrieval_model": {
            "top_k": top_k,
            "score_threshold": score_threshold,
            "score_threshold_enabled": bool(score_threshold),
        },
    }

    result = mify_request(
        "POST", f"/datasets/{kb_id}/mibrag_retrieve", config, body=body
    )
    return _parse_mibrag_records(result, top_k)


def search_mibrag_v2(config, kb_id, query, top_k=5, score_threshold=0.1):
    """Search using MiBRAG v2 retrieve endpoint (flat body params)."""
    body = {
        "query": query,
        "top_k": top_k,
        "score_threshold": score_threshold,
        "score_threshold_enabled": bool(score_threshold),
    }

    result = mify_request(
        "POST", f"/datasets/{kb_id}/mibrag_retrieve", config, body=body
    )
    return _parse_mibrag_records(result, top_k)


# ---------------------------------------------------------------------------
# Result formatting
# ---------------------------------------------------------------------------


def format_results(records, kb_name):
    """Format and print search results."""
    if not records:
        print("No results found.")
        return

    print(f"Found {len(records)} result(s) in KB '{kb_name}'\n")

    for i, r in enumerate(records, 1):
        score = r.get("score")
        score_pct = f"{score * 100:.1f}%" if score is not None else "N/A"

        print(f"--- [{i}] {score_pct} ---")

        doc_name = r.get("document_name", "Unknown")
        doc_url = r.get("document_url", "")
        source_type = r.get("source_type", "")

        if doc_url and source_type == "feishu":
            print(f"Doc: {doc_name}  ({doc_url})")
        else:
            print(f"Doc: {doc_name}")

        content = r.get("content", "").strip()
        if content:
            # Truncate very long content for display
            if len(content) > 500:
                content = content[:500] + "..."
            print(f"\n{content}\n")
        else:
            print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _find_kb_in_profiles(kb_name, search_profiles):
    """Find which profile owns a KB by scanning registries.

    Returns (profile_name, kb_entry) or (None, None) if not found.
    Searches profiles in order; first match wins.
    """
    for profile in search_profiles:
        registry = read_kb_registry(profile)
        for kb in registry:
            if kb.get("id") == kb_name or kb.get("name") == kb_name:
                return profile, kb
    return None, None


def main():
    parser = argparse.ArgumentParser(description="Search a Mify knowledge base")
    parser.add_argument("--kb", required=True, help="KB name or ID")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.1,
        help="Min score threshold (default: 0.1)",
    )
    parser.add_argument("--no-rerank", action="store_true", help="Disable reranking")
    parser.add_argument("--profile", default=None, help="Profile name (skip auto-routing, use this profile directly)")

    args = parser.parse_args()
    rerank = not args.no_rerank

    if args.profile:
        # Explicit profile — no auto-routing
        profile = args.profile
        config = load_config(profile_name=profile)
        if config is None:
            return
        registry = read_kb_registry(profile)
        kb = None
        for entry in registry:
            if entry.get("id") == args.kb or entry.get("name") == args.kb:
                kb = entry
                break
        if not kb:
            print(
                f"[ERROR] KB '{args.kb}' not found in profile '{profile}' registry.\n"
                f"  Run list_knowledge_bases.py list --profile {profile} to refresh."
            )
            return
    else:
        # Auto-route: scan search_profiles to find which profile owns this KB
        config = load_config()
        if config is None:
            return
        search_profiles = config.get("search_profiles", [config.get("profile_name")])
        profile, kb = _find_kb_in_profiles(args.kb, search_profiles)
        if not kb:
            profiles_str = ", ".join(search_profiles)
            print(
                f"[ERROR] KB '{args.kb}' not found in any profile registry.\n"
                f"  Searched profiles: {profiles_str}\n"
                f"  Run preflight.py to refresh registries, or specify --profile explicitly."
            )
            return
        # Reload config with the resolved profile for correct API key
        config = load_config(profile_name=profile)
        if config is None:
            return

    # Whitelist check
    if not is_kb_active(config, kb):
        active_kbs_map = config.get("active_kbs_map", {})
        allowed = active_kbs_map.get(profile)
        if allowed is not None and len(allowed) == 0:
            print(
                f'[BLOCKED] Search is disabled: active_kbs is set to an empty list for profile \'{profile}\'.\n'
                f'  KB \'{kb["name"]}\' cannot be searched.\n'
                f'  To allow this KB, run: list_knowledge_bases.py search-config --add "{kb["name"]}"'
            )
        else:
            allowed_str = ", ".join(allowed) if allowed else "(none)"
            print(
                f'[BLOCKED] KB \'{kb["name"]}\' is not in the search whitelist for profile \'{profile}\'.\n'
                f'  Current whitelist: {allowed_str}\n'
                f'  To add it, run: list_knowledge_bases.py search-config --add "{kb["name"]}"'
            )
        return

    # Search the KB
    kb_id = kb["id"]
    provider = kb.get("provider", "vendor")

    if provider == "mibrag_v2":
        records = search_mibrag_v2(
            config, kb_id, args.query, args.top_k, args.score_threshold
        )
    elif provider == "mibrag":
        records = search_mibrag(
            config, kb_id, args.query, args.top_k, args.score_threshold
        )
    elif provider in ("vendor", ""):
        records = search_mifyrag(
            config, kb_id, args.query, args.top_k, args.score_threshold, rerank
        )
    else:
        print(f"[ERROR] Unsupported provider type: {provider}")
        return

    format_results(records, kb["name"])


if __name__ == "__main__":
    main()
