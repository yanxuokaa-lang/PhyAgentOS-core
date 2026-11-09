# 周末选店（Jev + 高德）

本地 Web 小工具：用表单选城市和地标，高德搜附近餐厅，**TypeSafe Jev** 只按「味道」给每家店打分并排序，页面展示推荐结果和完整 JSON。

也可使用命令行：[`weekend_dinner.py`](weekend_dinner.py)。

## 网站功能

打开首页后可以：

1. **填写搜索条件**
   - 城市（如「上海」）
   - 菜系 / 关键词（如「日料」「火锅」）
   - 地标或地址（如「徐家汇」），后端会地理编码再周边搜餐饮 POI
   - **附加需求**（可选多行）：如人均上限、带娃、安静等，原文写入 Jev 的 `user_extra_requirements`
   - 高级选项：直接填 `lng,lat` 中心点；候选店数量 1–8

2. **一键推荐**
   - 后端调用高德 Web 服务（评分、特色菜、人均、品类等）
   - 一次 Jev 请求为每家候选店打 **综合 Score**（0–3；味道 + 附加需求，见配置）
   - 代码按该分数排序，同分再用高德评分作 tie-break

> 附加需求不会改高德搜店关键词；排队、环境等若高德未返回，Jev 只能结合品类、人均等做合理推断。

3. **查看结果**
   - **推荐卡片**：第一名店名、地址、特色菜、人均、高德评分、Jev 味道分与说明
   - **排序表格**：全部候选店及 confidence
   - **Jev 完整 JSON**：`pick`、`ranked`、`model`、`usage`，便于对照调试

4. **健康检查**
   - 页面加载时会请求 `/api/health`，提示 `.env` 里 TypeSafe / 高德 Key 是否已配置（不暴露 Key 内容）

> 说明：高德 Web 服务**不提供用户长评文本**，Jev 主要依据品类、特色菜标签和高德综合评分做判断。

## 环境准备

- Python 3.10+
- 在项目根目录配置 [`.env`](.env)（可参考 [`.env.example`](.env.example)）：
  - `TYPESAFE_API_KEY` — [TypeSafe 控制台](https://console.typesafe.ai/settings/keys)
  - `AMAP_KEY` — [高德开放平台](https://console.amap.com/dev/key/app) **Web 服务** 类型 Key（需开通搜索与地理编码）

```powershell
pip install -r requirements.txt
```

## 启动 Web（端口 5656）

```powershell
cd d:\python-project
python -m uvicorn web_app:app --host 127.0.0.1 --port 5656
```

浏览器访问：**http://127.0.0.1:5656**

开发时可加热重载：

```powershell
python -m uvicorn web_app:app --host 127.0.0.1 --port 5656 --reload
```

停止服务：在运行窗口按 `Ctrl+C`。

## 命令行选店（可选）

```powershell
python weekend_dinner.py --city 上海 --keyword 日料 --near 徐家汇
```

## Jev 问题配置（提示词）

[`config/jev_questions.json`](config/jev_questions.json) 存放打分的 **instructions**、等级 **criteria**、`ranking_rule` / `ranking_rule_with_extra` 与推荐文案模板，由 [`jev_config.py`](jev_config.py) 加载。

占位符：`{restaurant_name}`、`{restaurant_id}`（每家店自动生成问题）。用户附加需求通过 API 字段 `extra_requirements` 进入 `state.user_extra_requirements`。修改配置后需重启 Web 服务。

## 项目结构

| 路径 | 说明 |
| --- | --- |
| `config/jev_questions.json` | Jev 问题配置 |
| `jev_config.py` | 读取配置 |
| `web_app.py` | FastAPI：`/`、`/api/recommend`、`/api/health` |
| `static/` | 前端页面与样式 |
| `weekend_dinner.py` | 搜店 + Jev 打分（Web / CLI 共用） |
| `amap_client.py` | 高德地理编码与 POI 搜索 |

## API 简要

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 选店页面 |
| GET | `/api/health` | Key 是否就绪 |
| POST | `/api/recommend` | JSON body：`city`, `keyword`, `near`, 可选 `location`, `limit`, `extra_requirements`（最多 500 字） |

## 费用与配额

- **Jev**：按输入 token 计费，输出免费；个人试用量通常很小。
- **高德**：个人认证开发者有免费月配额（搜索约 5000 次/月量级），详见高德计费说明；超限需自行购买，一般不会静默扣费。
