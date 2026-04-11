import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class RetryException(Exception):
    """重试异常"""
    pass

def retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2, retryable_exceptions=None):
    """
    错误重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_interval: 初始重试间隔（秒）
        backoff_factor: 退避因子
        retryable_exceptions: 可重试的异常类型列表
    """
    if retryable_exceptions is None:
        retryable_exceptions = (Exception,)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_interval = retry_interval
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"达到最大重试次数 {max_retries}，操作失败: {str(e)}")
                        raise
                    
                    logger.warning(f"操作失败，{current_interval}秒后重试 ({retries}/{max_retries}): {str(e)}")
                    time.sleep(current_interval)
                    current_interval *= backoff_factor
        return wrapper
    return decorator

def handle_api_error(func):
    """
    API错误处理装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 检查是否是HTTP错误
            if hasattr(e, 'response'):
                status_code = e.response.status_code
                if 400 <= status_code < 500:
                    # 4xx错误：记录并跳过
                    logger.error(f"API错误 (4xx): {status_code} - {str(e)}")
                    return None
                elif 500 <= status_code < 600:
                    # 5xx错误：抛出异常，让重试机制处理
                    logger.error(f"API错误 (5xx): {status_code} - {str(e)}")
                    raise
            
            # 其他错误：抛出异常
            logger.error(f"未知错误: {str(e)}")
            raise
    return wrapper
