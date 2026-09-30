# Instagram Comment Scanner

A dependency-free Python CLI that exports comments and replies from media owned by an authorized Instagram Business or Creator account through Meta's Graph API.

## Features

- Fetch account media and paginated comments
- Follow pagination until exhausted
- Fetch replies from each comment's replies edge, rather than relying on a truncated embedded reply list
- Export JSON and CSV locally
- Use environment variables or CLI arguments for credentials
- Send tokens in HTTPS Authorization headers, never query strings
- Supports Meta Graph API hosts `graph.facebook.com` and `graph.instagram.com`
- Defaults to Graph API `v26.0`, configurable with `IG_GRAPH_VERSION`

## Requirements

- Python 3.10+
- An Instagram Business or Creator account
- A Meta app and authorized Graph API token with the permissions required for the account/API configuration
- Numeric Instagram account ID

No third-party Python packages are required.

## Quick start

```sh
export IG_ACCESS_TOKEN='your-authorized-token'
export IG_USER_ID='your-numeric-instagram-account-id'
python3 ig_fetch_comments.py
```

Optional configuration:

```sh
export IG_GRAPH_VERSION='v26.0'
export IG_GRAPH_BASE_URL='https://graph.facebook.com'
```

For an Instagram Login setup that uses the Instagram Graph host, set `IG_GRAPH_BASE_URL=https://graph.instagram.com` if that matches your Meta app configuration.

You can also pass `--token`, `--ig-user-id`, and `--output-prefix`. Prefer environment variables for the token because command-line arguments may be visible to local process inspection tools.

## Output

The scanner writes:

- `comments_instagram.json`
- `comments_instagram.csv` when comments/replies exist

Each reply contains `reply_to` with the parent comment username.

## Testing

```sh
python3 -m unittest discover -s tests -v
python3 ig_fetch_comments.py --help
```

Tests use mocked Graph API responses and do not require credentials.

## Security and privacy

The scanner accepts pagination only from approved HTTPS Meta Graph API hosts and strips any `access_token` query parameter before requests. Never commit tokens, generated exports, or account data. Only collect data you are authorized to access and follow Meta's platform terms and applicable privacy law.

## License

Apache-2.0. See `LICENSE`.
