import logging
from config import Config
from dida_api import DidaAPI
from zectrix_api import ZectrixAPI
from mapper import Mapper
from logger import setup_logger

# 配置日志
setup_logger()
logger = logging.getLogger(__name__)

def test_config():
    """测试配置加载"""
    try:
        config = Config()
        logger.info("配置加载成功")
        logger.info(f"API_BASE: {config.api_base}")
        logger.info(f"DEVICE_ID: {config.device_id}")
        logger.info(f"SYNC_INTERVAL: {config.sync_interval}")
        logger.info(f"SYNC_DIRECTION: {config.sync_direction}")
        return True
    except Exception as e:
        logger.error(f"配置加载失败: {str(e)}")
        return False

def test_mapper():
    """测试数据映射"""
    try:
        # 测试DIDA365到Zectrix的映射
        dida_task = {
            "id": "test_id",
            "title": "测试任务",
            "content": "测试内容",
            "dueDate": "2026-04-11T12:00:00.000+0000",
            "isAllDay": False,
            "priority": 3,
            "status": 0
        }
        zectrix_todo = Mapper.dida_to_zectrix(dida_task)
        logger.info(f"DIDA365到Zectrix映射结果: {zectrix_todo}")
        
        # 测试Zectrix到DIDA365的映射
        zectrix_todo = {
            "title": "测试待办",
            "description": "测试描述 [DIDA365:test_id]",
            "dueDate": "2026-04-11",
            "dueTime": "12:00",
            "priority": 1,
            "completed": False
        }
        dida_task = Mapper.zectrix_to_dida(zectrix_todo)
        logger.info(f"Zectrix到DIDA365映射结果: {dida_task}")
        
        # 测试ID提取
        description = "测试描述 [DIDA365:test_id]"
        dida_id = Mapper.extract_dida_id(description)
        logger.info(f"提取DIDA365 ID: {dida_id}")
        
        # 测试移除ID
        clean_description = Mapper.remove_dida_id(description)
        logger.info(f"移除ID后的描述: {clean_description}")
        
        return True
    except Exception as e:
        logger.error(f"数据映射测试失败: {str(e)}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始测试...")
    
    # 测试配置
    config_test = test_config()
    
    # 测试数据映射
    mapper_test = test_mapper()
    
    if config_test and mapper_test:
        logger.info("所有测试通过！")
    else:
        logger.error("测试失败！")

if __name__ == "__main__":
    main()
