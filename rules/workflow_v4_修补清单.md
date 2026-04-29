---
description: V4 工作流修补清单与执行顺序
globs: ["local_generator/*", "rules/*"]
---
# V4 工作流修补清单

## 1. 目标
- 修复“第23章可模拟但上下文被污染”的问题。
- 把运行时真正需要的动态信息收口到 `novel_ledger.db`。
- 保留 `SPEC` 与 `rules` 的文件层地位，不把冷规则和细纲原文混进运行时动态表。

## 2. 立即执行项
- 修补 `read_recent_chapters.py`
  - 停止读取上一章正文尾段。
  - 只输出数据库中的 `timeline_mark / written_summary / next_hook / key_assets_change`。
- 修补数据库 schema
  - 增加 `character_history_log`，按章记录角色动态。
  - 增加 `asset_history_log`，按章记录资产快照/变动。
- 修补 `read_character_db.py`
  - 动态经历改为从 `character_history_log` 按 `chapter_no` 截断读取。
  - 禁止直接把 `history_json` 当运行时动态事实源。
- 修补 `read_assets_db.py`
  - 优先读取 `asset_history_log` 中 `<= 当前章前一章` 的最新快照。
  - 缺失时才回退到 `wealth_and_assets` 当前值。
- 修补 `finalize_chapter_workflow.py`
  - 闭环时把 `character_updates.history` 追加写入 `character_history_log`。
  - 闭环时把 `assets_updates` 写入 `asset_history_log`。
- 修补 `build_ai_target_context.py`
  - 不再按文件名硬推单元细纲。
  - 改为按细纲正文内容识别真实覆盖范围。
  - 输出当前章的单元纲摘要、本章止步点、下一章禁止提前兑现项。

## 3. 后续扩展项
- 设计 `chapter_constraints` 或 `chapter_outline_cache`
  - 字段建议：`chapter_no / chapter_function / stop_point / do_not_advance / cognitive_boundary / involved_characters`。
- 设计“已曝光信息”入库方案
  - 优先复用 `hooks_network`，若语义不足再新建 `info_exposure_log`。
- 设计 `world_facts` 的冷数据回填机制
  - 用于称谓、物价、历史铁案等静态查证。

## 4. 执行顺序
1. 前情读取去污染。
2. 数据库补历史表。
3. 角色读取改按章切片。
4. 资产读取改按章快照。
5. 闭环脚本补动态日志写入。
6. 雷达改成“正文识别覆盖范围 + 输出章边界”。
7. 重新模拟第23章流程验证。

## 5. 验收标准
- 模拟第23章时，不再读取第22章正文尾段。
- 角色上下文里不再出现第24章结果态。
- 资产读取能接受 `chapter_no` 并返回对应时点的快照。
- 雷达能同时给出：
  - 当前章单章细纲
  - 对应单元细纲摘要
  - 本章止步点
  - 下一章禁止提前兑现项
- 闭环后数据库里能看到角色动态日志和资产历史日志。
