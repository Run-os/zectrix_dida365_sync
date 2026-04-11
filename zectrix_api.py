import requests
import logging
from error_handler import retry_on_error, handle_api_error

logger = logging.getLogger(__name__)

class ZectrixAPI:
    def __init__(self, api_base, api_key, device_id):
        self.base_url = api_base
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        self.device_id = device_id
    
    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def get_todos(self, status=None):
        """获取待办列表"""
        params = {"deviceId": self.device_id}
        if status is not None:
            params["status"] = status
        
        url = f"{self.base_url}/todos"
        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data", [])
    
    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def create_todo(self, todo_data):
        """创建待办"""
        # 确保设备ID存在
        if "deviceId" not in todo_data:
            todo_data["deviceId"] = self.device_id
        
        url = f"{self.base_url}/todos"
        response = requests.post(url, json=todo_data, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data")
    
    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def update_todo(self, todo_id, todo_data):
        """更新待办"""
        # 确保当dueDate和dueTime为None时，设置为null
        if "dueDate" in todo_data and todo_data["dueDate"] is None:
            todo_data["dueDate"] = None
        if "dueTime" in todo_data and todo_data["dueTime"] is None:
            todo_data["dueTime"] = None
        url = f"{self.base_url}/todos/{todo_id}"
        response = requests.put(url, json=todo_data, headers=self.headers)
        response.raise_for_status()
        return response.json().get("data")
    
    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def complete_todo(self, todo_id):
        """标记待办完成/取消完成"""
        url = f"{self.base_url}/todos/{todo_id}/complete"
        response = requests.put(url, headers=self.headers)
        response.raise_for_status()
        return True
