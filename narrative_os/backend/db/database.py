import sqlite3
import sys
from pathlib import Path

# 获取项目根目录 (Outline_advancement)
PROJECT_ROOT = Path(__file__).absolute().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from local_generator.single_db_utils import DB_PATH

# 大纲目录路径
OUTLINE_DIR = PROJECT_ROOT / "SPEC" / "04_分卷细纲"

# 正文目录路径
CHAPTER_DIR = PROJECT_ROOT / "chapter"

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
