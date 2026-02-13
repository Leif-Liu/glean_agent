"""
工具模块 - 重试和辅助函数
"""
import time
import functools
from typing import Callable, Any
import requests
from loguru import logger


def retry_on_rate_limit(max_retries: int = 3, delay: float = 1.0):
    """
    速率限制重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 基础延迟（秒）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    if hasattr(e.response, 'status_code'):
                        status_code = e.response.status_code
                        if status_code == 429:  # Rate limited
                            wait_time = delay * (2 ** attempt)
                            logger.warning(f"⏱️  Rate limited, waiting {wait_time:.1f}s...")
                            time.sleep(wait_time)
                            continue
                        elif status_code >= 500:
                            wait_time = delay * (1.5 ** attempt)
                            logger.warning(f"⚠️  Server error {status_code}, retrying...")
                            time.sleep(wait_time)
                            continue
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (1.5 ** attempt)
                        logger.warning(f"⚠️  Error occurred, retrying: {e}")
                        time.sleep(wait_time)
                        continue
            
            raise last_exception
        return wrapper
    return decorator


def format_duration(seconds: float) -> str:
    """
    格式化持续时间
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的持续时间字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def truncate_text(text: str, max_length: int = 200) -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."


def extract_urls(text: str) -> list:
    """
    从文本中提取 URL
    
    Args:
        text: 文本
        
    Returns:
        URL 列表
    """
    import re
    url_pattern = r'https?://[^\s<>"\)]+'
    urls = re.findall(url_pattern, text)
    return urls


def clean_html(html: str) -> str:
    """
    清理 HTML 标签
    
    Args:
        html: HTML 字符串
        
    Returns:
        纯文本
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator=' ', strip=True)


def calculate_confidence(
    sources: list,
    answer_length: int,
    execution_time: float
) -> float:
    """
    计算置信度
    
    Args:
        sources: 来源列表
        answer_length: 答案长度
        execution_time: 执行时间（秒）
        
    Returns:
        置信度分数 (0-1)
    """
    confidence = 0.0
    
    # 来源数量得分
    if len(sources) >= 3:
        confidence += 0.3
    elif len(sources) >= 1:
        confidence += 0.2
    
    # 答案长度得分（不要太短也不要太长）
    if 100 < answer_length < 1000:
        confidence += 0.2
    elif answer_length >= 50:
        confidence += 0.1
    
    # 执行时间得分（太慢可能意味着数据不足）
    if execution_time < 10:
        confidence += 0.2
    elif execution_time < 30:
        confidence += 0.1
    
    # 执行时间扣分（太慢）
    if execution_time > 60:
        confidence -= 0.2
    
    return max(0.0, min(1.0, confidence))
