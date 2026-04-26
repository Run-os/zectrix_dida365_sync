# Zectrix DIDA365 Sync

Zectrix 墨水屏待办事项与 DIDA365（滴答清单开放 API）之间的同步工具。

## 项目目标

这个项目的核心目标是让 DIDA365 和 Zectrix 设备上的待办事项保持尽量一致。当前实现以双向同步为主：DIDA365 任务会写入 Zectrix，Zectrix 待办也会反向写回 DIDA365。

## 主要特性

- 支持 DIDA365 和 Zectrix 之间的双向同步。
- 通过在 Zectrix 的 description 中写入 [DIDA365:任务ID] 标记来建立关联。
- 支持标题、正文、截止日期、截止时间、优先级和完成状态同步。
- 使用 sync_state.json 持久化上次同步完成时间，降低双向覆盖风险。
- 仅执行一次同步，完成后退出。
- 内置重试和 API 错误处理。
- 运行日志同时输出到控制台和 logs 目录。

## 目录结构

- main.py: 程序入口。
- config.py: 环境变量加载与配置校验。
- dida_api.py: DIDA365 API 封装。
- zectrix_api.py: Zectrix API 封装。
- mapper.py: 两端字段和时间格式映射。
- sync.py: 单次同步与双向同步逻辑。
- error_handler.py: 重试和 API 错误处理装饰器。
- logger.py: 日志配置。
- test.py: 本地验证脚本。
- doc/api.md: 接口与字段说明。

## 环境要求

- Python 3.10 或更高版本。
- 能访问 DIDA365 Open API 和 Zectrix Open API。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 环境变量

项目通过 .env 文件加载配置。当前代码实际读取的变量如下：

| 变量名          | 必填 | 默认值                            | 说明                             |
| --------------- | ---- | --------------------------------- | -------------------------------- |
| API_BASE        | 是   | https://cloud.zectrix.com/open/v1 | Zectrix API 基础地址             |
| API_KEY         | 是   | 无                                | Zectrix API Key                  |
| DEVICE_ID       | 是   | 无                                | Zectrix 设备 ID，通常是 MAC 地址 |
| DIDA_TOKEN      | 是   | 无                                | DIDA365 Bearer Token             |
| DIDA_PROJECT_ID | 是   | inbox                             | DIDA365 目标项目 ID              |
| SYNC_COMPLETED  | 否   | false                             | 是否同步已完成任务               |

示例：

```env
API_BASE=https://cloud.zectrix.com/open/v1
API_KEY=your-zectrix-api-key
DEVICE_ID=00:00:00:00:00:00

DIDA_TOKEN=your-dida-token
DIDA_PROJECT_ID=inbox

SYNC_COMPLETED=false

```

## 运行方式

直接启动主程序：

```bash
python main.py
```

程序启动后会执行一次同步，完成后退出。

## 验证脚本

可以运行 test.py 做本地检查：

```bash
python test.py
```

这个脚本会检查配置加载、字段映射，以及首次从 Zectrix 创建 DIDA 任务后是否会回写 DIDA ID 标记。

## 同步规则

### 数据关联

Zectrix 没有可直接保存外部 ID 的字段，所以项目使用 description 末尾的标记建立关联：

```text
[DIDA365:任务ID]
```

当 description 原本有内容时，标记会追加到末尾；同步回写时会先移除旧标记，再重新写入新的标记。

### 字段映射

- title 直接同步。
- DIDA365 的 content 映射到 Zectrix 的 description。
- DIDA365 的 dueDate 会转换为 Zectrix 的 dueDate 和 dueTime。
- Zectrix 的 dueDate 和 dueTime 会合并后转换回 DIDA365 的 startDate 和 dueDate。
- DIDA365 优先级 0/1/3/5 映射到 Zectrix 0/0/1/2。
- Zectrix 优先级 0/1/2 映射回 DIDA365 0/3/5。
- DIDA365 status 2 表示完成，对应 Zectrix completed=true。

### 时间处理

- DIDA365 时间字符串会兼容 Z、+0000、+08:00 这类格式。
- DIDA365 到 Zectrix 时会按 Asia/Shanghai 处理。
- Zectrix 到 DIDA365 时会把本地时间换算成 UTC 再写回。

这部分逻辑由 mapper.py 统一处理。

### 完成状态联动

同步时会先处理完成状态，再处理普通字段更新，目的是避免状态被后续更新覆盖：

- 如果 Zectrix 待办已完成，而 DIDA 任务仍未完成，会先把 DIDA 任务标记为完成。
- 如果 Zectrix 中存在 DIDA 标记，但 DIDA 任务已经不存在，当前实现会倾向于把 Zectrix 任务也标记为完成。

### 反向覆盖保护

程序每次同步完成后会把 UTC 时间戳写入 sync_state.json 的 last_sync_completion_time。

当执行 Zectrix -> DIDA365 更新时，如果某条 Zectrix 任务的 updateDate 不晚于上次同步完成时间，系统会认为这次变更可能来自上轮同步写回而非用户操作，从而跳过反向更新，避免把 DIDA365 上较新的内容覆盖掉。

## 错误处理

- 请求失败会自动重试，最多 3 次。
- 4xx 错误会记录日志并返回 None，通常表示参数或权限问题。
- 5xx 错误会继续走重试机制。
- 同步过程中如果某个项目或接口失败，日志会记录下来，尽量继续处理后续任务。

## 日志

日志会写入：

- 控制台输出。
- logs/sync_YYYYMMDD.log。

## 已知限制

- DIDA365 项目同步默认使用 DIDA_PROJECT_ID 指定的项目，不会自动选择多个项目。

## 相关文档

- [接口文档](doc/api.md)
