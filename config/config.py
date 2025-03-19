from datetime import datetime
from pathlib import Path

from loguru import logger


def get_project_root() -> Path:
    """获取当前项目根目录位置"""
    return Path(__file__).parent.parent


def load_logger():
    """初始化logger"""
    root = get_project_root()
    filename = f"{datetime.now().strftime("%Y%m%d%H%M%S")}.log"
    logger.add(root / "logs" / filename)
