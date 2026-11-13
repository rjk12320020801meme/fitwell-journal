# FitWell Journal 健身健康日志

> 记录吃饭时间与睡眠时间，获得食谱推荐与做法，看懂自己的代谢规律与睡眠规律趋势。
> **本工具输出为趋势洞察，不构成医疗诊断或医疗建议。**

## 功能（v0.1.1）

- **今日节奏（小闹钟）**：按你设定的进食窗口与就寝目标，实时提示当前阶段与下一动作——"睡前收尾 🌙 距离目标就寝还有 1 小时"。温和提示，不追打卡、不制造焦虑
- **30 秒快速记录**：一餐（时间/餐次）、睡眠（起止）、体重、训练——**只记客观事实**，没有主观打分（v0.1.1 移除心情/压力/精力等主观项：它们模糊、主观、且加重填写负担）
- **周报趋势洞察**：代谢规律（进食窗口/末餐-入睡间隔/进食节奏/睡前 2h 进食）、睡眠规律（时长/就寝波动/起床波动/社交时差），呈现为**文字档位**（很稳/不错/可调整）；趋势卡片与关联卡片（睡眠↔加餐、睡前进食↔睡眠、进食窗口↔睡眠、训练↔入睡）
- **食谱推荐**：12 道健身食谱，按目标（减脂/维持/增肌）× 餐次筛选，含具体用量、做法步骤、食用时机
- **数据主权**：JSON 文件本地存储，一键导出/导入
- **PWA**：可安装到手机主屏，离线缓存应用外壳

## 快速开始

```bash
cd fitwell-journal
pip install -r backend/requirements.txt   # 仅需 fastapi + uvicorn
python -m uvicorn backend.app.server:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000> 即可使用（前端由 FastAPI 直接托管）。

数据文件默认 `backend/data/journal.json`，可用环境变量 `FITWELL_DATA` 覆盖。

## 运行测试

核心逻辑（模型/存储/规则引擎/趋势/食谱）**纯标准库**，无需任何依赖：

```bash
cd fitwell-journal
python -m unittest discover backend/tests -v
```

## 架构

```
fitwell-journal/
├── docs/
│   ├── PRD.md              # 产品需求文档（定位、分层、商业化路径）
│   ├── data-model.md       # 数据模型与 API 契约
│   └── insights-rules.md   # 洞察规则规格（评分/卡片/措辞红线）
├── backend/
│   ├── app/
│   │   ├── models.py       # 记录模型与校验（纯标准库）
│   │   ├── storage.py      # JSON 文件存储 + 节奏目标设置（纯标准库）
│   │   ├── rules.py        # 规则引擎：档位 + 关联卡片（纯标准库）
│   │   ├── trends.py       # 日聚合 + 周报组装（纯标准库）
│   │   ├── rhythm.py       # 今日节奏（小闹钟）（纯标准库）
│   │   ├── recipes.py      # 内置食谱数据与推荐（纯标准库）
│   │   └── server.py       # FastAPI 服务层（唯一的 web 依赖）
│   ├── tests/              # 单元测试（unittest，核心逻辑全覆盖）
│   └── requirements.txt
└── frontend/               # React PWA（无构建步骤）
    ├── index.html          # 应用外壳（React 18 UMD + htm，本地 vendor）
    ├── js/                 # app.js / api.js / charts.js（手写 SVG 图表）
    ├── css/styles.css      # 移动优先卡片式主题
    ├── icons/              # PWA 图标
    └── sw.js               # Service Worker（缓存外壳）
```

**设计原则**：判断逻辑全部在可测试的规则引擎里，LLM（未来版本）只负责把结论写成人话；每个评分和卡片都可展开看到"为什么"。

## 措辞红线

- 只说"数据显示…趋势""建议关注"，不出现"抵抗""诊断""患病"等诊断性语言（`rules.BANNED_WORDS` 有单元测试断言）
- 周报固定展示免责声明
- 体检血值只做长期趋势展示，不做临床解释

## 路线图

- **v0.2**：拍照识食、LLM 对话式营养教练、补剂/咖啡因时点录入、月报
- **v0.3**：可穿戴接入（Apple Health / 华为 / Garmin）、体检血值趋势、CGM 接入
- **商业化**：订阅制深度报告 → 体检报告趋势解读 → B2B 企业健康

## License

MIT
