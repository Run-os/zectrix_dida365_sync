import time
import logging
from config import Config
from dida_api import DidaAPI
from zectrix_api import ZectrixAPI
from sync import SyncManager
from logger import setup_logger

# 配置日志
setup_logger()
logger = logging.getLogger(__name__)

def main():
    try:
        # 加载配置
        config = Config()
        
        # 初始化API客户端
        dida_api = DidaAPI(config.dida_token)
        zectrix_api = ZectrixAPI(config.api_base, config.api_key, config.device_id)
        
        # 初始化同步管理器
        sync_manager = SyncManager(dida_api, zectrix_api, config)
        
        # 执行初始同步
        logger.info("开始执行初始同步...")
        sync_manager.sync()
        logger.info("初始同步完成")
        
        # 如果配置了定时同步，则启动定时任务
        if config.sync_interval > 0:
            logger.info(f"启动定时同步，间隔：{config.sync_interval}秒")
            sync_manager.start_scheduler()
            
            # 保持程序运行
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("用户中断，停止同步服务")
                sync_manager.stop_scheduler()
    except Exception as e:
        logger.error(f"同步服务启动失败: {str(e)}")

if __name__ == "__main__":
    main()
