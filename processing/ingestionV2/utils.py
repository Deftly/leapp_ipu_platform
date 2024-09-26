import time
from functools import wraps
from logger import get_logger

logger = get_logger(__name__)


def retry_with_backoff(max_retries=3, backoff_in_seconds=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    wait_time = backoff_in_seconds * (2**retries)
                    logger.warning(
                        f"Error in {func.__name__}, retrying in {wait_time} seconds... Error: {str(e)}"
                    )
                    time.sleep(wait_time)
                    retries += 1
            return func(*args, **kwargs)

        return wrapper

    return decorator
