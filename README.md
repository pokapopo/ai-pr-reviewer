# AI PR Reviewer

[![CI](https://github.com/Pokapopo/ai-pr-reviewer/actions/workflows/ci.yml/badge.svg)](https://github.com/Pokapopo/ai-pr-reviewer/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Automated pull request code review powered by LLMs. Listens to GitHub webhook events, analyses PR diffs with an LLM (OpenAI / any OpenAI-compatible API), and posts inline review comments directly on the PR.

## Features

- **GitHub Webhook Integration** — receives `pull_request.opened` and `pull_request.synchronize` events
- **LLM-Powered Review** — sends the PR diff to an LLM for contextual code analysis
- **Inline PR Comments** — posts structured review comments back to the pull request
- **Multi-Provider** — works with OpenAI, Azure OpenAI, or any OpenAI-compatible API endpoint
- **Signature Verification** — validates webhook payloads with HMAC-SHA256
- **Configurable** — all settings via environment variables
- **Lightweight** — single FastAPI server, no database required

## Quick Start

### Prerequisites

- Python 3.12+
- A GitHub personal access token with `repo` scope
- An LLM API key (OpenAI, or any compatible provider)

### Installation

```bash
git clone https://github.com/Pokapopo/ai-pr-reviewer.git
cd ai-pr-reviewer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | — | GitHub PAT with `repo` scope |
| `GITHUB_WEBHOOK_SECRET` | No | — | Webhook secret for HMAC verification |
| `LLM_API_KEY` | Yes | — | API key for the LLM provider |
| `LLM_API_BASE` | No | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_MODEL` | No | `gpt-4o` | Model name to use |
| `LLM_MAX_TOKENS` | No | `4096` | Max tokens for LLM response |
| `LLM_TEMPERATURE` | No | `0.3` | LLM temperature |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

### Run

```bash
python main.py
```

The server starts at `http://0.0.0.0:8000`.

### Expose to GitHub

Use a tool like [ngrok](https://ngrok.com/) to expose your local server:

```bash
ngrok http 8000
```

Then configure a GitHub webhook on your repository:

1. Go to **Settings → Webhooks → Add webhook**
2. Payload URL: `https://your-ngrok-url.ngrok.io/webhook`
3. Content type: `application/json`
4. Secret: same as `GITHUB_WEBHOOK_SECRET`
5. Events: **Pull requests**

## Usage

Once set up, the bot will automatically:

1. Receive a webhook event when a PR is opened or updated
2. Fetch the PR diff from GitHub
3. Send the diff to the configured LLM for analysis
4. Post review comments directly on the PR

Example review output in a PR:

> **AI Code Review**
>
> - **`src/auth.py`** (line 42): Potential SQL injection — use parameterized queries instead of string formatting.
> - **`src/api.py`** (line 87): Missing error handling for the HTTP request; consider wrapping in try/except.

## Using Different LLM Providers

This project uses the OpenAI-compatible API format, which is supported by many providers:

<details>
<summary><b>OpenAI</b></summary>

```env
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o
```
</details>

<details>
<summary><b>Anthropic Claude (via OpenAI-compatible proxy)</b></summary>

```env
LLM_API_BASE=https://your-proxy-url/v1
LLM_API_KEY=sk-ant-...
LLM_MODEL=claude-sonnet-4-6
```
</details>

<details>
<summary><b>Azure OpenAI</b></summary>

```env
LLM_API_BASE=https://<your-resource>.openai.azure.com/openai/deployments/<deployment-id>/chat/completions?api-version=2024-02-15-preview
LLM_API_KEY=...
LLM_MODEL=gpt-4o
```
</details>

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/webhook` | GitHub webhook receiver |

## Project Structure

```
ai-pr-reviewer/
├── .env.example            # Environment variable template
├── .github/workflows/ci.yml # GitHub Actions CI
├── .gitignore
├── README.md
├── config.py               # Configuration management
├── main.py                 # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── reviewer.py             # LLM review logic
└── webhook_handler.py      # Webhook processing & GitHub API
```

## License

MIT
