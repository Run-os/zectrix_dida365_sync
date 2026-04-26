import logging
import os
from datetime import datetime


def cleanup_old_logs(log_dir: str, keep_count: int = 10):
    """清理旧日志文件，仅保留指定数量的最新日志

    Args:
        log_dir: 日志目录路径
        keep_count: 保留的日志文件数量，默认为10
    """
    if not os.path.exists(log_dir):
        return

    # 获取所有日志文件
    log_files = [
        os.path.join(log_dir, f)
        for f in os.listdir(log_dir)
        if f.startswith('sync_') and f.endswith('.log')
    ]

    # 如果日志文件数量不超过保留数量，无需清理
    if len(log_files) <= keep_count:
        return

    # 按修改时间排序（最新的在前）
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    # 删除超出保留数量的旧日志
    for old_log in log_files[keep_count:]:
        try:
            os.remove(old_log)
            logging.info(f"已清理旧日志文件: {os.path.basename(old_log)}")
        except OSError as e:
            logging.warning(f"清理日志文件失败: {os.path.basename(old_log)}, 错误: {e}")


def setup_logger():
    """配置日志"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 日志文件名
    log_file = os.path.join(
        log_dir, f"sync_{datetime.now().strftime('%Y%m%d')}.log")

    # 配置根日志
    # 创建StreamHandler并设置编码为utf-8
    stream_handler = logging.StreamHandler()
    stream_handler.setStream(os.fdopen(os.dup(1), 'w', encoding='utf-8'))

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            stream_handler
        ]
    )

    # 配置requests库的日志级别（避免过多的调试信息）
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # 清理旧日志，仅保留10份最新的
    cleanup_old_logs(log_dir, keep_count=10)
