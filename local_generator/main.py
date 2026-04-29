import time
import os
from db_updater import get_pending_chapters, update_chapter_status

def generate_chapter(chapter_data):
    """
    调用本地大模型，基于大纲生成章节正文，并提取元数据
    这里是桩函数 (Stub)，需根据具体的 LLM API 进行对接
    """
    print(f"正在生成第 {chapter_data['chapter_no']} 章...")
    print(f"  > 目标: {chapter_data['chapter_target']}")
    print(f"  > 阶段目标: {chapter_data['stage_goal']}")
    
    # 模拟生成过程
    time.sleep(1)
    
    # 模拟生成的正文及提取的结构化信息
    mock_summary = f"主角完成了【{chapter_data['chapter_target']}】，剧情顺利推进。"
    mock_next_hook = "新的人物登场，留下悬念。"
    mock_assets_change = "无"
    
    # 更新数据库
    update_chapter_status(
        chapter_no=chapter_data['chapter_no'],
        summary=mock_summary,
        next_hook=mock_next_hook,
        assets_change=mock_assets_change
    )
    print(f"第 {chapter_data['chapter_no']} 章生成完毕，数据库已更新。\n")

def run_generator():
    """本地生成器的主循环"""
    print("=== 本地大纲生成器启动 ===")
    pending_chapters = get_pending_chapters()
    
    if not pending_chapters:
        print("目前没有待生成的章节 (status='pending')。")
        return
        
    print(f"找到 {len(pending_chapters)} 个待生成章节。")
    for chapter in pending_chapters:
        generate_chapter(chapter)
        
    print("=== 所有任务执行完毕 ===")

if __name__ == "__main__":
    run_generator()
