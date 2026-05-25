"""AI-powered GitHub PR reviewer — FastAPI webhook server entry point."""

import logging
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config import Config
from webhook_handler import WebhookHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

config = Config()
missing = config.validate()
if missing:
    logger.error("Missing required environment variables: %s", ", ".join(missing))
    sys.exit(1)

handler = WebhookHandler(config)
app = FastAPI(title="AI PR Reviewer", version="1.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request) -> JSONResponse:
    """Receive GitHub webhook events for pull requests."""
    event_type = request.headers.get("X-GitHub-Event", "")

    if event_type != "pull_request":
        return JSONResponse({"status": "ignored", "event": event_type})

    if not await handler.verify_signature(request):
        return JSONResponse({"status": "error", "reason": "invalid signature"}, status_code=401)

    payload: dict = await request.json()
    logger.info("Received %s event for %s", event_type, payload.get("action", "unknown"))

    if not handler.is_pr_event(payload):
        return JSONResponse(
            {"status": "skipped", "action": payload.get("action", "")}
        )

    result = await handler.handle(payload)
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=config.host, port=config.port, reload=True)
