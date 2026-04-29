# 方案B：主库全量重建与 SPEC 灌库执行方案

## 1. 目标

- 放弃现有章节进度、角色动态状态、资产快照、历史台账。
- 以 `SPEC/01_核心宪法`、`SPEC/02_写作手册`、`SPEC/03_静态词典`、`SPEC/05_实体档案` 为静态事实源，重建主库底层设定。
- 同时读取 `SPEC/04_分卷细纲`，重建 `chapters_nav`，确保旧工作流和 Web 端仍可读取章节导航。

## 2. 清理范围

### 2.1 文件层

- 删除 `chapter/*.md`
- 删除 `ledger/history/update_chapter_*.md`
- 删除 `temp/update_chapter_*.md`
- 删除 `temp/workflow_preview/*`
- 删除 `temp/reference_pack/*`

### 2.2 数据库层

- 删除项目根目录唯一主库 `novel_ledger.db`
- 删除可能残留的 `local_generator/novel_ledger.db`
- 不保留旧章节、旧摘要、旧钩子、旧资产、旧角色动态日志

## 3. 重建原则

- `SPEC` 文件只读，绝不反写。
- `SPEC/01`、`SPEC/03`、`SPEC/05` 负责静态底库。
- `SPEC/02` 主要进入规范型知识库，不直接当剧情事实。
- `SPEC/04` 负责生成 `chapters_nav` 的待写导航。
- 所有章节状态初始化为 `pending`。
- `timeline_mark` 初始留空，运行时再按统一格式闭环回写。

## 4. 数据表落位

### 4.1 保留并重建

- `chapters_nav`
- `entities_registry`
- `entity_relationships`
- `locations_and_territories`
- `wealth_and_assets`
- `hooks_network`
- `world_facts`
- `character_history_log`
- `asset_history_log`

### 4.2 新增

- `spec_chunks`

用途：
- 保存 `SPEC/01`、`SPEC/02`、`SPEC/03`、`SPEC/05` 的规范型切片
- 支持后续按来源文件、领域、标题、关键词检索冷数据

建议字段：
- `source_file`
- `section`
- `domain`
- `chunk_key`
- `content`
- `tags`

## 5. 具体灌库映射

### 5.1 `SPEC/01_核心宪法`

写入：
- `world_facts`
- `spec_chunks`

内容：
- 世界规则
- 寿命锚点
- 六卷总主线
- 精确历史节点

### 5.2 `SPEC/02_写作手册`

写入：
- `spec_chunks`

内容：
- 写作风格红线
- 叙事约束
- 对白和节奏规范

### 5.3 `SPEC/03_静态词典`

写入：
- `world_facts`
- `locations_and_territories`
- `spec_chunks`

内容：
- 人物称呼规则
- 地理点位与航线
- 物价、工资、产量、运输与金融标尺

### 5.4 `SPEC/05_实体档案`

写入：
- `entities_registry`
- `entity_relationships`
- `spec_chunks`

内容：
- 核心角色
- 文官与外围配角
- 婚配关系
- 子女谱系

### 5.5 `SPEC/04_分卷细纲`

写入：
- `chapters_nav`

生成规则：
- 以十章片段为基础，批量展开到单章。
- 若存在单章细纲，则用单章级别内容覆盖对应章节的 `chapter_target` 与 `stage_goal`。
- `status` 统一置为 `pending`。

## 6. 初始资产策略

- 不保留旧资产余额。
- 为兼容 `read_assets_db.py`，保留最小可读的空白资产骨架。
- 所有数值型资产初始化为 `0`。
- 所有文本型资产初始化为 `未建立`、`未启用` 或 `待建立`。

## 7. 执行顺序

1. 清理旧正文、旧台账、旧预览文件。
2. 删除旧主库与本地残留库。
3. 重建数据库结构。
4. 导入 `SPEC/01`、`SPEC/02`、`SPEC/03`、`SPEC/05` 的静态底库。
5. 导入 `SPEC/04`，生成完整 `chapters_nav`。
6. 校验角色、地点、世界规则、章节数量与首批章节导航。

## 8. 验收标准

- 根目录存在新的 `novel_ledger.db`
- `chapters_nav` 已生成完整待写记录
- `entities_registry` 已有核心角色与婚配谱系
- `locations_and_territories` 已有北平城内与海贸核心点位
- `world_facts` 已有世界规则、价格标尺、金融规则
- `spec_chunks` 已可作为静态规范检索层
- `read_character_db.py`、`read_assets_db.py` 能对新库正常读取
