# Instagram Comment Scanner

A small Python CLI that reads comments and replies from media owned by an Instagram Business or Creator account through the Meta Graph API. It does not log in with an Instagram password or store account sessions.

## Features

- Fetch account media and paginated comments/replies using the Graph API.
- Export JSON and CSV locally.
- Configure the access token and numeric account ID through environment variables or CLI options.
- Send the token in an HTTPS Authorization header rather than a URL query parameter.

## Requirements and installation

- Python 3.10 or newer
- An Instagram Business or Creator account linked to a Facebook Page
- A Meta app and a valid Graph API access token with the Instagram and Pages permissions required by Meta for the account

No third-party packages are required. Clone/download this directory, then set `IG_ACCESS_TOKEN` and `IG_USER_ID`. `.env.example` contains dummy values only; the script does not automatically load `.env` files.

## Quick start

```sh
export IG_ACCESS_TOKEN='your-token-in-your-local-shell'
export IG_USER_ID='your-numeric-instagram-account-id'
python3 ig_fetch_comments.py
```

Alternatively, pass `--token` and `--ig-user-id`. Prefer environment variables because command-line arguments may be visible to local process inspection tools.

## Example and expected output

`examples/sample-response.json` and `examples/expected-output.json` are synthetic fixtures, not account data. Run the offline verification with:

```sh
python3 -m unittest discover -s tests -v
```

When a real run succeeds, the current directory receives `comments_instagram.json` and, if comments exist, `comments_instagram.csv`.

## Configuration

| Variable | Meaning |
| --- | --- |
| `IG_ACCESS_TOKEN` | Meta Graph API access token |
| `IG_USER_ID` | Numeric Instagram Business/Creator account ID |
The token is never printed by the program. Treat downloaded comment text and usernames as personal data.

## Architecture

`ig_fetch_comments.py` performs Graph API requests, follows pagination links, flattens replies, and writes local exports. It has no cookie jar, password login, proxy, database, or account-specific configuration.

## Development and testing

```sh
python3 -m unittest discover -s tests -v
python3 ig_fetch_comments.py --help
```

Tests use mocked Graph API responses. A live account scan was not run in this staging workspace because no access token or account ID was supplied.

## Security

Never commit `.env`, access tokens, generated exports, or account data. Revoke tokens that are exposed. Only collect comments for accounts and purposes you are authorized to access, and follow Meta platform terms and applicable privacy law.

## Licence

Apache-2.0. See `LICENSE`.