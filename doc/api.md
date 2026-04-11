# Zectrix DIDA365 Sync

Zectrix 墨水屏待办事项与滴答清单（DIDA365）之间的同步工具。

---

## 目录

- [Zectrix DIDA365 Sync](#zectrix-dida365-sync)
  - [目录](#目录)
  - [环境配置](#环境配置)
    - [变量说明](#变量说明)
    - [示例 `.env` 文件](#示例-env-文件)
    - [运行前加载](#运行前加载)
  - [DIDA365 API](#dida365-api)
    - [获取项目列表](#获取项目列表)
    - [获取项目任务](#获取项目任务)
    - [创建任务](#创建任务)
  - [Zectrix API](#zectrix-api)
    - [获取待办列表](#获取待办列表)
    - [创建待办](#创建待办)
    - [标记完成/取消完成](#标记完成取消完成)

---

## 环境配置

所有配置通过 `.env` 文件以**环境变量**方式注入。

### 变量说明

| 变量名       | 类型   | 必填 | 说明                        |
|--------------|--------|------|-----------------------------|
| `API_BASE`   | string | 是   | Zectrix API 基础地址        |
| `API_KEY`    | string | 是   | Zectrix API 密钥            |
| `DEVICE_ID`  | string | 是   | Zectrix 设备 ID（MAC 地址） |
| `dida_token` | string | 是   | DIDA365 OAuth Bearer Token  |

### 示例 `.env` 文件

```env
# Zectrix API 配置
API_BASE=https://cloud.zectrix.com/open/v1
API_KEY=your-api-key
DEVICE_ID=your-device-id

# DIDA365 配置
dida_token=your-token
```

### 运行前加载

```python
import dotenv
dotenv.load_dotenv()
import sync_dida
```

---

## DIDA365 API

**基础地址：** `https://api.dida365.com/open/v1`

**认证方式：** Bearer Token（通过 `Authorization` 请求头传递）

```
Authorization: Bearer <dida_token>
```

---

### 获取项目列表

获取当前用户的所有项目（清单）。

**请求**

```
GET /project
```

**示例**

```python
import requests

url = "https://api.dida365.com/open/v1/project"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <dida_token>"
}

response = requests.get(url, headers=headers)
print(response.json())
```

**响应**

```json
[
  {
    "id": "418443cb9b0beed47293f1f1",
    "name": "便签",
    "color": "transparent",
    "sortOrder": 0,
    "kind": "NOTE"
  },
  {
    "id": "65ebcc5d769ac798b4718164",
    "name": "👩•🦰老妈-共享",
    "color": "#35D870",
    "sortOrder": -3298534948864,
    "viewMode": "kanban",
    "permission": "write",
    "kind": "TASK"
  },
  {
    "id": "67ea7799eba6f600000003a9",
    "name": "💢工作--循环",
    "color": "#E6EA49",
    "sortOrder": -3848894742528,
    "viewMode": "list",
    "kind": "TASK"
  }
]
```

**响应字段说明**

| 字段         | 类型    | 说明                                       |
|--------------|---------|--------------------------------------------|
| `id`         | string  | 项目唯一标识                               |
| `name`       | string  | 项目名称                                   |
| `color`      | string  | 项目颜色（十六进制或预设值）               |
| `sortOrder`  | integer | 排序权重（值越小越靠前）                   |
| `viewMode`   | string  | 视图模式：`list`（列表）/ `kanban`（看板） |
| `permission` | string  | 权限（共享项目时出现）：`write` / `read`   |
| `kind`       | string  | 项目类型：`TASK`（任务）/ `NOTE`（便签）   |

---

### 获取项目任务

获取指定项目下的所有任务数据，包含任务和看板列信息。

**请求**

```
GET /project/{projectId}/data
```

**路径参数**

| 参数名      | 类型   | 必填 | 说明    |
|-------------|--------|------|---------|
| `projectId` | string | 是   | 项目 ID |

**示例**

```python
import requests

url = "https://api.dida365.com/open/v1/project/67ea77d1eba6f600000003ee/data"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer <dida_token>"
}

response = requests.get(url, headers=headers)
print(response.json())
```

**响应**

```json
{
  "project": {
    "id": "67ea77d1eba6f600000003ee",
    "name": "💼工作",
    "color": "#FF6161",
    "sortOrder": -3849364504576,
    "viewMode": "list",
    "kind": "TASK"
  },
  "tasks": [
    {
      "id": "69ca4a58d392ee9ec6770f6b",
      "projectId": "67ea77d1eba6f600000003ee",
      "sortOrder": -30794916429784,
      "title": "二季度典型材料：纳税信用和社保费",
      "content": "",
      "desc": "",
      "startDate": "2026-06-29T16:00:00.000+0000",
      "dueDate": "2026-06-29T16:00:00.000+0000",
      "timeZone": "Asia/Shanghai",
      "isAllDay": true,
      "priority": 0,
      "status": 0,
      "columnId": "6893891ceba6f600000009d4",
      "etag": "k45zoj7j",
      "kind": "TEXT",
      "modifiedTime": "2026-04-09T12:52:06.000+0000"
    }
  ],
  "columns": [
    {
      "id": "6893891ceba6f600000009d4",
      "projectId": "67ea77d1eba6f600000003ee",
      "name": "紧急",
      "sortOrder": 536870912
    }
  ]
}
```

**Task 字段说明**

| 字段           | 类型    | 说明                                               |
|----------------|---------|----------------------------------------------------|
| `id`           | string  | 任务唯一标识                                       |
| `projectId`    | string  | 所属项目 ID                                        |
| `sortOrder`    | integer | 排序权重                                           |
| `title`        | string  | 任务标题                                           |
| `content`      | string  | 任务内容                                           |
| `desc`         | string  | 任务描述                                           |
| `startDate`    | string  | 开始时间（ISO 8601）                               |
| `dueDate`      | string  | 截止时间（ISO 8601）                               |
| `timeZone`     | string  | 时区                                               |
| `isAllDay`     | boolean | 是否为全天任务                                     |
| `priority`     | integer | 优先级：`0`（无）/ `1`（低）/ `3`（中）/ `5`（高） |
| `status`       | integer | 状态：`0`（待办）/ `2`（已完成）                   |
| `repeatFlag`   | string  | 重复规则（仅重复任务出现）                         |
| `columnId`     | string  | 所属看板列 ID                                      |
| `etag`         | string  | 版本标识                                           |
| `kind`         | string  | 类型：`TEXT` / `CHECKLIST`                         |
| `modifiedTime` | string  | 最后修改时间（ISO 8601）                           |

---

### 创建任务

在指定项目中创建一个新任务。若不指定 `projectId`，任务将创建在收集箱中。

**请求**

```
POST /task
```

**请求体参数**

| 参数名      | 类型    | 必填 | 说明                                               |
|-------------|---------|------|----------------------------------------------------|
| `title`     | string  | 是   | 任务标题                                           |
| `projectId` | string  | 否   | 所属项目 ID，默认为收集箱                          |
| `content`   | string  | 否   | 任务内容                                           |
| `startDate` | string  | 否   | 开始时间（ISO 8601）                               |
| `dueDate`   | string  | 否   | 截止时间（ISO 8601）                               |
| `isAllDay`  | boolean | 否   | 是否全天任务                                       |
| `priority`  | integer | 否   | 优先级：`0`（无）/ `1`（低）/ `3`（中）/ `5`（高） |

**示例**

```bash
curl --request POST \
  --url https://api.dida365.com/open/v1/task \
  --header 'Authorization: Bearer <dida_token>' \
  --header 'Content-Type: application/json' \
  --data '{
    "title": "二季度税费服务诉求相关资料报送",
    "startDate": "2026-04-11T11:01:53.044+0000",
    "content": "AAAAAAAAAnikan你看"
  }'
```

**响应**

```json
{
  "id": "69da2a94e4b075626889b602",
  "projectId": "inbox1014324003",
  "sortOrder": -296486274924544,
  "title": "二季度税费服务诉求相关资料报送",
  "content": "AAAAAAAAAnikan你看",
  "startDate": "2026-04-11T11:01:53.044+0000",
  "dueDate": "2026-04-11T11:01:53.044+0000",
  "timeZone": "Asia/Hong_Kong",
  "isAllDay": false,
  "priority": 0,
  "status": 0,
  "tags": [],
  "etag": "38lkrrnh",
  "kind": "TEXT",
  "modifiedTime": "2026-04-11T11:03:48.614+0000"
}
```

---

## Zectrix API

**基础地址：** `https://cloud.zectrix.com/open/v1`

**认证方式：** API Key（通过 `X-API-Key` 请求头传递）

```
X-API-Key: <API_KEY>
```

---

### 获取待办列表

获取指定设备上的待办事项列表。

**请求**

```
GET /todos?status={status}&deviceId={deviceId}
```

**查询参数**

| 参数名     | 类型    | 必填 | 说明                                   |
|------------|---------|------|----------------------------------------|
| `status`   | integer | 否   | 状态筛选：`0`（未完成）/ `1`（已完成） |
| `deviceId` | string  | 否   | 设备 ID（MAC 地址），URL 编码          |

**示例**

```bash
curl --request GET \
  --url 'https://cloud.zectrix.com/open/v1/todos?status=0&deviceId=9C%3A13%3A9E%3AB5%3A7C%3A00' \
  --header 'X-API-Key: <API_KEY>'
```

**响应**

```json
{
  "code": 0,
  "msg": "success",
  "data": [
    {
      "id": 5192,
      "title": "洗澡",
      "description": null,
      "dueDate": "2026-04-11",
      "dueTime": "18:28",
      "repeatType": "none",
      "repeatWeekday": null,
      "repeatMonth": null,
      "repeatDay": null,
      "status": 0,
      "priority": 0,
      "completed": false,
      "deviceId": "9C:13:9E:B5:7C:00",
      "deviceName": "zectrix-s3-epaper-4.2",
      "createDate": "2026-04-11 18:27",
      "updateDate": 1775934588
    }
  ]
}
```

**Todo 字段说明**

| 字段            | 类型            | 说明                                                         |
|-----------------|-----------------|--------------------------------------------------------------|
| `id`            | integer         | 待办唯一标识                                                 |
| `title`         | string          | 标题                                                         |
| `description`   | string \| null  | 描述                                                         |
| `dueDate`       | string          | 截止日期（`yyyy-MM-dd`）                                     |
| `dueTime`       | string          | 截止时间（`HH:mm`）                                          |
| `repeatType`    | string          | 重复类型：`none` / `daily` / `weekly` / `monthly` / `yearly` |
| `repeatWeekday` | integer \| null | 周几（0-6，0=周日），`weekly` 时使用                         |
| `repeatMonth`   | integer \| null | 几月（1-12），`yearly` 时使用                                |
| `repeatDay`     | integer \| null | 几号（1-31），`monthly` / `yearly` 时使用                    |
| `status`        | integer         | 状态：`0`（未完成）/ `1`（已完成）                           |
| `priority`      | integer         | 优先级：`0`（普通）/ `1`（重要）/ `2`（紧急）                |
| `completed`     | boolean         | 是否已完成                                                   |
| `deviceId`      | string          | 设备 MAC 地址                                                |
| `deviceName`    | string          | 设备名称                                                     |
| `createDate`    | string          | 创建时间（`yyyy-MM-dd HH:mm`）                               |
| `updateDate`    | integer         | 更新时间（Unix 时间戳）                                      |

---

### 创建待办

在指定设备上创建一个新的待办事项。

**请求**

```
POST /todos
```

**请求体参数**

| 参数名          | 类型    | 必填 | 说明                                                         |
|-----------------|---------|------|--------------------------------------------------------------|
| `title`         | string  | 是   | 标题                                                         |
| `description`   | string  | 否   | 描述                                                         |
| `dueDate`       | string  | 否   | 截止日期（`yyyy-MM-dd`）                                     |
| `dueTime`       | string  | 否   | 截止时间（`HH:mm`）                                          |
| `repeatType`    | string  | 否   | 重复类型：`none` / `daily` / `weekly` / `monthly` / `yearly` |
| `repeatWeekday` | integer | 否   | 周几（0-6，0=周日），`weekly` 时使用                         |
| `repeatMonth`   | integer | 否   | 几月（1-12），`yearly` 时使用                                |
| `repeatDay`     | integer | 否   | 几号（1-31），`monthly` / `yearly` 时使用                    |
| `priority`      | integer | 否   | 优先级：`0`（普通）/ `1`（重要）/ `2`（紧急）                |
| `deviceId`      | string  | 否   | 设备 ID（MAC 地址），为空则为个人待办                        |

**示例**

```bash
curl --request POST \
  --url https://cloud.zectrix.com/open/v1/todos \
  --header 'X-API-Key: <API_KEY>' \
  --header 'Content-Type: application/json' \
  --data '{
    "title": "买牛奶",
    "description": "111111",
    "dueDate": "2026-04-11",
    "dueTime": "20:00",
    "repeatType": "none",
    "priority": 1,
    "deviceId": "9C:13:9E:B5:7C:00"
  }'
```

**响应**

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "id": 5254,
    "title": "买牛奶",
    "description": "111111",
    "dueDate": "2026-04-11",
    "dueTime": "20:00",
    "repeatType": "none",
    "repeatWeekday": null,
    "repeatMonth": null,
    "repeatDay": null,
    "status": 0,
    "priority": 1,
    "completed": false,
    "deviceId": "9C:13:9E:B5:7C:00",
    "deviceName": "zectrix-s3-epaper-4.2",
    "createDate": "2026-04-11 19:13",
    "updateDate": 1775906032
  }
}
```

---

### 标记完成/取消完成

切换指定待办事项的完成状态。

**请求**

```
PUT /todos/{id}/complete
```

**路径参数**

| 参数名 | 类型    | 必填 | 说明    |
|--------|---------|------|---------|
| `id`   | integer | 是   | 待办 ID |

**示例**

```bash
curl --request PUT \
  --url https://cloud.zectrix.com/open/v1/todos/5192/complete \
  --header 'X-API-Key: <API_KEY>'
```

**响应**

```json
{
  "code": 0,
  "msg": "success"
}
```
