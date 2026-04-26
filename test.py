import logging
import unicodedata
from config import Config
from dida_api import DidaAPI
from zectrix_api import ZectrixAPI
from mapper import Mapper
from sync import SyncManager
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


def test_backfill_zectrix_link_after_creating_dida_task():
    """测试首次从Zectrix创建DIDA任务后，会把DIDA ID回写到Zectrix任务中"""
    try:
        class FakeConfig:
            DIDA_PROJECT_ID = "project_1"
            sync_completed = True

        class FakeDidaAPI:
            def __init__(self):
                self.tasks = []
                self.created_count = 0

            def get_tasks(self, status=0):
                return list(self.tasks)

            def get_project_tasks(self, project_id):
                return {"tasks": list(self.tasks)}

            def create_task(self, task_data):
                self.created_count += 1
                task_id = f"dida_{self.created_count}"
                created_task = dict(task_data)
                created_task["id"] = task_id
                created_task.setdefault(
                    "projectId", FakeConfig.DIDA_PROJECT_ID)
                self.tasks.append(created_task)
                return created_task

            def update_task(self, task_id, task_data):
                return task_data

            def complete_task(self, project_id, task_id):
                return {"success": True}

        class FakeZectrixAPI:
            def __init__(self):
                self.todos = [{
                    "id": "z1",
                    "title": "测试3",
                    "description": "",
                    "dueDate": None,
                    "dueTime": None,
                    "priority": 0,
                    "completed": False,
                    "updateDate": 200
                }]
                self.created_count = 0
                self.updated_payloads = []

            def get_todos(self, status=None):
                return [dict(todo) for todo in self.todos]

            def create_todo(self, todo_data):
                self.created_count += 1
                todo = dict(todo_data)
                todo["id"] = f"z_new_{self.created_count}"
                self.todos.append(todo)
                return todo

            def update_todo(self, todo_id, todo_data):
                self.updated_payloads.append((todo_id, dict(todo_data)))
                for todo in self.todos:
                    if todo.get("id") == todo_id:
                        todo.update(todo_data)
                        return todo
                return None

            def complete_todo(self, todo_id):
                return True

        dida_api = FakeDidaAPI()
        zectrix_api = FakeZectrixAPI()
        sync_manager = SyncManager(dida_api, zectrix_api, FakeConfig())

        sync_manager.sync()
        sync_manager.sync()

        assert dida_api.created_count == 1, f"DIDA任务被重复创建: {dida_api.created_count}"
        assert len(zectrix_api.updated_payloads) >= 1, "Zectrix任务没有回写DIDA ID"
        assert any(
            "[DIDA365:dida_1]" in payload.get("description", "")
            for _, payload in zectrix_api.updated_payloads
        ), "回写的Zectrix description 未包含DIDA ID标记"

        return True
    except Exception as e:
        logger.error(f"Zectrix关联回写测试失败: {str(e)}")
        return False


def test_no_reverse_sync_after_dida_to_zectrix():
    """测试DIDA365同步至Zectrix后，下次同步不应将Zectrix旧数据反向覆盖DIDA365"""
    try:
        class FakeConfig:
            DIDA_PROJECT_ID = "project_1"
            sync_completed = True

        # 用户在DIDA365中修改了截止时间，modifiedTime = T2
        dida_modified_time = "2024-01-15T10:00:00.000Z"
        dida_modified_ts = 1705312800  # Unix timestamp for 2024-01-15T10:00:00Z

        # 模拟上次同步完成时间 T3 > T2（上次同步将DIDA数据写入Zectrix，导致Zectrix updateDate = T3）
        last_sync_ts = dida_modified_ts + 120  # T3

        class FakeDidaAPI:
            def __init__(self):
                self.tasks = [{
                    "id": "dida_1",
                    "title": "测试任务",
                    "content": "",
                    "dueDate": "2024-01-15T10:00:00.000Z",
                    "priority": 0,
                    "status": 0,
                    "modifiedTime": dida_modified_time,
                    "projectId": "project_1"
                }]
                self.update_calls = []

            def get_tasks(self, status=0):
                return list(self.tasks)

            def get_project_tasks(self, project_id):
                return {"tasks": list(self.tasks)}

            def update_task(self, task_id, task_data):
                self.update_calls.append((task_id, dict(task_data)))
                return task_data

            def create_task(self, task_data):
                return task_data

            def complete_task(self, project_id, task_id):
                return {"success": True}

        class FakeZectrixAPI:
            def __init__(self):
                self.todos = [{
                    "id": "z1",
                    "title": "测试任务",
                    "description": "[DIDA365:dida_1]",
                    "dueDate": "2024-01-15",
                    "dueTime": "18:00",
                    "priority": 0,
                    "completed": False,
                    # updateDate = T3（由上次同步写入，晚于DIDA的modifiedTime T2）
                    "updateDate": last_sync_ts
                }]
                self.update_calls = []

            def get_todos(self, status=None):
                return [dict(todo) for todo in self.todos]

            def update_todo(self, todo_id, todo_data):
                self.update_calls.append((todo_id, dict(todo_data)))
                return todo_data

            def complete_todo(self, todo_id):
                return True

        dida_api = FakeDidaAPI()
        zectrix_api = FakeZectrixAPI()
        sync_manager = SyncManager(dida_api, zectrix_api, FakeConfig())

        # 注入上次同步完成时间（模拟跨次运行状态）
        sync_manager.last_sync_completion_time = last_sync_ts

        sync_manager.sync()

        # 不应触发反向 Zectrix→DIDA 更新
        assert len(dida_api.update_calls) == 0, \
            f"不应触发反向DIDA更新，但实际触发了: {dida_api.update_calls}"

        # 场景2：用户在Zectrix侧手动修改（updateDate > last_sync_ts），且核心字段发生变化，此时应允许同步
        dida_api2 = FakeDidaAPI()
        zectrix_api2 = FakeZectrixAPI()
        zectrix_api2.todos[0]["updateDate"] = last_sync_ts + \
            300  # 用户改动发生在上次同步之后
        zectrix_api2.todos[0]["title"] = "测试任务-已修改"  # 核心字段变化，应该触发反向更新

        sync_manager2 = SyncManager(dida_api2, zectrix_api2, FakeConfig())
        sync_manager2.last_sync_completion_time = last_sync_ts

        sync_manager2.sync()

        # Zectrix侧有真实改动（核心字段变化），应触发 Zectrix→DIDA 更新
        assert len(dida_api2.update_calls) >= 1, \
            f"Zectrix侧有真实改动时，应触发DIDA更新，但实际未触发"

        return True
    except Exception as e:
        logger.error(f"反向同步防护测试失败: {str(e)}")
        return False


def test_skip_update_when_fingerprint_unchanged():
    """测试四字段（dueDate/content/title/status）不变时，双向更新都应跳过"""
    try:
        class FakeConfig:
            DIDA_PROJECT_ID = "project_1"
            sync_completed = True

        class FakeDidaAPI:
            def __init__(self):
                self.tasks = [
                    {
                        "id": "dida_1",
                        "projectId": "project_1",
                        "title": "任务A",
                        "content": "内容A",
                        "dueDate": "2024-01-15T10:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        # dida_1 比 zectrix 更“新”，会进入 DIDA -> Zectrix 更新分支
                        "modifiedTime": "2024-01-15T11:00:00.000Z"
                    },
                    {
                        "id": "dida_2",
                        "projectId": "project_1",
                        "title": "任务B",
                        "content": "内容B",
                        "dueDate": "2024-01-15T12:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        # dida_2 比 zectrix 更“旧”，会进入 Zectrix -> DIDA 更新分支
                        "modifiedTime": "2024-01-15T09:00:00.000Z"
                    }
                ]
                self.update_calls = []

            def get_tasks(self, status=0):
                return list(self.tasks)

            def get_project_tasks(self, project_id):
                return {"tasks": list(self.tasks)}

            def update_task(self, task_id, task_data):
                self.update_calls.append((task_id, dict(task_data)))
                return task_data

            def create_task(self, task_data):
                return task_data

            def complete_task(self, project_id, task_id):
                return {"success": True}

        class FakeZectrixAPI:
            def __init__(self):
                dida_task_1 = {
                    "id": "dida_1",
                    "title": "任务A",
                    "content": "内容A",
                    "dueDate": "2024-01-15T10:00:00.000Z",
                    "isAllDay": False,
                    "priority": 0,
                    "status": 0
                }
                dida_task_2 = {
                    "id": "dida_2",
                    "title": "任务B",
                    "content": "内容B",
                    "dueDate": "2024-01-15T12:00:00.000Z",
                    "isAllDay": False,
                    "priority": 0,
                    "status": 0
                }

                mapped_1 = Mapper.dida_to_zectrix(dida_task_1)
                mapped_2 = Mapper.dida_to_zectrix(dida_task_2)

                self.todos = [
                    {
                        "id": "z1",
                        "title": mapped_1.get("title"),
                        "description": mapped_1.get("description"),
                        "dueDate": mapped_1.get("dueDate"),
                        "dueTime": mapped_1.get("dueTime"),
                        "priority": mapped_1.get("priority"),
                        "completed": mapped_1.get("status") == 1,
                        # 比 dida_1 的 modifiedTime 更旧
                        "updateDate": 1705310000
                    },
                    {
                        "id": "z2",
                        "title": mapped_2.get("title"),
                        "description": mapped_2.get("description"),
                        "dueDate": mapped_2.get("dueDate"),
                        "dueTime": mapped_2.get("dueTime"),
                        "priority": mapped_2.get("priority"),
                        "completed": mapped_2.get("status") == 1,
                        # 比 dida_2 的 modifiedTime 更晚
                        "updateDate": 1705320000
                    }
                ]
                self.update_calls = []

            def get_todos(self, status=None):
                return [dict(todo) for todo in self.todos]

            def update_todo(self, todo_id, todo_data):
                self.update_calls.append((todo_id, dict(todo_data)))
                return todo_data

            def create_todo(self, todo_data):
                return todo_data

            def complete_todo(self, todo_id):
                return True

        dida_api = FakeDidaAPI()
        zectrix_api = FakeZectrixAPI()
        sync_manager = SyncManager(dida_api, zectrix_api, FakeConfig())

        sync_manager.sync()

        assert len(zectrix_api.update_calls) == 0, \
            f"四字段未变化时不应更新 Zectrix，但实际调用: {zectrix_api.update_calls}"
        assert len(dida_api.update_calls) == 0, \
            f"四字段未变化时不应更新 DIDA365，但实际调用: {dida_api.update_calls}"

        return True
    except Exception as e:
        logger.error(f"字段指纹跳过更新测试失败: {str(e)}")
        return False


def test_sync_loads_unfinished_dida_tasks_via_status_filter():
    """测试同步时读取 DIDA365 任务应走 status=0 的过滤接口，而不是项目列表接口"""
    try:
        class FakeConfig:
            DIDA_PROJECT_ID = "project_1"
            sync_completed = True

        class FakeDidaAPI:
            def __init__(self):
                self.calls = []

            def get_tasks(self, status=None):
                self.calls.append(status)
                assert status == 0, f"应请求未完成任务 status=0，但实际为: {status}"
                return [
                    {
                        "id": "dida_1",
                        "projectId": "project_1",
                        "title": "任务A",
                        "content": "内容A",
                        "dueDate": "2024-01-15T10:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        "modifiedTime": "2024-01-15T11:00:00.000Z"
                    }
                ]

            def get_project_tasks(self, project_id):
                raise AssertionError("不应再调用 get_project_tasks 拉取项目任务")

            def create_task(self, task_data):
                return task_data

            def update_task(self, task_id, task_data):
                return task_data

            def complete_task(self, project_id, task_id):
                return {"success": True}

        class FakeZectrixAPI:
            def __init__(self):
                self.todos = []

            def get_todos(self, status=None):
                return []

            def create_todo(self, todo_data):
                return todo_data

            def update_todo(self, todo_id, todo_data):
                return todo_data

            def complete_todo(self, todo_id):
                return True

        dida_api = FakeDidaAPI()
        zectrix_api = FakeZectrixAPI()
        sync_manager = SyncManager(dida_api, zectrix_api, FakeConfig())

        sync_manager.sync()

        assert dida_api.calls == [0], f"DIDA 过滤接口调用异常: {dida_api.calls}"
        return True
    except Exception as e:
        logger.error(f"DIDA未完成任务过滤接口测试失败: {str(e)}")
        return False


def test_skip_note_kind_tasks():
    """测试同步时会跳过 kind=NOTE，只同步 TEXT 和 CHECKLIST"""
    try:
        class FakeConfig:
            DIDA_PROJECT_ID = "project_1"
            sync_completed = True

        class FakeDidaAPI:
            def __init__(self):
                self.tasks = [
                    {
                        "id": "dida_text",
                        "projectId": "project_1",
                        "title": "文本任务",
                        "content": "文本内容",
                        "dueDate": "2024-01-15T10:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        "kind": "TEXT",
                        "modifiedTime": "2024-01-15T11:00:00.000Z"
                    },
                    {
                        "id": "dida_note",
                        "projectId": "project_1",
                        "title": "便签",
                        "content": "便签内容",
                        "dueDate": "2024-01-16T10:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        "kind": "NOTE",
                        "modifiedTime": "2024-01-16T11:00:00.000Z"
                    },
                    {
                        "id": "dida_checklist",
                        "projectId": "project_1",
                        "title": "清单",
                        "content": "清单内容",
                        "dueDate": "2024-01-17T10:00:00.000Z",
                        "isAllDay": False,
                        "status": 0,
                        "priority": 0,
                        "kind": "CHECKLIST",
                        "modifiedTime": "2024-01-17T11:00:00.000Z"
                    }
                ]
                self.created_count = 0

            def get_tasks(self, status=0):
                return list(self.tasks)

            def create_task(self, task_data):
                self.created_count += 1
                return task_data

            def update_task(self, task_id, task_data):
                return task_data

            def complete_task(self, project_id, task_id):
                return {"success": True}

        class FakeZectrixAPI:
            def __init__(self):
                self.todos = [
                    {
                        "id": "z_note",
                        "title": "便签同步标记",
                        "description": "便签内容 [DIDA365:dida_note]",
                        "dueDate": "2024-01-16",
                        "dueTime": "10:00",
                        "priority": 0,
                        "completed": False,
                        "updateDate": 200
                    }
                ]
                self.created_payloads = []

            def get_todos(self, status=None):
                return [dict(todo) for todo in self.todos]

            def create_todo(self, todo_data):
                self.created_payloads.append(dict(todo_data))
                return {"id": f"todo_{len(self.created_payloads)}"}

            def update_todo(self, todo_id, todo_data):
                return todo_data

            def complete_todo(self, todo_id):
                return True

        dida_api = FakeDidaAPI()
        zectrix_api = FakeZectrixAPI()
        sync_manager = SyncManager(dida_api, zectrix_api, FakeConfig())

        sync_manager.sync()

        assert len(zectrix_api.created_payloads) == 2, \
            f"应只同步 TEXT 和 CHECKLIST，但实际创建了: {len(zectrix_api.created_payloads)} 个"
        created_titles = {payload.get("title")
                          for payload in zectrix_api.created_payloads}
        assert created_titles == {"文本任务", "清单"}, \
            f"同步结果不正确，实际创建标题: {created_titles}"

        return True
    except Exception as e:
        logger.error(f"NOTE 类型过滤测试失败: {str(e)}")
        return False


def _visual_width(text):
    total = 0
    for ch in str(text or ""):
        if unicodedata.combining(ch):
            continue
        total += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return total


def test_task_log_visual_alignment():
    """测试中英文混合任务名下，状态字段起始列在终端视觉上对齐"""
    try:
        msg_a = SyncManager._format_task_log(
            "养老保险-老妈", "核心字段未变化，跳过 Zectrix ➡️ DIDA365"
        )
        msg_b = SyncManager._format_task_log(
            "freeAI-task-001", "核心字段未变化，跳过 Zectrix ➡️ DIDA365"
        )

        marker = " 状态："
        left_a = msg_a.split(marker, 1)[0]
        left_b = msg_b.split(marker, 1)[0]

        assert marker in msg_a and marker in msg_b, "日志格式缺少状态字段分隔标记"
        assert _visual_width(left_a) == _visual_width(left_b), \
            f"状态列未对齐: {msg_a} | {msg_b}"

        return True
    except Exception as e:
        logger.error(f"任务日志视觉对齐测试失败: {str(e)}")
        return False


def main():
    """运行所有测试"""
    logger.info("开始测试...")

    # 测试配置
    config_test = test_config()

    # 测试数据映射
    mapper_test = test_mapper()

    # 测试新建任务后的关联回写
    link_backfill_test = test_backfill_zectrix_link_after_creating_dida_task()

    # 测试跨次运行的反向同步防护
    reverse_sync_test = test_no_reverse_sync_after_dida_to_zectrix()

    # 测试四字段指纹不变时跳过更新
    fingerprint_skip_test = test_skip_update_when_fingerprint_unchanged()

    # 测试同步时通过 status=0 获取 DIDA 未完成任务
    unfinished_filter_test = test_sync_loads_unfinished_dida_tasks_via_status_filter()

    # 测试只同步 TEXT 和 CHECKLIST
    note_kind_filter_test = test_skip_note_kind_tasks()

    # 测试任务日志中英混排视觉对齐
    task_log_alignment_test = test_task_log_visual_alignment()

    if mapper_test and link_backfill_test and reverse_sync_test and fingerprint_skip_test and unfinished_filter_test and note_kind_filter_test and task_log_alignment_test:
        logger.info("所有测试通过！")
    else:
        logger.error("测试失败！")


if __name__ == "__main__":
    main()
