# API 文档

本文档按当前代码实现整理，优先反映程序真实调用方式，而不是单纯复述上游平台的公开说明。

## 1. 配置与运行约定

项目通过 .env 注入配置，`Config` 会在启动时读取并校验这些变量：

| 变量名          | 必填 | 默认值                            | 说明                       |
|-----------------|------|-----------------------------------|----------------------------|
| API_BASE        | 否   | https://cloud.zectrix.com/open/v1 | Zectrix API 基础地址       |
| API_KEY         | 是   | 无                                | Zectrix API Key            |
| DEVICE_ID       | 是   | 无                                | Zectrix 设备 ID            |
| DIDA_TOKEN      | 是   | 无                                | DIDA365 Bearer Token       |
| SYNC_INTERVAL   | 否   | 300                               | 定时同步间隔，单位是秒     |
| SYNC_DIRECTION  | 否   | bidirectional                     | 当前读取但尚未影响同步分支 |
| DIDA_PROJECT_ID | 否   | inbox                             | DIDA365 同步目标项目       |
| SYNC_COMPLETED  | 否   | false                             | 是否同步已完成任务         |

程序启动流程：

1. 加载 .env。
2. 创建 DidaAPI 和 ZectrixAPI 客户端。
3. 执行一次双向同步。
4. 如果 SYNC_INTERVAL 大于 0，则启动后台调度器持续同步。

## 2. DIDA365 API

### 2.1 基础信息

- 基础地址: https://api.dida365.com/open/v1
- 认证方式: Bearer Token
- 请求头:

```http
Authorization: Bearer <DIDA_TOKEN>
Content-Type: application/json
```

### 2.2 获取项目列表

- 方法: GET
- 路径: /project
- 用途: 获取当前账号下可访问的项目列表。

返回值是一个项目数组，常用字段如下：

| 字段       | 说明                            |
|------------|---------------------------------|
| id         | 项目 ID                         |
| name       | 项目名称                        |
| kind       | 项目类型，常见值为 TASK 或 NOTE |
| viewMode   | list 或 kanban                  |
| permission | 共享项目权限                    |
| sortOrder  | 排序权重                        |

### 2.3 获取项目任务

- 方法: GET
- 路径: /project/{projectId}/data
- 用途: 拉取指定项目下的任务和列信息。

返回对象包含：

- project: 项目信息。
- tasks: 任务列表。
- columns: 看板列列表。

任务字段中，当前代码实际会用到：

| 字段         | 说明                 |
|--------------|----------------------|
| id           | 任务 ID              |
| projectId    | 所属项目             |
| title        | 标题                 |
| content      | 正文                 |
| dueDate      | 截止时间             |
| startDate    | 开始时间             |
| priority     | 优先级，0/1/3/5      |
| status       | 状态，0=待办，2=完成 |
| modifiedTime | 最后修改时间         |
| isAllDay     | 是否全天             |

### 2.4 创建任务

- 方法: POST
- 路径: /task
- 用途: 在 DIDA365 中创建任务。

请求体常用字段：

| 字段      | 必填 | 说明                |
|-----------|------|---------------------|
| title     | 是   | 任务标题            |
| projectId | 否   | 项目 ID，默认收集箱 |
| content   | 否   | 任务内容            |
| startDate | 否   | 开始时间，ISO 8601  |
| dueDate   | 否   | 截止时间，ISO 8601  |
| priority  | 否   | 0/1/3/5             |
| status    | 否   | 0=待办，2=完成      |

代码会把 Zectrix 待办转换成 DIDA 任务后调用这个接口。

### 2.5 更新任务

- 方法: POST
- 路径: /task/{taskId}
- 用途: 更新已有任务。

注意：当前代码使用的是 POST，不是 PUT。

更新时通常会补齐这些字段：

- id
- projectId
- title

### 2.6 标记完成

- 方法: POST
- 路径: /project/{projectId}/task/{taskId}/complete
- 用途: 将指定任务标记为已完成。

如果该任务已存在于 DIDA365 中但 Zectrix 已完成，SyncManager 会调用这个接口同步完成状态。

## 3. Zectrix API

### 3.1 基础信息

- 基础地址: 由 API_BASE 指定，默认 https://cloud.zectrix.com/open/v1
- 认证方式: API Key
- 请求头:

```http
X-API-Key: <API_KEY>
Content-Type: application/json
```

### 3.2 获取待办列表

- 方法: GET
- 路径: /todos
- 查询参数:

| 参数     | 必填 | 说明               |
|----------|------|--------------------|
| deviceId | 是   | 设备 ID            |
| status   | 否   | 0=未完成，1=已完成 |

当前代码的实际行为：

- 如果显式传入 status，就只获取对应状态。
- 如果不传 status，就分别获取 status=0 和 status=1，然后合并去重。

返回结构为：

```json
{
  "code": 0,
  "msg": "success",
  "data": []
}
```

常用字段如下：

| 字段        | 说明                   |
|-------------|------------------------|
| id          | 待办 ID                |
| title       | 标题                   |
| description | 描述                   |
| dueDate     | 截止日期，yyyy-MM-dd   |
| dueTime     | 截止时间，HH:mm        |
| priority    | 0=普通，1=重要，2=紧急 |
| completed   | 是否完成               |
| updateDate  | Unix 时间戳            |
| deviceId    | 设备 ID                |

### 3.3 创建待办

- 方法: POST
- 路径: /todos
- 用途: 在设备上创建待办事项。

请求体常用字段：

| 字段          | 必填 | 说明                             |
|---------------|------|----------------------------------|
| title         | 是   | 标题                             |
| description   | 否   | 描述                             |
| dueDate       | 否   | yyyy-MM-dd                       |
| dueTime       | 否   | HH:mm                            |
| repeatType    | 否   | none/daily/weekly/monthly/yearly |
| repeatWeekday | 否   | 周几，weekly 使用                |
| repeatMonth   | 否   | 月份，yearly 使用                |
| repeatDay     | 否   | 日，monthly/yearly 使用          |
| priority      | 否   | 0/1/2                            |
| deviceId      | 否   | 设备 ID，空则为个人待办          |

如果请求体没有 deviceId，代码会自动补上当前设备 ID。

### 3.4 更新待办

- 方法: PUT
- 路径: /todos/{todoId}
- 用途: 更新已有待办。

当前代码会保持以下字段可空：

- dueDate
- dueTime

这两个字段如果为 None，会原样写成 null。

### 3.5 完成/取消完成

- 方法: PUT
- 路径: /todos/{todoId}/complete
- 用途: 切换待办的完成状态。

当前同步逻辑里，这个接口既用于把未完成标记为完成，也用于维持与 DIDA365 的完成状态一致。

## 4. 数据映射规则

### 4.1 DIDA365 -> Zectrix

| DIDA365 字段 | Zectrix 字段       | 说明                             |
|--------------|--------------------|----------------------------------|
| title        | title              | 直接映射                         |
| content      | description        | 直接映射，并在末尾追加 DIDA 标记 |
| dueDate      | dueDate / dueTime  | 转换为本地日期和时间             |
| priority     | priority           | 0/1/3/5 映射到 0/0/1/2           |
| status       | status / completed | 2 映射为完成                     |
| id           | description        | 写入 [DIDA365:task_id]           |

描述写回规则：

```text
原始描述 + [DIDA365:任务ID]
```

如果原始描述为空，则只写入标记。

### 4.2 Zectrix -> DIDA365

| Zectrix 字段         | DIDA365 字段        | 说明                    |
|----------------------|---------------------|-------------------------|
| title                | title               | 直接映射                |
| description          | content             | 移除 DIDA 标记后写回    |
| dueDate / dueTime    | startDate / dueDate | 组合后转为 UTC ISO 8601 |
| priority             | priority            | 0/1/2 映射到 0/3/5      |
| completed            | status              | true 映射为 2           |
| description 中的标记 | id                  | 用于匹配已有 DIDA 任务  |

### 4.3 时间处理

代码中的时间处理有几个关键点：

- DIDA365 的时间字符串会兼容 Z 和 +0000 格式。
- DIDA365 到 Zectrix 时会按 Asia/Shanghai 转换成 yyyy-MM-dd 和 HH:mm。
- Zectrix 到 DIDA365 时会按 Asia/Shanghai 组装后再转 UTC。

这部分逻辑由 mapper.py 中的 _parse_dida_datetime、dida_to_zectrix 和 zectrix_to_dida 实现。

## 5. 同步行为

### 5.1 同步顺序

当前 SyncManager 的实际顺序是：

1. 读取 DIDA365 指定项目任务。
2. 读取 Zectrix 当前设备待办。
3. 先做完成态联动。
4. 再执行 DIDA365 -> Zectrix 的创建/更新。
5. 最后执行 Zectrix -> DIDA365 的创建/更新。

### 5.2 去重与关联

Zectrix 任务通过 description 中的 DIDA ID 标记与 DIDA365 任务建立一一对应关系。

同步时会先从 Zectrix description 中解析 [DIDA365:xxx]，再建立映射表，避免重复创建。

### 5.3 完成状态处理

- DIDA365 status=2 时，Zectrix completed 会被同步为 true。
- Zectrix completed=true 时，DIDA365 会调用 complete 接口。
- 如果 Zectrix 中存在 DIDA 标记，但 DIDA 任务已不存在，当前实现会尝试将 Zectrix 待办标记为完成。

## 6. 错误处理与重试

所有 API 方法都套用了两层装饰器：

- retry_on_error: 负责重试。
- handle_api_error: 负责分类处理 HTTP 错误。

当前策略：

| 错误类型             | 行为                                  |
|----------------------|---------------------------------------|
| 网络或其他可重试异常 | 最多重试 3 次，间隔按 1s、2s、4s 递增 |
| 4xx HTTP 错误        | 记录错误并返回 None                   |
| 5xx HTTP 错误        | 抛出异常，交给重试逻辑                |

## 7. 调试提示

- 如果配置加载失败，优先检查 DIDA_TOKEN、API_KEY、DEVICE_ID 是否存在。
- 如果 Zectrix 任务没有和 DIDA 任务对应，先确认 description 中是否带有 [DIDA365:任务ID]。
- 如果时间看起来偏移，优先检查是否按 Asia/Shanghai 处理。
- 如果只看到部分待办，确认 Zectrix 的 status=0 和 status=1 是否都已拉取。

