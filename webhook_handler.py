"""GitHub webhook event processing for PR review automation."""

import hashlib
import hmac
import logging
from typing import Any

import httpx
from fastapi import Request

from config import Config
from reviewer import PRReviewer, ReviewResult

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class WebhookHandler:
    """Handles incoming GitHub webhook events for pull requests."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._reviewer = PRReviewer(config)

    async def verify_signature(self, request: Request) -> bool:
        """Verify the HMAC signature of an incoming webhook request.

        Returns True if the signature matches or no secret is configured.
        """
        secret = self._config.github_webhook_secret
        if not secret:
            logger.warning("No GITHUB_WEBHOOK_SECRET configured; skipping signature verification")
            return True

        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()

        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def is_pr_event(self, payload: dict[str, Any]) -> bool:
        """Check if the event is a PR open or synchronize (push) event."""
        action = payload.get("action", "")
        return action in ("opened", "synchronize")

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a PR webhook event end-to-end.

        Extracts PR metadata, fetches the diff, runs the review,
        and posts the results back to the PR.
        """
        pr = payload.get("pull_request", {})
        repository = payload.get("repository", {})

        owner = repository.get("owner", {}).get("login", "")
        repo_name = repository.get("name", "")
        pr_number = pr.get("number", 0)
        diff_url = pr.get("diff_url", "")

        if not all([owner, repo_name, pr_number, diff_url]):
            return {"status": "skipped", "reason": "missing PR metadata"}

        logger.info("Processing PR %s/%s#%d", owner, repo_name, pr_number)

        diff = await self._fetch_diff(diff_url)
        if diff is None:
            return {"status": "error", "reason": "failed to fetch diff"}

        result = self._reviewer.review(diff)

        if result.comments:
            await self._post_review_comments(owner, repo_name, pr_number, result)
        elif result.summary:
            await self._post_summary_comment(owner, repo_name, pr_number, result.summary)

        return {
            "status": "ok",
            "comments": len(result.comments),
            "has_summary": bool(result.summary),
        }

    async def _fetch_diff(self, diff_url: str) -> str | None:
        """Fetch the unified diff from GitHub's diff URL."""
        headers = {
            "Authorization": f"Bearer {self._config.github_token}",
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "ai-pr-reviewer",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(diff_url, headers=headers)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch diff from %s: %s", diff_url, exc)
                return None

    async def _post_review_comments(
        self, owner: str, repo: str, pr_number: int, result: ReviewResult
    ) -> None:
        """Post review comments as a pull request review."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        headers = {
            "Authorization": f"Bearer {self._config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-pr-reviewer",
        }

        body = "## AI Code Review\n\n"
        for comment in result.comments:
            body += f"- **`{comment.path}`**"
            if comment.line:
                body += f" (line {comment.line})"
            body += f": {comment.body}\n"

        payload: dict[str, Any] = {
            "body": body,
            "event": "COMMENT",
            "comments": [
                {
                    "path": c.path,
                    "body": c.body,
                    "position": 1,
                    **({"line": c.line} if c.line else {}),
                }
                for c in result.comments
            ],
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                logger.info("Posted review to %s/%s#%d", owner, repo, pr_number)
            except httpx.HTTPError as exc:
                logger.error("Failed to post review: %s", exc)

    async def _post_summary_comment(
        self, owner: str, repo: str, pr_number: int, summary: str
    ) -> None:
        """Post a plain summary as an issue comment."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {self._config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-pr-reviewer",
        }

        payload = {"body": f"## AI Code Review\n\n{summary}"}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                logger.info("Posted summary comment to %s/%s#%d", owner, repo, pr_number)
            except httpx.HTTPError as exc:
                logger.error("Failed to post summary: %s", exc)
