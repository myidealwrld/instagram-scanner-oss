#!/usr/bin/env python3
"""Export comments and replies from an authorized Instagram Business/Creator account."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_GRAPH_BASE = "https://graph.facebook.com"
DEFAULT_GRAPH_VERSION = "v26.0"
ALLOWED_GRAPH_HOSTS = {"graph.facebook.com", "graph.instagram.com"}


def _graph_root() -> str:
    base = os.environ.get("IG_GRAPH_BASE_URL", DEFAULT_GRAPH_BASE).rstrip("/")
    version = os.environ.get("IG_GRAPH_VERSION", DEFAULT_GRAPH_VERSION).strip()
    if not re.fullmatch(r"v\d+\.\d+", version):
        raise ValueError("IG_GRAPH_VERSION must look like v26.0")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_GRAPH_HOSTS or parsed.port not in (None, 443):
        raise ValueError("IG_GRAPH_BASE_URL must be an approved HTTPS Meta Graph API host")
    return f"{base}/{version}"


def _request_json(url: str, token: str):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_GRAPH_HOSTS or parsed.port not in (None, 443):
        raise ValueError("Refusing to send the access token outside an approved HTTPS Meta Graph API host")
    safe_query = urllib.parse.urlencode([
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() != "access_token"
    ])
    safe_url = urllib.parse.urlunparse(parsed._replace(query=safe_query))
    request = urllib.request.Request(
        safe_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = f"Meta Graph API HTTP {exc.code}"
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("error", {}).get("message") if isinstance(payload, dict) else None
            if detail:
                message += f": {detail}"
        except Exception:
            pass
        raise RuntimeError(message) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Meta Graph API request failed: {exc.reason}") from exc


def get(path: str, params: dict, token: str):
    url = f"{_graph_root()}/{path}?" + urllib.parse.urlencode(params)
    return _request_json(url, token)


def get_all(path: str, params: dict, token: str):
    """Follow paging.next until all pages are exhausted."""
    out = []
    data = get(path, params, token)
    while True:
        out.extend(data.get("data", []))
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        data = _request_json(nxt, token)
        time.sleep(0.3)
    return out


def flatten(comment: dict, media: dict, parent: str | None = None):
    return {
        "platform": "instagram",
        "comment_id": comment.get("id", ""),
        "text": (comment.get("text") or "").replace("\n", " ").strip(),
        "username": comment.get("username", ""),
        "timestamp": comment.get("timestamp", ""),
        "like_count": comment.get("like_count", 0),
        "reply_to": parent or "",
        "post_url": media.get("permalink", ""),
        "post_caption": (media.get("caption") or "").replace("\n", " ")[:120],
    }


def fetch(token: str, ig_user_id: str):
    media = get_all(
        f"{ig_user_id}/media",
        {
            "fields": "id,caption,permalink,media_type,timestamp,comments_count,like_count",
            "limit": 50,
        },
        token,
    )
    print(f"Found {len(media)} posts/reels.", file=sys.stderr)

    rows = []
    for i, item in enumerate(media, 1):
        if not item.get("comments_count"):
            continue
        comments = get_all(
            f"{item['id']}/comments",
            {
                "fields": "id,text,username,timestamp,like_count,replies.limit(1){id}",
                "limit": 50,
            },
            token,
        )
        reply_count = 0
        for comment in comments:
            rows.append(flatten(comment, item))
            if comment.get("replies"):
                replies = get_all(
                    f"{comment['id']}/replies",
                    {"fields": "id,text,username,timestamp,like_count", "limit": 50},
                    token,
                )
                reply_count += len(replies)
                for reply in replies:
                    rows.append(flatten(reply, item, parent=comment.get("username")))
        print(
            f"  [{i}/{len(media)}] {len(comments)} comments + {reply_count} replies on {item.get('permalink','')}",
            file=sys.stderr,
        )
        time.sleep(0.3)
    return media, rows


def write_outputs(media, rows, output_prefix="comments_instagram"):
    json_path = f"{output_prefix}.json"
    csv_path = f"{output_prefix}.csv"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump({"media": media, "comments": rows}, handle, ensure_ascii=False, indent=2)
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return json_path, csv_path
    return json_path, None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Export comments and replies from an authorized Instagram account")
    parser.add_argument("--token", default=os.environ.get("IG_ACCESS_TOKEN"), help="Meta Graph API token; prefer IG_ACCESS_TOKEN")
    parser.add_argument("--ig-user-id", default=os.environ.get("IG_USER_ID"), help="Numeric Instagram Business/Creator account ID")
    parser.add_argument("--output-prefix", default="comments_instagram")
    args = parser.parse_args(argv)

    if not args.token or not args.ig_user_id:
        parser.error("Set IG_ACCESS_TOKEN and IG_USER_ID, or pass --token and --ig-user-id")
    if not re.fullmatch(r"\d+", args.ig_user_id):
        parser.error("IG_USER_ID must contain only digits")

    try:
        media, rows = fetch(args.token, args.ig_user_id)
        json_path, csv_path = write_outputs(media, rows, args.output_prefix)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    suffix = f" and {csv_path}" if csv_path else ""
    print(f"\nSaved {len(rows)} comments/replies to {json_path}{suffix}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
