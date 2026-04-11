import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from mapper import Mapper

logger = logging.getLogger(__name__)

class SyncManager:
    def __init__(self, dida_api, zectrix_api, config):
        self.dida_api = dida_api
        self.zectrix_api = zectrix_api
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.last_sync_time = None
    
    def sync(self):
        """执行同步"""
        try:
            logger.info("🔄 同步任务开始")
            
            # 根据同步方向执行不同的同步操作
            if self.config.sync_direction == "bidirectional":
                # 双向同步，只获取一次数据
                self.bidirectional_sync()
            elif self.config.sync_direction == "unidirectional_dida_to_zectrix":
                # 单向从DIDA365到Zectrix
                self.sync_dida_to_zectrix()
            elif self.config.sync_direction == "unidirectional_zectrix_to_dida":
                # 单向从Zectrix到DIDA365
                self.sync_zectrix_to_dida()
            
            # 更新最后同步时间
            self.last_sync_time = datetime.now()
            logger.info("✅ 同步任务全部完成")
        except Exception as e:
            logger.error(f"❌ 同步失败: {str(e)}")
            # 抛出异常，停止同步服务
            raise
    
    def sync_dida_to_zectrix(self):
        """从DIDA365同步到Zectrix"""
        # 获取DIDA365项目任务
        project_tasks = self.dida_api.get_project_tasks(self.config.target_project_id)
        if not project_tasks:
            logger.warning("获取DIDA365项目任务失败，跳过同步")
            return
        dida_tasks = project_tasks.get("tasks", [])
        
        # 获取Zectrix待办列表
        zectrix_todos = self.zectrix_api.get_todos()
        if zectrix_todos is None:
            logger.warning("获取Zectrix待办列表失败，跳过同步")
            return
        
        # 构建Zectrix待办映射（通过DIDA365任务ID）
        zectrix_todo_map = {}
        for todo in zectrix_todos:
            dida_id = Mapper.extract_dida_id(todo.get("description", ""))
            if dida_id:
                zectrix_todo_map[dida_id] = todo
        
        # 同步每个DIDA365任务
        for dida_task in dida_tasks:
            # 跳过已完成任务（如果配置了不同步已完成任务）
            if not self.config.sync_completed and dida_task.get("status") == 2:
                continue
            
            dida_id = dida_task.get("id")
            dida_modified_time = dida_task.get("modifiedTime")
            
            # 转换为Zectrix待办格式
            zectrix_todo_data = Mapper.dida_to_zectrix(dida_task)
            
            # 检查是否已存在对应待办
            if dida_id in zectrix_todo_map:
                # 更新现有待办
                existing_todo = zectrix_todo_map[dida_id]
                zectrix_update_date = existing_todo.get("updateDate")
                
                # 比较修改时间
                if self.should_update_from_dida(dida_modified_time, zectrix_update_date):
                    logger.info(f"任务：{dida_task.get('title')}，DIDA365 ➡️ Zectrix")
                    result = self.zectrix_api.update_todo(existing_todo.get("id"), zectrix_todo_data)
                    if result is None:
                        logger.warning(f"任务：{dida_task.get('title')}，❌ Zectrix 更新失败")
                # else:
                    # logger.info(f"任务：{dida_task.get('title')}，Zectrix 较新，跳过更新")
            else:
                # 创建新待办
                logger.info(f"任务：{dida_task.get('title')}，✏️ Zectrix 新建")
                result = self.zectrix_api.create_todo(zectrix_todo_data)
                if result is None:
                    logger.warning(f"任务：{dida_task.get('title')}，❌ Zectrix 新建失败")
    
    def sync_zectrix_to_dida(self):
        """从Zectrix同步到DIDA365"""
        # 获取Zectrix待办列表
        zectrix_todos = self.zectrix_api.get_todos()
        if zectrix_todos is None:
            logger.warning("获取Zectrix待办列表失败，跳过同步")
            return
        
        # 获取DIDA365项目任务
        project_tasks = self.dida_api.get_project_tasks(self.config.target_project_id)
        if not project_tasks:
            logger.warning("获取DIDA365项目任务失败，跳过同步")
            return
        dida_tasks = project_tasks.get("tasks", [])
        
        # 构建DIDA365任务映射
        dida_task_map = {}
        for task in dida_tasks:
            dida_task_map[task.get("id")] = task
        
        # 同步每个Zectrix待办
        for zectrix_todo in zectrix_todos:
            # 跳过已完成任务（如果配置了不同步已完成任务）
            if not self.config.sync_completed and zectrix_todo.get("completed"):
                continue
            
            zectrix_update_date = zectrix_todo.get("updateDate")
            
            # 转换为DIDA365任务格式
            dida_task_data = Mapper.zectrix_to_dida(zectrix_todo)
            dida_id = dida_task_data.get("id")
            
            # 检查是否已存在对应任务
            if dida_id and dida_id in dida_task_map:
                # 更新现有任务
                original_task = dida_task_map[dida_id]
                dida_modified_time = original_task.get("modifiedTime")
                
                # 比较修改时间
                if self.should_update_from_zectrix(zectrix_update_date, dida_modified_time):
                    logger.info(f"任务：{zectrix_todo.get('title')}，Zectrix ➡️ DIDA365")
                    # 确保请求体包含必要的字段
                    if "id" not in dida_task_data:
                        dida_task_data["id"] = dida_id
                    if "projectId" not in dida_task_data:
                        dida_task_data["projectId"] = original_task.get("projectId")
                    if "title" not in dida_task_data:
                        dida_task_data["title"] = zectrix_todo.get("title")
                    result = self.dida_api.update_task(dida_id, dida_task_data)
                    if result is None:
                        logger.warning(f"任务：{zectrix_todo.get('title')}，❌ DIDA365 更新失败")
                else:
                    logger.info(f"任务：{zectrix_todo.get('title')}，DIDA365 较新，跳过更新")
            else:
                # 创建新任务
                logger.info(f"任务：{zectrix_todo.get('title')}，✏️ DIDA365 新建")
                # 移除id字段，因为创建API不需要
                if "id" in dida_task_data:
                    del dida_task_data["id"]
                # 添加项目ID
                dida_task_data["projectId"] = self.config.target_project_id
                result = self.dida_api.create_task(dida_task_data)
                if result is None:
                    logger.warning(f"任务：{zectrix_todo.get('title')}，❌ DIDA365 新建失败")
    
    def start_scheduler(self):
        """启动定时同步任务"""
        # 添加定时任务
        self.scheduler.add_job(
            self.sync,
            'interval',
            seconds=self.config.sync_interval,
            id='sync_job',
            replace_existing=True
        )
        
        # 启动调度器
        self.scheduler.start()
        logger.info(f"定时同步任务已启动，间隔：{self.config.sync_interval}秒")
    
    def should_update_from_dida(self, dida_modified_time, zectrix_update_date):
        """判断是否应该从DIDA更新到Zectrix"""
        try:
            # DIDA的modifiedTime是ISO格式的字符串，如"2023-12-17T16:00:00.000Z"
            # Zectrix的updateDate是时间戳，如1742284800
            if not dida_modified_time or not zectrix_update_date:
                return True
            
            # 解析DIDA的modifiedTime为时间戳
            from datetime import datetime
            import pytz
            dt = datetime.fromisoformat(dida_modified_time.replace("Z", "+00:00"))
            dida_timestamp = int(dt.timestamp())
            
            # 比较时间戳
            return dida_timestamp > zectrix_update_date
        except Exception:
            # 如果解析失败，默认更新
            return True
    
    def should_update_from_zectrix(self, zectrix_update_date, dida_modified_time):
        """判断是否应该从Zectrix更新到DIDA"""
        try:
            # Zectrix的updateDate是时间戳，如1742284800
            # DIDA的modifiedTime是ISO格式的字符串，如"2023-12-17T16:00:00.000Z"
            if not zectrix_update_date or not dida_modified_time:
                return True
            
            # 解析DIDA的modifiedTime为时间戳
            from datetime import datetime
            import pytz
            dt = datetime.fromisoformat(dida_modified_time.replace("Z", "+00:00"))
            dida_timestamp = int(dt.timestamp())
            
            # 比较时间戳
            return zectrix_update_date > dida_timestamp
        except Exception:
            # 如果解析失败，默认更新
            return True
    
    def bidirectional_sync(self):
        """双向同步，避免循环更新"""
        # 获取DIDA365项目任务
        project_tasks = self.dida_api.get_project_tasks(self.config.target_project_id)
        if not project_tasks:
            logger.warning("获取DIDA365项目任务失败，跳过同步")
            return
        dida_tasks = project_tasks.get("tasks", [])
        
        # 获取Zectrix待办列表
        zectrix_todos = self.zectrix_api.get_todos()
        if zectrix_todos is None:
            logger.warning("获取Zectrix待办列表失败，跳过同步")
            return
        
        # 构建Zectrix待办映射（通过DIDA365任务ID）
        zectrix_todo_map = {}
        for todo in zectrix_todos:
            dida_id = Mapper.extract_dida_id(todo.get("description", ""))
            if dida_id:
                zectrix_todo_map[dida_id] = todo
        
        # 构建DIDA365任务映射
        dida_task_map = {}
        for task in dida_tasks:
            dida_task_map[task.get("id")] = task
        
        # 同步DIDA365到Zectrix
        for dida_task in dida_tasks:
            # 跳过已完成任务（如果配置了不同步已完成任务）
            if not self.config.sync_completed and dida_task.get("status") == 2:
                continue
            
            dida_id = dida_task.get("id")
            dida_modified_time = dida_task.get("modifiedTime")
            
            # 转换为Zectrix待办格式
            zectrix_todo_data = Mapper.dida_to_zectrix(dida_task)
            
            # 检查是否已存在对应待办
            if dida_id in zectrix_todo_map:
                # 更新现有待办
                existing_todo = zectrix_todo_map[dida_id]
                zectrix_update_date = existing_todo.get("updateDate")
                
                # 比较修改时间
                if self.should_update_from_dida(dida_modified_time, zectrix_update_date):
                    logger.info(f"任务：{dida_task.get('title')}，DIDA365 ➡️ Zectrix")
                    result = self.zectrix_api.update_todo(existing_todo.get("id"), zectrix_todo_data)
                    if result is None:
                        logger.warning(f"任务：{dida_task.get('title')}，❌ Zectrix 更新失败")
                # else:
                    # logger.info(f"任务：{dida_task.get('title')}，Zectrix 较新，跳过更新")
            else:
                # 创建新待办
                logger.info(f"任务：{dida_task.get('title')}，✏️ Zectrix 新建")
                result = self.zectrix_api.create_todo(zectrix_todo_data)
                if result is None:
                    logger.warning(f"任务：{dida_task.get('title')}，❌ Zectrix 新建失败")
        
        logger.info("===================================================")
        
        # 同步Zectrix到DIDA365
        for zectrix_todo in zectrix_todos:
            # 跳过已完成任务（如果配置了不同步已完成任务）
            if not self.config.sync_completed and zectrix_todo.get("completed"):
                continue
            
            zectrix_update_date = zectrix_todo.get("updateDate")
            
            # 转换为DIDA365任务格式
            dida_task_data = Mapper.zectrix_to_dida(zectrix_todo)
            dida_id = dida_task_data.get("id")
            
            # 检查是否已存在对应任务
            if dida_id and dida_id in dida_task_map:
                # 更新现有任务
                original_task = dida_task_map[dida_id]
                dida_modified_time = original_task.get("modifiedTime")
                
                # 比较修改时间
                if self.should_update_from_zectrix(zectrix_update_date, dida_modified_time):
                    logger.info(f"任务：{zectrix_todo.get('title')}，Zectrix ➡️ DIDA365")
                    # 确保请求体包含必要的字段
                    if "id" not in dida_task_data:
                        dida_task_data["id"] = dida_id
                    if "projectId" not in dida_task_data:
                        dida_task_data["projectId"] = original_task.get("projectId")
                    if "title" not in dida_task_data:
                        dida_task_data["title"] = zectrix_todo.get("title")
                    result = self.dida_api.update_task(dida_id, dida_task_data)
                    if result is None:
                        logger.warning(f"任务：{zectrix_todo.get('title')}，❌ DIDA365 更新失败")
                else:
                    logger.info(f"任务：{zectrix_todo.get('title')}，DIDA365 较新，跳过更新")
            else:
                # 创建新任务
                logger.info(f"任务：{zectrix_todo.get('title')}，✏️ DIDA365 新建")
                # 移除id字段，因为创建API不需要
                if "id" in dida_task_data:
                    del dida_task_data["id"]
                # 添加项目ID
                dida_task_data["projectId"] = self.config.target_project_id
                result = self.dida_api.create_task(dida_task_data)
                if result is None:
                    logger.warning(f"任务：{zectrix_todo.get('title')}，❌ DIDA365 新建失败")
    
    def stop_scheduler(self):
        """停止定时同步任务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时同步任务已停止")
