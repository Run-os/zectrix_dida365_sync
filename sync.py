import json
import logging
import os
from datetime import datetime
from mapper import Mapper

logger = logging.getLogger(__name__)

_SYNC_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sync_state.json"
)


class SyncManager:
    def __init__(self, dida_api, zectrix_api, config):
        self.dida_api = dida_api
        self.zectrix_api = zectrix_api
        self.config = config
        self.last_sync_time = None
        self.last_sync_completion_time = self._load_last_sync_time()

    def _load_last_sync_time(self):
        """从状态文件加载上次同步完成的 Unix 时间戳"""
        try:
            if os.path.exists(_SYNC_STATE_FILE):
                with open(_SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("last_sync_completion_time")
        except Exception:
            pass
        return None

    def _save_last_sync_time(self):
        """将当前 UTC 时间戳保存为上次同步完成时间"""
        try:
            from datetime import timezone
            ts = int(datetime.now(timezone.utc).timestamp())
            with open(_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_sync_completion_time": ts}, f)
            self.last_sync_completion_time = ts
        except Exception as e:
            logger.warning(f"保存同步状态失败: {str(e)}")

    @staticmethod
    def _extract_created_task_id(result):
        """从创建接口返回中提取任务ID"""
        if not isinstance(result, dict):
            return None

        if result.get("id"):
            return result.get("id")

        data = result.get("data")
        if isinstance(data, dict):
            if data.get("id"):
                return data.get("id")
            nested_id = SyncManager._extract_created_task_id(data)
            if nested_id:
                return nested_id

        return None

    @staticmethod
    def _build_zectrix_description(description, dida_id):
        """把DIDA任务ID写回Zectrix描述"""
        clean_description = Mapper.remove_dida_id(description).strip()
        marker = f"[DIDA365:{dida_id}]"
        if clean_description:
            return f"{clean_description} {marker}"
        return marker

    def sync(self):
        """执行同步"""
        try:
            logger.info("🔄 同步任务开始")
            self.bidirectional_sync()

            # 更新最后同步时间
            self.last_sync_time = datetime.now()
            self._save_last_sync_time()
            logger.info("✅ 同步任务全部完成")
        except Exception as e:
            logger.error(f"❌ 同步失败: {str(e)}")
            # 抛出异常，停止同步服务
            raise

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
            dt = datetime.fromisoformat(
                dida_modified_time.replace("Z", "+00:00"))
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
            dt = datetime.fromisoformat(
                dida_modified_time.replace("Z", "+00:00"))
            dida_timestamp = int(dt.timestamp())

            # 比较时间戳
            return zectrix_update_date > dida_timestamp
        except Exception:
            # 如果解析失败，默认更新
            return True

    def bidirectional_sync(self):
        """双向同步，避免循环更新"""
        # 获取DIDA365项目任务
        project_tasks = self.dida_api.get_project_tasks(
            self.config.DIDA_PROJECT_ID)
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

        # 先做完成态联动，避免后续常规更新把状态拉回。
        for zectrix_todo in zectrix_todos:
            description = zectrix_todo.get("description", "")
            dida_id = Mapper.extract_dida_id(description)
            if not dida_id:
                continue

            zectrix_todo_id = zectrix_todo.get("id")
            zectrix_completed = bool(zectrix_todo.get("completed", False))

            if dida_id in dida_task_map:
                dida_task = dida_task_map[dida_id]
                dida_status = dida_task.get("status", 0)
                if zectrix_completed and dida_status != 2:
                    project_id = dida_task.get(
                        "projectId") or self.config.DIDA_PROJECT_ID
                    logger.info(
                        f"完成态联动：Zectrix任务已完成，标记DIDA365任务完成，任务ID：{dida_id}")
                    result = self.dida_api.complete_task(project_id, dida_id)
                    if result is None:
                        logger.warning(
                            f"完成态联动失败：DIDA365任务完成失败，任务ID：{dida_id}")
                    else:
                        dida_task["status"] = 2
            else:
                # Zectrix里有映射ID，但DIDA列表中不存在，视为DIDA已完成，回写完成状态到Zectrix。
                if not zectrix_completed and zectrix_todo_id:
                    logger.info(
                        f"完成态联动：DIDA365任务不存在，标记Zectrix任务完成，任务ID：{zectrix_todo_id}")
                    try:
                        result = self.zectrix_api.complete_todo(
                            zectrix_todo_id)
                        if result:
                            zectrix_todo["completed"] = True
                    except Exception as e:
                        logger.warning(
                            f"完成态联动失败：Zectrix任务完成失败，任务ID：{zectrix_todo_id}，错误：{str(e)}")

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
                existing_completed = existing_todo.get("completed", False)
                new_completed = zectrix_todo_data.get("completed", False)

                # 比较修改时间
                if self.should_update_from_dida(dida_modified_time, zectrix_update_date):
                    logger.info(
                        f"任务：{dida_task.get('title')}，DIDA365 ➡️ Zectrix")
                    # 先更新任务基本信息
                    result = self.zectrix_api.update_todo(
                        existing_todo.get("id"), zectrix_todo_data)
                    if result is None:
                        logger.warning(
                            f"任务：{dida_task.get('title')}，❌ Zectrix 更新失败")
                    else:
                        # 检查状态是否需要切换
                        if existing_completed != new_completed:
                            logger.info(
                                f"任务：{dida_task.get('title')}，状态切换：{existing_completed} → {new_completed}")
                            # 调用complete接口切换状态
                            try:
                                logger.info(
                                    f"调用Zectrix API切换任务状态，任务ID：{existing_todo.get('id')}")
                                result = self.zectrix_api.complete_todo(
                                    existing_todo.get("id"))
                                logger.info(
                                    f"任务：{dida_task.get('title')}，状态切换成功，结果：{result}")
                            except Exception as e:
                                logger.warning(
                                    f"任务：{dida_task.get('title')}，❌ 状态切换失败：{str(e)}")
                # else:
                    # logger.info(f"任务：{dida_task.get('title')}，Zectrix 较新，跳过更新")
            else:
                # 创建新待办
                logger.info(f"任务：{dida_task.get('title')}，✏️ Zectrix 新建")
                result = self.zectrix_api.create_todo(zectrix_todo_data)
                if result is None:
                    logger.warning(
                        f"任务：{dida_task.get('title')}，❌ Zectrix 新建失败")

        logger.info("===================================================")

        # 同步Zectrix到DIDA365
        for zectrix_todo in zectrix_todos:
            # 跳过已完成任务（如果配置了不同步已完成任务）
            if not self.config.sync_completed and zectrix_todo.get("completed"):
                continue

            zectrix_update_date = zectrix_todo.get("updateDate")
            # logger.info(f"处理Zectrix待办：{zectrix_todo.get('title')}，更新时间：{zectrix_update_date}")

            # 转换为DIDA365任务格式
            dida_task_data = Mapper.zectrix_to_dida(zectrix_todo)
            dida_id = dida_task_data.get("id")

            # 检查是否已存在对应任务
            if dida_id and dida_id in dida_task_map:
                # 更新现有任务
                original_task = dida_task_map[dida_id]
                dida_modified_time = original_task.get("modifiedTime")
                # logger.info(f"找到对应DIDA365任务：{original_task.get('title')}，修改时间：{dida_modified_time}")

                # 如果Zectrix的更新时间不超过上次同步完成时间，说明该时间戳由上次同步写入，
                # 并非用户在Zectrix侧主动修改，跳过反向更新以避免覆盖DIDA中的最新数据。
                if (
                    self.last_sync_completion_time
                    and zectrix_update_date
                    and zectrix_update_date <= self.last_sync_completion_time
                ):
                    logger.info(
                        f"任务：{zectrix_todo.get('title')}，"
                        f"Zectrix更新时间未超过上次同步完成时间，跳过反向更新")
                    continue

                # 比较修改时间
                if self.should_update_from_zectrix(zectrix_update_date, dida_modified_time):
                    logger.info(
                        f"任务：{zectrix_todo.get('title')}，Zectrix ➡️ DIDA365")
                    # 确保请求体包含必要的字段
                    if "id" not in dida_task_data:
                        dida_task_data["id"] = dida_id
                    if "projectId" not in dida_task_data:
                        dida_task_data["projectId"] = original_task.get(
                            "projectId")
                    if "title" not in dida_task_data:
                        dida_task_data["title"] = zectrix_todo.get("title")
                    result = self.dida_api.update_task(dida_id, dida_task_data)
                    if result is None:
                        logger.warning(
                            f"任务：{zectrix_todo.get('title')}，❌ DIDA365 更新失败")
                else:
                    logger.info(
                        f"任务：{zectrix_todo.get('title')}，DIDA365 较新，跳过更新")
            else:
                # 创建新任务
                logger.info(f"任务：{zectrix_todo.get('title')}，✏️ DIDA365 新建")
                # 移除id字段，因为创建API不需要
                if "id" in dida_task_data:
                    del dida_task_data["id"]
                # 添加项目ID
                dida_task_data["projectId"] = self.config.DIDA_PROJECT_ID
                result = self.dida_api.create_task(dida_task_data)
                if result is None:
                    logger.warning(
                        f"任务：{zectrix_todo.get('title')}，❌ DIDA365 新建失败")
                else:
                    created_dida_id = self._extract_created_task_id(result)
                    zectrix_todo_id = zectrix_todo.get("id")
                    if created_dida_id and zectrix_todo_id:
                        updated_description = self._build_zectrix_description(
                            zectrix_todo.get("description", ""), created_dida_id)
                        if updated_description != zectrix_todo.get("description", ""):
                            try:
                                self.zectrix_api.update_todo(
                                    zectrix_todo_id,
                                    {"description": updated_description}
                                )
                                zectrix_todo["description"] = updated_description
                                zectrix_todo_map[created_dida_id] = zectrix_todo
                            except Exception as e:
                                logger.warning(
                                    f"任务：{zectrix_todo.get('title')}，DIDA ID 回写 Zectrix 失败：{str(e)}")
