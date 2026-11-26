"""Phase 5: one retry with exponential backoff for calls to outside services.

Every model, Pinecone and Tavily call goes through `call_upstream`. If it still fails
after the retries, it raises UpstreamError naming the service, which the API turns
into a 502 with a clear message.
"""
import logging
import time
from typing import Callable, TypeVar

log = logging.getLogger("upstream")
T = TypeVar("T")


class UpstreamError(RuntimeError):
    def __init__(self, service: str, cause: Exception):
        self.service = service
        super().__init__(f"{service} failed: {type(cause).__name__}: {cause}")


def call_upstream(service: str, fn: Callable[[], T], attempts: int = 2, base_delay: float = 1.0) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - we re-raise as UpstreamError
            if attempt == attempts:
                raise UpstreamError(service, exc) from exc
            delay = base_delay * 2 ** (attempt - 1)
            log.warning("%s call failed (attempt %d/%d): %s; retrying in %.1fs",
                        service, attempt, attempts, exc, delay)
            time.sleep(delay)
    raise AssertionError("unreachable")
