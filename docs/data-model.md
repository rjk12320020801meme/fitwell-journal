# FitWell Journal — 数据模型 v0.1

全部记录共性字段：`id`（uuid4 字符串，服务端生成）、`date`（`YYYY-MM-DD`）、`created_at`（ISO 8601，服务端生成）。
存储：单个 JSON 文件（默认 `backend/data/journal.json`，可用环境变量 `FITWELL_DATA` 覆盖），顶层按类型分组。

## 1. 实体与字段

### 1.1 MealEntry 一餐（type: `meal`）

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| date | str | ✅ | YYYY-MM-DD | 用餐日 |
| time | str | ✅ | HH:MM | 用餐时刻 |
| meal_type | str | ✅ | breakfast/lunch/dinner/snack | 餐次 |
| description | str | | | 吃了什么（可空，轻度使用） |
| portion | str | | | 分量描述 |
| notes | str | | | 备注 |

### 1.2 SleepEntry 睡眠（type: `sleep`）

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| date | str | ✅ | YYYY-MM-DD | **上床那天**的日期 |
| bed_time | str | ✅ | HH:MM | 上床时刻 |
| wake_time | str | ✅ | HH:MM | 起床时刻；早于 bed_time 视为跨午夜（+1 天） |
| quality | int | | 1–5 | 主观质量 |
| awakenings | int | | ≥0 | 夜间醒来次数 |
| nap_min | int | | ≥0 | 午睡分钟数 |

### 1.3 ~~SubjectiveEntry 主观状态~~（v0.1.1 移除）

心情/压力/精力/饥饿/渴望等主观打分已整体移除：它们主观、不可控，违背"只记录简单可控的数据"的产品宗旨。`subjective` 不再是合法记录类型（POST 返回 404）。

### 1.4 BodyEntry 身体指标（type: `body`）

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| date | str | ✅ | YYYY-MM-DD | |
| weight_kg | float | | >0 | 体重 |
| waist_cm | float | | >0 | 腰围 |
| body_fat_pct | float | | 0–70 | 体脂率 |
| resting_hr | float | | 20–200 | 静息心率 |
| hrv_ms | float | | >0 | HRV（如可穿戴提供） |

### 1.5 TrainingEntry 训练（type: `training`）

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| date | str | ✅ | YYYY-MM-DD | |
| time | str | ✅ | HH:MM | 开始时刻 |
| type | str | ✅ | 自由文本 | 力量/有氧/球类… |
| duration_min | int | ✅ | ≥1 | 时长 |
| rpe | int | | 1–10 | 主观强度 |

### 1.6 LabEntry 体检血值（type: `lab`，低频层）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| date | str | ✅ | 采血日 |
| fasting_glucose | float | | 空腹血糖 mmol/L |
| fasting_insulin | float | | 空腹胰岛素 μU/mL |
| hba1c | float | | 糖化血红蛋白 % |
| total_chol / ldl / hdl / triglycerides | float | | 血脂 mmol/L |

> lab 只做长期趋势对比展示，不做任何临床解释——这是措辞红线的一部分。

## 2. 存储格式

顶层键与记录类型同名（单数）：

```json
{
  "version": 1,
  "meal":      [ { "id": "…", "date": "2026-11-14", "time": "08:30", "meal_type": "breakfast", "...": "…" } ],
  "sleep":     [ … ],
  "body":      [ … ],
  "training":  [ … ],
  "lab":       [ … ]
}
```

节奏目标单独存 `settings.json`：`{"window_start":"10:00","window_end":"19:00","bed_target":"23:00","wake_target":"07:00"}`。

## 3. HTTP API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/records/{meal\|sleep\|body\|training\|lab}` | 新建记录，201 返回含 id 的记录 |
| GET | `/api/records?from=&to=` | 查询，返回 `{"meal":[],"sleep":[],"body":[],"training":[],"lab":[]}` |
| DELETE | `/api/records/{type}/{id}` | 删除，204 |
| GET | `/api/report/weekly?end_date=` | 周报（档位/cards/series），end_date 默认今天 |
| GET | `/api/settings` | 节奏目标（进食窗口/就寝/起床） |
| PUT | `/api/settings` | 更新节奏目标（字段均为可选 HH:MM） |
| GET | `/api/rhythm/today?now=HH:MM` | 今日节奏提示（now 可选，测试用）→ `{now, phase, title, message, next_time, next_label}` |
| GET | `/api/recipes?goal=&slot=&q=` | 食谱摘要列表 |
| GET | `/api/recipes/{id}` | 完整食谱（含 ingredients/steps） |
| GET | `/api/health` | 健康检查 |

周报响应结构见 [insights-rules.md](insights-rules.md#6-周报响应结构)。

## 4. 数据派生量（不落库，实时计算）

- `eating_window_h`：当日最早餐 → 最晚餐的小时跨度
- `last_meal_to_bed_min`：当日最后一餐 → 上床时刻的分钟数（负值表示餐在上床之后，即夜宵）
- `sleep_duration_h`：上床 → 起床（跨午夜 +24h）
- `bed_offset_min`：就寝时刻相对 20:00 的分钟偏移（用于圆形统计与作图）
- 社交时差：工作日与周末就寝/起床均值之差
