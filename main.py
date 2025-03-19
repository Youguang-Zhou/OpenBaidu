import asyncio
import os

from dotenv import load_dotenv
from loguru import logger

from app.OpenBaidu import OpenBaidu
from config.config import load_logger

load_dotenv()
load_logger()


async def main():
    # 检查环境变量设置
    if os.getenv("DEEPSEEK_API_KEY") is None or os.getenv("DEEPSEEK_BASE_URL") is None:
        logger.error(".env 文件配置错误！")
    # 初始化
    open_baidu = OpenBaidu()
    # 运行
    while True:
        await open_baidu.run(query=input("请输入搜索的关键词："))


if __name__ == "__main__":
    asyncio.run(main())
