from loguru import logger

from app.agents.browser import BrowserAgent
from app.agents.llm import AnalyzeResult, LLMAgent


class OpenBaidu:

    def __init__(self):
        self.browser_agent = BrowserAgent()
        self.llm_agent = LLMAgent()

    async def run(self, query: str):
        """主函数

        Args:
            query: 用户查询的搜索关键词。
        """
        # 获取搜索结果
        logger.info(f"🔍 搜索词：{query}")
        with logger.catch(level="DEBUG"):
            search_result = await self.browser_agent.search(query)
        logger.info("✅ 搜索结果：")
        for result in search_result.results:
            logger.info(f"{str(result.index)+'.':<3} {result}")

        # 把搜索结果交给推理模型分析
        stream = self.llm_agent.analyze_search_result(search_result)

        # 获取分析结果
        logger.info("⌛️ 等待推理模型分析")
        reasoning_content = None
        final_content = None
        for chunk in stream:
            chunk_r = chunk.choices[0].delta.reasoning_content
            chunk_f = chunk.choices[0].delta.content
            with logger.catch(level="DEBUG", message=f"无法渲染 {chunk} 至浏览器！"):
                # 思考过程
                if chunk_r is not None:
                    if reasoning_content is None:
                        await self.browser_agent.render(
                            f"{"="*20} 思考过程 {"="*20}\n",
                        )
                        reasoning_content = ""
                    reasoning_content += chunk_r
                    await self.browser_agent.render(chunk_r)
                # 最终回答
                if chunk_f is not None:
                    if final_content is None:
                        await self.browser_agent.render(
                            f"\n{"="*20} 最终回答 {"="*20}\n",
                        )
                        final_content = ""
                    final_content += chunk_f
                    await self.browser_agent.render(chunk_f)
        analyze_result = AnalyzeResult(
            reasoning_content=reasoning_content,
            final_content=final_content,
        )
        logger.info(f"✅ 推理结果：\n{reasoning_content}")
        logger.info(f"✅ 最终结果：\n{final_content}")

        # 执行
        logger.info("⌛️ 等待Agent模型执行function call")
        indices_to_remove = self.llm_agent.apply_function_call(
            search_result,
            analyze_result,
        )
        logger.info(f"广告内容的索引：{indices_to_remove}")

        # 删除所有广告
        for index in indices_to_remove:
            await self.browser_agent.remove(index)
            logger.info(f"已删除：{search_result.results[index]}")

        # 完成
        logger.info("✅ 大功告成！")
