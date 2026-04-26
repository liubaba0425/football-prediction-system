#!/usr/bin/env python3
"""
HTTP 请求重试工具
提供指数退避 + 抖动（jitter）的重试机制，应对间歇性网络故障
"""
import time
import random
import logging
from functools import wraps
from typing import Callable, TypeVar, Any
import requests

logger = logging.getLogger("retry_utils")

T = TypeVar("T")

# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 2.0   # 秒
DEFAULT_BACKOFF_FACTOR = 2  # 指数退避乘数
DEFAULT_JITTER = 0.5        # 随机抖动范围（±0.5秒）


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: int = DEFAULT_BACKOFF_FACTOR,
    jitter: float = DEFAULT_JITTER,
    retryable_exceptions: tuple = (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.HTTPError,
    ),
):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数（不含首次调用）
        base_delay: 第一次重试前的等待时间（秒）
        backoff_factor: 每次重试的延迟倍数
        jitter: 随机抖动范围，实际延迟 = base_delay * (backoff_factor ^ attempt) ± jitter
        retryable_exceptions: 可重试的异常类型元组

    Usage:
        @retry_with_backoff(max_retries=3)
        def fetch_data(url):
            return requests.get(url, timeout=30)

        result = safe_request(requests.get, url, timeout=30, params=params)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        delay += random.uniform(-jitter, jitter)
                        delay = max(0.1, delay)  # 保证最小延迟 0.1 秒

                        logger.warning(
                            f"请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}. "
                            f"{delay:.1f}秒后重试..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"请求最终失败，已耗尽 {max_retries} 次重试: {last_exception}"
                        )

            # 所有重试耗尽
            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator


def safe_request(
    method: Callable[..., Any],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    silent: bool = False,
    **kwargs,
) -> Any:
    """
    安全执行 HTTP 请求，失败时自动重试

    Args:
        method: requests.get / requests.post 等
        *args: 传给 method 的位置参数
        max_retries: 最大重试次数
        base_delay: 基础延迟
        silent: True 时抑制重试日志（返回 None 而非抛异常）
        **kwargs: 传给 method 的关键字参数

    Returns:
        成功时返回 requests.Response 对象
        失败（silent=True）时返回 None
    """
    last_exception = None
    backoff_factor = DEFAULT_BACKOFF_FACTOR

    for attempt in range(max_retries + 1):
        try:
            response = method(*args, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            last_exception = e

            if attempt < max_retries:
                delay = base_delay * (backoff_factor ** attempt)
                delay += random.uniform(-DEFAULT_JITTER, DEFAULT_JITTER)
                delay = max(0.1, delay)

                if not silent:
                    logger.warning(
                        f"请求失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}. "
                        f"{delay:.1f}秒后重试..."
                    )
                time.sleep(delay)
            else:
                if not silent:
                    logger.error(
                        f"请求最终失败，已耗尽 {max_retries} 次重试: {last_exception}"
                    )

    if silent:
        return None
    raise last_exception  # type: ignore[misc]
