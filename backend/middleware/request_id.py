"""Request ID middleware for tracing requests."""

from fastapi import Request
from uuid import uuid4
import time


class RequestIDMiddleware:
    """Middleware to add request ID and track timing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        """Add request ID and timing to all requests."""
        request_id = str(uuid4())
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(duration)

        return response
