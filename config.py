import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # Zectrix API 配置
        self.api_base = os.getenv("API_BASE", "https://cloud.zectrix.com/open/v1")
        self.api_key = os.getenv("API_KEY")
        self.device_id = os.getenv("DEVICE_ID")
        
        # DIDA365 配置
        self.dida_token = os.getenv("dida_token")
        
        # 同步配置
        # SYNC_INTERVAL 单位为秒
        try:
            self.sync_interval = int(os.getenv("SYNC_INTERVAL", "300"))  # 默认300秒（5分钟）
        except ValueError:
            self.sync_interval = 300  # 默认300秒（5分钟）
        
        self.sync_direction = os.getenv("SYNC_DIRECTION", "bidirectional")  # 默认双向同步
        self.target_project_id = os.getenv("TARGET_PROJECT_ID", "inbox")  # 默认收集箱
        self.sync_completed = os.getenv("SYNC_COMPLETED", "false").lower() == "true"  # 默认同步已完成任务
        
        # 验证必要的配置
        if not self.api_key:
            raise ValueError("API_KEY is required")
        if not self.device_id:
            raise ValueError("DEVICE_ID is required")
        if not self.dida_token:
            raise ValueError("dida_token is required")
