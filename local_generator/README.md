# 小说写作脚本说明

## 当前口径

- 唯一主库：项目根目录 `novel_ledger.db`
- 章节闭环输入：`temp/update_chapter_XXX.md`
- 章节正文目录：`chapter/`
- `character_db.json` 与 `assets_db.json` 仅保留为迁移来源或备份，不再作为运行时事实源

## 推荐流程

1. 生成雷达：`python local_generator/build_ai_target_context.py <章节号>`
2. 读取前情：`python local_generator/read_recent_chapters.py --chapter_no <上一章号>`
3. 读取角色：`python local_generator/read_character_db.py --names "角色A,角色B" --chapter_no <当前章节号>`
4. 读取资产：`python local_generator/read_assets_db.py --chapter_no <当前章节号>`
5. **正文落盘**：将章节定稿保存到 `chapter/` 目录。
6. **极简闭环与洗地**：使用内置 Write 工具生成 `temp/update_chapter_XXX.md`，随后执行闭环洗地脚本，统一刷新角色、资产和主库状态。

## 核心脚本

### 1. 雷达生成器 `build_ai_target_context.py`

从细纲和主数据库生成当前章的战术靶点文件。

```bash
python local_generator/build_ai_target_context.py 23
```

### 2. 前情读取 `read_recent_chapters.py`

读取上一章的时间线、资产变化、遗留悬念与正文结尾片段。

```bash
python local_generator/read_recent_chapters.py --chapter_no 22
```

### 3. 角色读取 `read_character_db.py`

从主数据库 `entities_registry` 读取角色底色和近期经历。

```bash
python local_generator/read_character_db.py --names "朱高燧,袁珙,陈奉" --chapter_no 23
```

### 4. 资产读取 `read_assets_db.py`

从主数据库 `wealth_and_assets` 读取大燕商行资产负债表。

```bash
python local_generator/read_assets_db.py --chapter_no 23
```

### 5. 去味前备份 `setup_humanize_backup.py`

在执行去 AI 味处理前备份当前原稿，防止覆盖后无法回退。

```bash
python local_generator/setup_humanize_backup.py "chapter/第022章 蛛丝马迹.md"
```

### 6. 闭环执行器 `finalize_chapter_workflow.py`

读取 `temp/update_chapter_XXX.md`，把章节摘要、钩子、角色变化、资产变化写回主数据库。

```bash
python local_generator/finalize_chapter_workflow.py 23
```

### 7. 一次性并库脚本 `migrate_to_single_db.py`

把旧库与旧 JSON 中的数据迁入根目录主库，只用于迁移或校验，不参与日常写作闭环。

```bash
python local_generator/migrate_to_single_db.py
```
