"""
日志记录模块，用于记录程序执行的日志信息
"""

import os
import sys
from loguru import logger
from typing import Dict, Any, Optional


def setup_logger(config: Dict[str, Any]) -> None:
    """
    配置日志记录器
    
    Args:
        config: 日志配置信息，包含级别、文件名等
    """
    # 获取日志配置
    log_level = config.get('level', 'INFO')
    log_file = config.get('file', 'logs/auto_signin.log')
    max_size = config.get('max_size', '10 MB')
    backup_count = config.get('backup_count', 3)

    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 移除默认处理器
    logger.remove()

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    # 添加文件处理器
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        rotation=max_size,
        retention=backup_count,
        enqueue=True
    )

    logger.info(f"日志记录器已配置 - 级别: {log_level}, 文件: {log_file}")


def get_logger():
    """获取已配置的日志记录器"""
    return logger


logger = get_logger()
