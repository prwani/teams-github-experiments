# teams-github-experiments

## List open PRs across your repositories

Use `scripts/list_open_prs.py` to list every open pull request across repositories owned by the authenticated GitHub user.

### Requirements

- `python3`
- `GITHUB_TOKEN` or `GH_TOKEN`

### Usage

```bash
python3 scripts/list_open_prs.py
```

Optional flags:

- `--json` prints machine-readable JSON.
- `--api-base-url` overrides the GitHub API base URL (defaults to `https://api.github.com`).