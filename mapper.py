import re
from datetime import datetime
import pytz


class Mapper:
    @staticmethod
    def _parse_dida_datetime(date_str):
        """解析DIDA日期字符串，兼容Z和+0000等时区格式"""
        if not date_str:
            return None

        normalized = date_str.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        # 将 +0800 / -0500 规范为 +08:00 / -05:00
        tz_match = re.search(r"([+-]\d{2})(\d{2})$", normalized)
        if tz_match:
            normalized = normalized[:-5] + \
                tz_match.group(1) + ":" + tz_match.group(2)

        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    @staticmethod
    def dida_to_zectrix(dida_task):
        """将DIDA365任务转换为Zectrix待办"""
        # 提取DIDA365任务ID
        dida_id = dida_task.get("id")

        # 转换标题和内容
        title = dida_task.get("title", "")
        content = dida_task.get("content", "")

        # 转换截止日期和时间
        due_date = None
        due_time = None
        dida_due_date = dida_task.get("dueDate")
        dida_start_date = dida_task.get("startDate")
        # 当DIDA任务的startDate和dueDate都为空时，设置Zectrix的dueDate和dueTime为null
        if not dida_due_date and not dida_start_date:
            due_date = None
            due_time = None
        elif dida_due_date:
            try:
                dt = Mapper._parse_dida_datetime(dida_due_date)
                if not dt:
                    raise ValueError("invalid dida dueDate")

                local_tz = pytz.timezone("Asia/Shanghai")
                dt_local = dt.astimezone(
                    local_tz) if dt.tzinfo else local_tz.localize(dt)

                due_date = dt_local.strftime("%Y-%m-%d")
                # 检查是否是全天任务
                is_all_day = dida_task.get("isAllDay", False)
                # 如果不是全天任务，提取时间
                if not is_all_day:
                    # 检查时间是否为00:00
                    if dt_local.hour != 0 or dt_local.minute != 0:
                        due_time = dt_local.strftime("%H:%M")
            except Exception:
                pass

        # 转换优先级
        priority = Mapper.map_priority(dida_task.get("priority", 0))

        # 转换状态
        status = 1 if dida_task.get("status", 0) == 2 else 0
        completed = status == 1

        # 构建描述，包含DIDA365任务ID
        description = content
        if dida_id:
            if description:
                description += f" [DIDA365:{dida_id}]"
            else:
                description = f"[DIDA365:{dida_id}]"

        return {
            "title": title,
            "description": description,
            "dueDate": due_date,
            "dueTime": due_time,
            "priority": priority,
            "status": status
        }

    @staticmethod
    def zectrix_to_dida(zectrix_todo):
        """将Zectrix待办转换为DIDA365任务"""
        # 解析描述，提取DIDA365任务ID
        description = zectrix_todo.get("description", "")
        dida_id = Mapper.extract_dida_id(description)

        # 提取纯描述内容（不含DIDA365任务ID）
        content = Mapper.remove_dida_id(description)

        # 转换标题
        title = zectrix_todo.get("title", "")

        # 转换截止日期和时间
        due_date = None
        start_date = None
        zectrix_due_date = zectrix_todo.get("dueDate")
        zectrix_due_time = zectrix_todo.get("dueTime")
        # 当dueDate和dueTime都为null时，认定提醒时间为空，不设置startDate和dueDate
        if zectrix_due_date and zectrix_due_time:
            try:
                import pytz
                local_tz = pytz.timezone('Asia/Shanghai')
                # 有固定时间，设置startDate和dueDate为相同值
                dt_str = f"{zectrix_due_date} {zectrix_due_time}"
                dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                # 转换为本地时区，再转换为UTC
                dt_local = local_tz.localize(dt)
                dt_utc = dt_local.astimezone(pytz.utc)
                due_date = dt_utc.isoformat().replace('+00:00', 'Z')
                start_date = due_date
            except Exception:
                pass
        elif zectrix_due_date:
            try:
                import pytz
                local_tz = pytz.timezone('Asia/Shanghai')
                # 只有日期，没有时间，设置startDate和dueDate为相同值
                dt = datetime.strptime(zectrix_due_date, "%Y-%m-%d")
                # 转换为本地时区的0点，再转换为UTC
                dt_local = local_tz.localize(dt)
                dt_utc = dt_local.astimezone(pytz.utc)
                due_date = dt_utc.strftime("%Y-%m-%d") + "T00:00:00Z"
                start_date = due_date
            except Exception:
                pass

        # 转换优先级
        priority = Mapper.reverse_map_priority(zectrix_todo.get("priority", 0))

        # 转换状态
        status = 2 if zectrix_todo.get("completed", False) else 0

        result = {
            "id": dida_id,
            "title": title,
            "content": content,
            "priority": priority,
            "status": status
        }

        # 只有当due_date不为空时才添加dueDate和startDate字段
        if due_date:
            result["dueDate"] = due_date
            result["startDate"] = start_date

        return result

    @staticmethod
    def map_priority(dida_priority):
        """映射DIDA365优先级到Zectrix优先级"""
        priority_map = {
            0: 0,  # 无 -> 普通
            1: 0,  # 低 -> 普通
            3: 1,  # 中 -> 重要
            5: 2   # 高 -> 紧急
        }
        return priority_map.get(dida_priority, 0)

    @staticmethod
    def reverse_map_priority(zectrix_priority):
        """映射Zectrix优先级到DIDA365优先级"""
        priority_map = {
            0: 0,  # 普通 -> 无
            1: 3,  # 重要 -> 中
            2: 5   # 紧急 -> 高
        }
        return priority_map.get(zectrix_priority, 0)

    @staticmethod
    def extract_dida_id(description):
        """从描述中提取DIDA365任务ID"""
        if not description:
            return None
        match = re.search(r"\[DIDA365:(.*?)\]", description)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def remove_dida_id(description):
        """从描述中移除DIDA365任务ID"""
        if not description:
            return ""
        return re.sub(r"\s*\[DIDA365:.*?\]\s*", "", description).strip()
