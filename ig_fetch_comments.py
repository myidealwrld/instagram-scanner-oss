#!/usr/bin/env python3
"""
Fetch every comment on your Instagram posts and reels via the Graph API.

You need:
  1. An Instagram Business or Creator account linked to a Facebook Page.
  2. A Graph API access token with instagram_basic + pages_read_engagement scopes.
  3. Your Instagram user id (numeric).

How to get the token and id (once, no password shared with anyone):
  a. Go to developers.facebook.com, create an app (type: Business).
  b. Open Graph API Explorer, pick your app, and add permissions:
     instagram_basic, instagram_manage_comments, pages_show_list,
     pages_read_engagement. Generate the token.
  c. In the Explorer, run:  me/accounts        -> gives your Page id
     then:                  {page-id}?fields=instagram_business_account
                            -> gives your Instagram user id.
  d. Paste the token and id below, or pass them as arguments:
       python3 ig_fetch_comments.py --token XXX --ig-user-id 1784...

Output: comments_instagram.json and comments_instagram.csv in this folder.
Pure standard library, so no pip install needed.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"


def _request_json(url, token):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "graph.facebook.com" or parsed.port not in (None, 443):
        raise ValueError("Refusing to send the access token outside the HTTPS Graph API host")
    safe_query = urllib.parse.urlencode([
        (key, value)
        for key, value in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() != "access_token"
    ])
    url = urllib.parse.urlunparse(parsed._replace(query=safe_query))
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def get(path, params, token):
    url = f"{GRAPH}/{path}?" + urllib.parse.urlencode(params)
    return _request_json(url, token)


def get_all(path, params, token):
    """Follow paging.next until the pages run out."""
    out = []
    data = get(path, params, token)
    while True:
        out.extend(data.get("data", []))
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        data = _request_json(nxt, token)
        time.sleep(0.3)  # be gentle on rate limits
    return out


def fetch(token, ig_user_id):
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
    for i, m in enumerate(media, 1):
        if not m.get("comments_count"):
            continue
        comments = get_all(
            f"{m['id']}/comments",
            {
                "fields": "id,text,username,timestamp,like_count,replies{text,username,timestamp,like_count}",
                "limit": 50,
            },
            token,
        )
        for c in comments:
            rows.append(flatten(c, m))
            for rep in c.get("replies", {}).get("data", []):
                rows.append(flatten(rep, m, parent=c.get("username")))
        print(f"  [{i}/{len(media)}] {len(comments)} comments on {m.get('permalink','')}",
              file=sys.stderr)
        time.sleep(0.3)
    return media, rows


def flatten(c, m, parent=None):
    return {
        "platform": "instagram",
        "comment_id": c.get("id", ""),
        "text": (c.get("text") or "").replace("\n", " ").strip(),
        "username": c.get("username", ""),
        "timestamp": c.get("timestamp", ""),
        "like_count": c.get("like_count", 0),
        "reply_to": parent or "",
        "post_url": m.get("permalink", ""),
        "post_caption": (m.get("caption") or "").replace("\n", " ")[:120],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("IG_ACCESS_TOKEN"), help="Meta Graph API token (prefer IG_ACCESS_TOKEN environment variable)")
    ap.add_argument("--ig-user-id", default=os.environ.get("IG_USER_ID"), help="Numeric Instagram Business/Creator account ID (or IG_USER_ID environment variable)")
    args = ap.parse_args()

    if not args.token or not args.ig_user_id:
        print("Set IG_ACCESS_TOKEN and IG_USER_ID, or pass --token and --ig-user-id.", file=sys.stderr)
        sys.exit(1)
    if not re.fullmatch(r"\d+", args.ig_user_id):
        print("IG_USER_ID must contain only digits.", file=sys.stderr)
        sys.exit(2)

    media, rows = fetch(args.token, args.ig_user_id)

    with open("comments_instagram.json", "w", encoding="utf-8") as f:
        json.dump({"media": media, "comments": rows}, f, ensure_ascii=False, indent=2)

    if rows:
        with open("comments_instagram.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    print(f"\nSaved {len(rows)} comments to comments_instagram.json / .csv",
          file=sys.stderr)


if __name__ == "__main__":
    main()
