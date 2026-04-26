# API 文档

本文档按当前代码实现整理，优先反映程序真实调用方式，而不是单纯复述上游平台的公开说明。

## 1. 配置与运行约定

项目通过 .env 注入配置，`Config` 会在启动时读取并校验这些变量：

| 变量名          | 必填 | 默认值                            | 说明                     |
|-----------------|------|-----------------------------------|--------------------------|
| API_BASE        | 是   | https://cloud.zectrix.com/open/v1 | Zectrix API 基础地址     |
| API_KEY         | 是   | 无                                | Zectrix API Key          |
| DEVICE_ID       | 是   | 无                                | Zectrix 设备 ID          |
| DIDA_TOKEN      | 是   | 无                                | DIDA365 Bearer Token     |
| DIDA_PROJECT_ID | 是   | inbox                             | DIDA365 同步目标项目     |
| SYNC_COMPLETED  | 否   | false                             | 是否同步已完成任务       |
| SYNC_INTERVAL   | 否   | 300                               | 同步间隔时间（秒）       |
| SYNC_DIRECTION  | 否   | bidirectional                     | 同步方向（暂未实际使用） |

程序启动流程：

1. 加载 config/.env。
2. 创建 DidaAPI 和 ZectrixAPI 客户端。
3. 执行一次双向同步。
4. 将上次同步完成时间写入 data/sync_state.json。
5. 完成后退出，不再启动后台定时任务。

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

### 2.7 按状态过滤任务

- 方法: POST
- 路径: /task/filter
- 用途: 按条件筛选任务。

请求体中的 status 参数：

| status 值 | 说明       |
|-----------|------------|
| 0         | 未完成任务 |
| 2         | 已完成任务 |

当前代码的实际行为：

- 调用 `get_tasks(status=0)` 获取未完成任务列表。
- 调用 `get_tasks(status=2)` 获取已完成任务列表。
- 两列表合并后用于完成态联动和常规同步。

请求示例（获取未完成任务）：

```bash
curl --request POST \
  --url https://api.dida365.com/open/v1/task/filter \
  --header 'Authorization: Bearer xxxxxxx' \
  --header 'content-type: application/json' \
  --data '{
  "status": [0]
}'
```

返回示例：

```json
[
  {
    "id": "69a85785b9061f3c217e9de6",
    "projectId": "69a850f41c20d2030e148fdf",
    "sortOrder": -2199023255552,
    "title": "task1",
    "content": "",
    "desc": "",
    "startDate": "2026-03-05T00:00:00.000+0000",
    "dueDate": "2026-03-05T00:00:00.000+0000",
    "timeZone": "America/Los_Angeles",
    "isAllDay": false,
    "priority": 0,
    "status": 0,
    "tags": [
      "tag"
    ],
    "etag": "cic6e3cg",
    "kind": "TEXT"
  },
  {
    "id": "69a8ea79b9061f4d803f6b32",
    "projectId": "69a850f41c20d2030e148fdf",
    "sortOrder": -3298534883328,
    "title": "task2",
    "content": "",
    "startDate": "2026-03-05T00:00:00.000+0000",
    "dueDate": "2026-03-05T00:00:00.000+0000",
    "timeZone": "America/Los_Angeles",
    "isAllDay": false,
    "priority": 0,
    "status": 0,
    "tags": [
      "tag"
    ],
    "etag": "0nvpcxzh",
    "kind": "TEXT"
  }
]
```

kind 字段说明：

| kind 值   | 说明                             |
|-----------|----------------------------------|
| TEXT      | 普通待办任务                     |
| NOTE      | 便签                             |
| CHECKLIST | 待办清单，清单内可包含多个子任务 |


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

### 3.6 删除待办

- 方法: DELETE
- 路径: /todos/{todoId}
- 用途: 删除指定待办事项。

当前代码中，该接口用于处理重复任务的旧周期清理：当 Zectrix 已完成且对应的 DIDA 任务为重复任务（repeatFlag 非空）时，会调用此接口删除 Zectrix 中的旧周期任务，以便 DIDA 侧生成新周期任务后重新同步。

## 4. 数据映射规则

### 4.1 DIDA365 -> Zectrix

当前由 Mapper.dida_to_zectrix 执行，输出的是 Zectrix 的待办更新/创建 payload。

| DIDA365 字段                   | Zectrix 字段      | 实际规则                                                                                                                                                                                                                              |
|--------------------------------|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| title                          | title             | 直接映射，缺省为空字符串。                                                                                                                                                                                                            |
| content                        | description       | 先取 content 文本，再在末尾拼接 DIDA 标记 [DIDA365:{id}]。                                                                                                                                                                            |
| id                             | description       | 只要存在 id，就写入标记；若 content 非空，格式为 content + 空格 + 标记；若 content 为空，则 description 仅为标记。                                                                                                                    |
| dueDate / startDate / isAllDay | dueDate / dueTime | 1) 若 dueDate 与 startDate 都为空，dueDate/dueTime 都置为 null。2) 若 dueDate 存在，先解析并转 Asia/Shanghai。3) dueDate 固定输出 yyyy-MM-dd。4) isAllDay=false 且本地时间不为 00:00 时才输出 dueTime=HH:mm，否则 dueTime 保持 null。 |
| priority(0/1/3/5)              | priority(0/1/2)   | 0->0, 1->0, 3->1, 5->2，未知值默认 0。                                                                                                                                                                                                |
| status(0/2)                    | status(0/1)       | status=2 映射为 1（完成），否则为 0（未完成）。内部同时计算 completed = (status == 1)，供同步层使用。                                                                                                                                 |

补充说明：

- 该函数返回 status 和 completed；completed 在同步层用于比较/状态切换。
- description 的 DIDA 标记是跨端关联主键来源，后续反向同步依赖该标记提取 DIDA 任务 ID。

### 4.2 Zectrix -> DIDA365

当前由 Mapper.zectrix_to_dida 执行，输出的是 DIDA 任务更新/创建 payload。

| Zectrix 字段                    | DIDA365 字段        | 实际规则                                                                                                                                                                                          |
|---------------------------------|---------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| description 中的 [DIDA365:{id}] | id                  | 先从 description 解析标记作为 DIDA 任务 ID；若无标记则 id 为 None。                                                                                                                               |
| title                           | title               | 直接映射，缺省为空字符串。                                                                                                                                                                        |
| description                     | content             | 去除 DIDA 标记后的纯文本写入 content。                                                                                                                                                            |
| dueDate / dueTime               | startDate / dueDate | 1) dueDate+dueTime 同时存在：按 Asia/Shanghai 解析，再转 UTC，startDate=dueDate。2) 仅 dueDate 存在：按本地 00:00 解析后转 UTC，startDate=dueDate。3) dueDate 为空：不写 startDate/dueDate 字段。 |
| priority(0/1/2)                 | priority(0/3/5)     | 0->0, 1->3, 2->5，未知值默认 0。                                                                                                                                                                  |
| completed(bool)                 | status(0/2)         | completed=true 映射为 2（完成），否则为 0。                                                                                                                                                       |

补充说明：

- zectrix_to_dida 结果里仅在 due_date 非空时才附带 startDate 与 dueDate。
- 反向更新时若 id 存在，会走更新；id 不存在则走新建并强制补 projectId。

### 4.3 时间处理

代码中的时间处理有几个关键点：

- DIDA365 的时间字符串会兼容 Z 和 +0000 格式。
- DIDA365 到 Zectrix 时会按 Asia/Shanghai 转换成 yyyy-MM-dd 和 HH:mm。
- Zectrix 到 DIDA365 时会按 Asia/Shanghai 组装后再转 UTC。

这部分逻辑由 mapper.py 中的 _parse_dida_datetime、dida_to_zectrix 和 zectrix_to_dida 实现。

### 4.4 指纹比较口径（用于跳过无变化同步）

当前同步层新增了统一字段指纹比较，比较字段为：title、content、dueDate、status。

比较规则：

1. 文本归一化：None 转空字符串，且去除首尾空白。
2. dueDate 归一化：统一比较 (dueDate, dueTime) 二元组。
3. DIDA 侧 dueDate 先通过 dida_to_zectrix 映射后再参与比较，避免时区与格式差异导致误判。
4. content 比较时，Zectrix 会先移除 [DIDA365:xxx] 标记再比较。
5. status 统一成 DIDA 语义（0 未完成 / 2 完成）后比较。

结论：若两端指纹一致，则即使时间戳满足“可更新”，也会直接跳过该任务更新。

## 5. 同步行为

### 5.1 同步顺序

当前 SyncManager 的实际顺序是：

1. 读取 DIDA365 未完成任务（status=0）。
2. 读取 DIDA365 已完成任务（status=2）。
3. 合并未完成和已完成任务，构建 dida_task_map 和 syncable_dida_tasks（过滤 kind）。
4. 读取 Zectrix 当前设备待办（默认拉取 status=0 和 status=1 后合并去重）。
5. 先做完成态联动（含重复任务旧周期删除）。
6. 再执行 DIDA365 -> Zectrix 的创建/更新。
7. 最后执行 Zectrix -> DIDA365 的创建/更新。

其中第 6、7 步都受"字段指纹比较 + 时间戳判定"双重约束。

### 5.2 去重与关联

Zectrix 任务通过 description 中的 DIDA ID 标记与 DIDA365 任务建立一一对应关系。

同步时会先从 Zectrix description 中解析 [DIDA365:xxx]，再建立映射表，避免重复创建。

关联构建细节：

1. zectrix_todo_map：键为 dida_id，值为 Zectrix todo（通过 description 解析得到）。
2. dida_task_map：键为 dida_task.id，值为 DIDA task。
3. 仅带有效 DIDA 标记的 Zectrix todo 会进入映射表；无标记 todo 在反向同步中默认走“可能新建 DIDA”。
4. DIDA365 的 projectId 不参与读取阶段，只在新建 DIDA 任务时写入请求体。
5. 仅同步 kind 为 TEXT 和 CHECKLIST 的 DIDA 任务；kind 为 NOTE 的任务会在双向同步中跳过。

### 5.3 完成状态处理

完成态联动发生在常规双向更新之前，遍历所有 Zectrix 待办，对带有 DIDA 标记的任务执行以下规则：

1. **DIDA 已完成，Zectrix 未完成**：调用 Zectrix complete_todo 接口，将 Zectrix 任务标记为完成。
2. **重复任务处理**：若 Zectrix 已完成，且对应 DIDA 任务有 repeatFlag（重复任务），则调用 Zectrix delete_todo 接口删除该旧周期任务，等待 DIDA 侧生成新周期后重新同步到 Zectrix。
3. **Zectrix 已完成，DIDA 未完成**：调用 DIDA complete_task 接口，将 DIDA 任务标记为完成，并更新内存中的 dida_task.status=2。
4. **DIDA 任务不存在**：若 Zectrix 带 DIDA 标记但 DIDA 任务列表中找不到对应任务（视为 DIDA 已删除/归档），调用 Zectrix complete_todo 接口将该待办标记完成。

### 5.4 DIDA365 -> Zectrix 更新判定

遍历 syncable_dida_tasks（仅 TEXT 和 CHECKLIST 类型），对每个 DIDA 任务按如下顺序判定：

1. 配置过滤：当 sync_completed=false 且 DIDA status=2，直接跳过。
2. 字段指纹比较：若 title/content/dueDate/status 四字段一致，直接跳过。
3. 时间戳比较：仅当 dida.modifiedTime > zectrix.updateDate 时，执行 update_todo。
4. 状态切换：update_todo 成功后，若 existing_completed 与 new_completed 不一致，再调用 complete_todo 切换完成态。
5. 若未关联到 Zectrix todo（dida_id 不在 zectrix_todo_map 中），则执行 create_todo。

注意：状态切换是独立 API（/todos/{todoId}/complete），不是依赖 update_todo 直接写 completed。

### 5.5 Zectrix -> DIDA365 更新判定

遍历所有 Zectrix 待办（跳过已被删除的重复任务旧周期），对每个待办按如下顺序判定：

1. 配置过滤：当 sync_completed=false 且 Zectrix completed=true，直接跳过。
2. 已删除任务跳过：若该待办的 id 在 deleted_repeating_zectrix_todo_ids 集合中，直接跳过。
3. 字段指纹比较：若 title/content/dueDate/status 四字段一致，直接跳过。
4. 非同步类型检查：若对应的 DIDA 任务 kind 不在 {TEXT, CHECKLIST} 中，直接跳过。
5. 上次同步保护：若 zectrix.updateDate <= last_sync_completion_time，跳过，避免上一轮写回触发反向覆盖。
6. 时间戳比较：仅当 zectrix.updateDate > dida.modifiedTime 时，执行 update_task；否则记录"DIDA365 较新，跳过更新"。
7. 更新前补齐必要字段：确保 id、projectId、title 存在。
8. 若 dida_id 不存在或未命中 dida_task_map，则执行 create_task，并强制写入 DIDA_PROJECT_ID。

### 5.6 新建后的关联回写

当 Zectrix -> DIDA365 发生新建并成功返回 DIDA 任务 ID 后：

1. 会将 Zectrix description 规范化为“纯描述 + [DIDA365:new_id]”。
2. 调用 update_todo 回写该 description。
3. 成功后立即更新内存中的 zectrix_todo_map，避免同轮或下轮重复创建。

### 5.7 同步状态落盘

每轮 sync 完成后会写入 data/sync_state.json：

- 字段：last_sync_completion_time（UTC Unix 时间戳）。
- 作用：为下一轮 Zectrix -> DIDA365 反向更新提供"上次同步写入屏障"。

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

## 7. 同步状态文件

程序会在项目 data 目录下维护 data/sync_state.json，核心字段如下：

```json
{
  "last_sync_completion_time": 1712999999
}
```

用途：

- 记录最近一次完整同步结束的 UTC Unix 时间戳。
- 在 Zectrix -> DIDA365 反向更新前，若 zectrix.updateDate <= last_sync_completion_time，则跳过更新，减少“上一轮同步写回触发下一轮反向覆盖”的风险。

## 8. 调试提示

- 如果配置加载失败，优先检查 DIDA_TOKEN、API_KEY、DEVICE_ID 是否存在。
- 如果 Zectrix 任务没有和 DIDA 任务对应，先确认 description 中是否带有 [DIDA365:任务ID]。
- 如果时间看起来偏移，优先检查是否按 Asia/Shanghai 处理。
- 如果只看到部分待办，确认 Zectrix 的 status=0 和 status=1 是否都已拉取。
- 如果重复任务未正确同步，检查 DIDA 任务的 repeatFlag 字段是否非空，以及旧周期 Zectrix 任务是否已被删除。
- 如果 Zectrix → DIDA 方向始终不更新，检查 data/sync_state.json 中的 last_sync_completion_time 是否过大，导致"上次同步保护"一直生效。
- 日志中"核心字段未变化，跳过"表示指纹比较通过，任务内容无实际变更。
