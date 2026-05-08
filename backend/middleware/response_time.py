"""Response time tracking middleware."""

import time
from fastapi import Request


class ResponseTimeMiddleware:
    """Middleware to track response times."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        """Add response time header."""
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        response.headers["X-Process-Time"] = str(duration)
        return response
