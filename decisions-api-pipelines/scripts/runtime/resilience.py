"""Resilience mechanisms: Retries with jitter, deadlines, and circuit breakers."""

import random
import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

class CircuitBreakerOpenError(Exception):
    """Raised when request is rejected by an open circuit breaker."""

class Breaker:
    """Sliding-window circuit breaker for API calls."""

    def __init__(self, failure_threshold: float = 0.50, window_size: int = 50, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.window_size = window_size
        self.cooldown_seconds = cooldown_seconds
        self.calls: list[tuple[float, bool]] = []
        self.tripped_until: float = 0.0

    def allow_request(self) -> bool:
        now = time.time()
        if now < self.tripped_until:
            return False
        return True

    def record_result(self, success: bool):
        now = time.time()
        self.calls.append((now, success))
        if len(self.calls) > self.window_size:
            self.calls.pop(0)

        if len(self.calls) >= 10:
            failures = sum(1 for _, ok in self.calls if not ok)
            rate = failures / len(self.calls)
            if rate >= self.failure_threshold:
                self.tripped_until = now + self.cooldown_seconds

def is_retryable_error(exc: Exception) -> bool:
    """Identifies if exception is a transient network or rate-limit error."""
    msg = str(exc).lower()
    # Non-retryable
    if "insufficient_quota" in msg or "invalid_request" in msg or "authentication" in msg:
        return False
    if "400" in msg or "401" in msg or "403" in msg:
        return False
    # Retryable
    if "429" in msg or "rate_limit" in msg or "500" in msg or "502" in msg or "503" in msg or "timeout" in msg or "connection reset" in msg:
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    return False

def execute_with_resilience(
    func: Callable[..., T],
    deadline: float | None = None,
    breaker: Breaker | None = None,
    max_retries: int = 2,
    base_backoff: float = 0.2,
    max_backoff: float = 2.0,
    *args: Any,
    **kwargs: Any,
) -> T:
    """
    Executes a callable with whole-request retries, exponential backoff with jitter,
    circuit breaking, and deadline enforcement.
    """
    if breaker and not breaker.allow_request():
        raise CircuitBreakerOpenError("Circuit breaker is currently OPEN.")

    attempt = 0
    while True:
        now = time.time()
        if deadline is not None:
            remaining = deadline - now
            if remaining <= 0.05:
                raise TimeoutError("Global execution deadline expired.")
            kwargs["timeout"] = remaining

        try:
            res = func(*args, **kwargs)
            if breaker:
                breaker.record_result(success=True)
            return res
        except Exception as exc:
            if breaker:
                breaker.record_result(success=False)

            attempt += 1
            if attempt > max_retries or not is_retryable_error(exc):
                raise exc

            # Calculate sleep with full jitter
            sleep_cap = min(max_backoff, base_backoff * (2 ** (attempt - 1)))
            sleep_time = random.uniform(0.01, sleep_cap)

            if deadline is not None and (time.time() + sleep_time) >= deadline:
                raise TimeoutError("Deadline will expire before next retry.") from exc

            time.sleep(sleep_time)
