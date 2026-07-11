#!/usr/bin/env python3

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import error, parse, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List open pull requests across repositories owned by the authenticated GitHub user."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print pull requests as JSON.",
    )
    parser.add_argument(
        "--api-base-url",
        default="https://api.github.com",
        help="GitHub API base URL.",
    )
    return parser.parse_args()


def parse_next_link(link_header: Optional[str]) -> Optional[str]:
    if not link_header:
        return None

    for part in link_header.split(","):
        url_part, _, rel_part = part.partition(";")
        if 'rel="next"' not in rel_part:
            continue
        return url_part.strip()[1:-1]

    return None


class GitHubClient:
    def __init__(self, token: str, api_base_url: str) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "prwani/teams-github-experiments",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_json(self, url: str) -> Tuple[object, Optional[str]]:
        req = request.Request(url, headers=self.headers)
        with request.urlopen(req) as response:
            payload = json.load(response)
            return payload, response.headers.get("Link")

    def paginate(self, url: str) -> Iterable[object]:
        next_url: Optional[str] = url
        while next_url:
            payload, link_header = self.get_json(next_url)
            if not isinstance(payload, list):
                raise TypeError(f"Expected a list response from {next_url}")
            for item in payload:
                yield item
            next_url = parse_next_link(link_header)


def get_token() -> str:
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        return token
    raise RuntimeError("Set GITHUB_TOKEN or GH_TOKEN before running this script.")


def fetch_owner_and_open_pull_requests(client: GitHubClient) -> Tuple[str, List[Dict[str, Any]]]:
    user, _ = client.get_json(f"{client.api_base_url}/user")
    if not isinstance(user, dict) or "login" not in user:
        raise TypeError("Unexpected response from /user")

    owner = str(user["login"])
    repos_url = (
        f"{client.api_base_url}/user/repos?"
        + parse.urlencode(
            {
                "affiliation": "owner",
                "per_page": 100,
                "sort": "full_name",
            }
        )
    )

    results: List[Dict[str, Any]] = []
    for repo in client.paginate(repos_url):
        if not isinstance(repo, dict):
            raise TypeError("Unexpected repository payload")

        full_name = str(repo["full_name"])
        pulls_url = (
            f"{client.api_base_url}/repos/{full_name}/pulls?"
            + parse.urlencode({"state": "open", "per_page": 100})
        )
        for pull in client.paginate(pulls_url):
            if not isinstance(pull, dict):
                raise TypeError("Unexpected pull request payload")
            results.append(
                {
                    "repository": full_name,
                    "number": pull["number"],
                    "title": pull["title"],
                    "url": pull["html_url"],
                    "author": pull["user"]["login"] if isinstance(pull.get("user"), dict) else None,
                }
            )

    return owner, sorted(results, key=lambda pr: (pr["repository"], pr["number"]))


def print_human_readable(owner: str, pull_requests: List[Dict[str, Any]]) -> None:
    if not pull_requests:
        print(f"No open pull requests found across repositories owned by {owner}.")
        return

    print(f"Open pull requests across repositories owned by {owner}:")
    for pull_request in pull_requests:
        author = f" by {pull_request['author']}" if pull_request.get("author") else ""
        print(
            f"- {pull_request['repository']}#{pull_request['number']}: "
            f"{pull_request['title']}{author}\n  {pull_request['url']}"
        )


def main() -> int:
    args = parse_args()

    try:
        client = GitHubClient(get_token(), args.api_base_url)
        owner, pull_requests = fetch_owner_and_open_pull_requests(client)
    except (RuntimeError, TypeError, error.HTTPError, error.URLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump({"owner": owner, "pull_requests": pull_requests}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print_human_readable(owner, pull_requests)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
