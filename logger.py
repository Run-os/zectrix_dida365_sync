import logging
import os
from datetime import datetime

def setup_logger():
    """配置日志"""
    # 创建日志目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 日志文件名
    log_file = os.path.join(log_dir, f"sync_{datetime.now().strftime('%Y%m%d')}.log")
    
    # 配置根日志
    # 创建StreamHandler并设置编码为utf-8
    stream_handler = logging.StreamHandler()
    stream_handler.setStream(os.fdopen(os.dup(1), 'w', encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            stream_handler
        ]
    )
    
    # 配置requests库的日志级别（避免过多的调试信息）
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
