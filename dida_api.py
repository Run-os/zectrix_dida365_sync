import requests
import logging
from error_handler import retry_on_error, handle_api_error

logger = logging.getLogger(__name__)


class DidaAPI:
    def __init__(self, token):
        self.base_url = "https://api.dida365.com/open/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def get_projects(self):
        """获取项目列表"""
        url = f"{self.base_url}/project"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def get_project_tasks(self, project_id):
        """获取项目任务"""
        url = f"{self.base_url}/project/{project_id}/data"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def get_tasks(self, status=0):
        """按状态过滤任务"""
        url = f"{self.base_url}/task/filter"
        payload = {"status": [status]}
        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def create_task(self, task_data):
        """创建任务"""
        url = f"{self.base_url}/task"
        response = requests.post(url, json=task_data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def update_task(self, task_id, task_data):
        """更新任务"""
        url = f"{self.base_url}/task/{task_id}"
        # 确保请求体包含必要的字段
        if "id" not in task_data:
            task_data["id"] = task_id
        if "projectId" not in task_data:
            # 尝试从任务数据中获取projectId，如果没有则使用默认值
            pass
        if "title" not in task_data:
            # 标题是必填字段，如果没有则不更新
            logger.warning("更新任务时缺少标题字段")
        # 使用POST方法而不是PUT方法
        response = requests.post(url, json=task_data, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @retry_on_error(max_retries=3, retry_interval=1, backoff_factor=2)
    @handle_api_error
    def complete_task(self, project_id, task_id):
        """将任务标记为已完成"""
        url = f"{self.base_url}/project/{project_id}/task/{task_id}/complete"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {"success": True}
