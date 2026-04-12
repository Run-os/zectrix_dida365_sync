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
        zectrix_api = ZectrixAPI(
            config.api_base, config.api_key, config.device_id)

        # 初始化同步管理器
        sync_manager = SyncManager(dida_api, zectrix_api, config)

        # 执行初始同步
        logger.info("开始执行初始同步...")
        sync_manager.sync()
        # logger.info("一次性同步完成，程序退出")
    except Exception as e:
        logger.error(f"同步服务启动失败: {str(e)}")


if __name__ == "__main__":
    main()
