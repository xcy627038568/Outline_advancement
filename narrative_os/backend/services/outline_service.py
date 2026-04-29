import os
from pathlib import Path
from db.database import OUTLINE_DIR

def parse_outline_structure():
    """解析大纲目录结构，返回树形数据供前端展示"""
    if not OUTLINE_DIR.exists():
        return {"error": "大纲目录不存在", "path": str(OUTLINE_DIR)}

    tree = []
    
    # 获取卷列表并按名称排序
    volumes = sorted([d for d in OUTLINE_DIR.iterdir() if d.is_dir()])
    
    for volume in volumes:
        vol_data = {
            "name": volume.name,
            "type": "volume",
            "path": str(volume.relative_to(OUTLINE_DIR)),
            "summary_file": None,
            "units": []
        }
        
        # 查找该卷的纲要文件 (如: 01_第一卷百章纲要.md)
        summary_files = list(volume.glob("*百章纲要.md"))
        if summary_files:
            vol_data["summary_file"] = summary_files[0].name
            
        # 查找细纲目录
        details_dir = volume / "百章细纲"
        if details_dir.exists() and details_dir.is_dir():
            units = sorted([f for f in details_dir.glob("*.md")])
            for unit in units:
                vol_data["units"].append({
                    "name": unit.name,
                    "type": "unit",
                    "path": str(unit.relative_to(OUTLINE_DIR))
                })
                
        tree.append(vol_data)
        
    return tree

def get_outline_content(relative_path: str):
    """读取具体的 markdown 文件内容"""
    target_path = (OUTLINE_DIR / relative_path).resolve()
    
    # 安全检查：确保路径在大纲目录下，防止目录穿越
    if not str(target_path).startswith(str(OUTLINE_DIR.resolve())):
        return {"error": "非法的路径访问"}
        
    if not target_path.exists() or not target_path.is_file():
        return {"error": "文件不存在"}
        
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}
