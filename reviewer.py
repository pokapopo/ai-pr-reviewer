"""LLM-powered code reviewer that analyses PR diffs and produces review comments."""

import json
from dataclasses import dataclass, field

from openai import OpenAI

from config import Config

REVIEW_SYSTEM_PROMPT = """\
You are a senior software engineer conducting a code review. Analyse the provided git diff \
and produce actionable, constructive feedback.

For each issue you find, include:
- The exact file path where the issue occurs
- A brief, specific description of the problem
- A concrete suggestion for how to fix it

Focus on:
1. Bugs and logic errors
2. Security vulnerabilities (SQL injection, XSS, insecure deserialization, etc.)
3. Performance regressions (N+1 queries, unnecessary allocations, etc.)
4. Error handling gaps (missing exception handling, swallowed errors)
5. Code clarity and maintainability issues
6. Adherence to common best practices

Do NOT comment on:
- Formatting or style (that is the linter's job)
- Missing docstrings or comments (unless the logic is genuinely confusing)
- Variable naming preferences (unless truly misleading)

If the diff looks good with no notable issues, say so briefly.

Return your review as a JSON array of comments. Each comment object must have:
- "path": the relative file path
- "body": the review comment text
- "line": (optional) the line number the comment applies to

Example:
[{"path": "src/auth.py", "body": "Potential SQL injection ...", "line": 42}]
"""


@dataclass
class ReviewComment:
    """A single review comment produced by the LLM."""

    path: str
    body: str
    line: int | None = None


@dataclass
class ReviewResult:
    """The result of a PR review, containing all comments and a summary."""

    comments: list[ReviewComment] = field(default_factory=list)
    summary: str = ""

    @property
    def is_clean(self) -> bool:
        return len(self.comments) == 0


class PRReviewer:
    """Calls the LLM API to review a pull request diff."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = OpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_api_base,
        )

    def review(self, diff: str) -> ReviewResult:
        """Send the diff to the LLM and parse the review response.

        Args:
            diff: The unified diff text of the PR.

        Returns:
            A ReviewResult containing parsed comments and a summary.
        """
        response = self._client.chat.completions.create(
            model=self._config.llm_model,
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": f"Review this diff:\n\n{diff}"},
            ],
            max_tokens=self._config.llm_max_tokens,
            temperature=self._config.llm_temperature,
        )

        raw = response.choices[0].message.content or "[]"
        return self._parse_response(raw)

    def _parse_response(self, raw: str) -> ReviewResult:
        """Parse the LLM response into a structured ReviewResult."""
        raw = raw.strip()

        # Try to extract a JSON array from the response
        json_start = raw.find("[")
        json_end = raw.rfind("]")

        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_str = raw[json_start : json_end + 1]
        else:
            # Fallback: treat the entire response as a plain-text summary
            return ReviewResult(summary=raw)

        try:
            items = json.loads(json_str)
        except json.JSONDecodeError:
            return ReviewResult(summary=raw)

        if isinstance(items, list):
            return ReviewResult(
                comments=[
                    ReviewComment(
                        path=c.get("path", ""),
                        body=c.get("body", ""),
                        line=c.get("line"),
                    )
                    for c in items
                ],
                summary="",
            )

        return ReviewResult(summary=raw)
