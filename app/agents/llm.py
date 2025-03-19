import json
import os

from openai import OpenAI, Stream, pydantic_function_tool
from openai.types.chat import ChatCompletionSystemMessageParam as SystemMessage
from openai.types.chat import ChatCompletionUserMessageParam as UserMessage
from pydantic import BaseModel

from app.agents.browser import SearchResult
from app.tools.RemoveAds import RemoveAds

SYSTEM_PROMPT_FOR_R1 = """
你是一个搜索引擎助手，用户会给你搜索关键词 query 以及搜索结果 results 。
对于 results 中的每一项（用 index 索引），你需要分析这项结果是否与用户查询的关键词相关。
你需要尽可能的找出官方内容或对用户搜索有帮助的内容，排查错误的广告内容或有风险的第三方内容。
因为你没有联网，分析时可以忽略与日期相关的线索。
"""

USER_PROMPT_FOR_R1 = """
搜索关键词 query 为：{query}
搜索结果 results 为：{results}
"""

SYSTEM_PROMPT_FOR_V3 = """
你是一个搜索引擎助手，用户会给你搜索关键词 query ，搜索结果 results ，以及对搜索结果的分析 analyze_result 。
对于 results 中的每一项（用 index 索引）， analyze_result 详细地分析了其是否为错误的广告内容或有风险的第三方内容。
你需要 **完全** 根据 analyze_result 的内容，帮助用户删除所有错误的广告内容以及有风险的第三方内容，尽可能的保留官方内容或对用户搜索有帮助的内容。
"""

USER_PROMPT_FOR_V3 = """
搜索关键词 query 为：{query}
搜索结果 results 为：{results}
分析报告 analyze_result 为：{analyze_result}
"""


class AnalyzeResult(BaseModel):
    reasoning_content: str
    final_content: str


class LLMAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL"),
        )

    def analyze_search_result(self, search_result: SearchResult) -> Stream:
        """调用推理模型分析 search_result 是否为广告，并返回 stream 。

        Args:
            search_result: SearchResult类。

        Returns:
            stream: 模型的输出。
        """
        messages = [
            SystemMessage(role="system", content=SYSTEM_PROMPT_FOR_R1),
            UserMessage(
                role="user",
                content=USER_PROMPT_FOR_R1.format(
                    query=search_result.query,
                    results=search_result.results,
                ),
            ),
        ]
        stream = self.client.chat.completions.create(
            model="deepseek-reasoner",
            messages=messages,
            stream=True,
        )
        return stream

    def apply_function_call(
        self,
        search_result: SearchResult,
        analyze_result: AnalyzeResult,
    ) -> list[int]:
        """调用Agent模型并返回 indices 。

        Args:
            search_result: SearchResult类。
            analyze_result: AnalyzeResult类。

        Returns:
            indices_to_remove: 标记为广告的索引
        """
        messages = [
            SystemMessage(role="system", content=SYSTEM_PROMPT_FOR_V3),
            UserMessage(
                role="user",
                content=USER_PROMPT_FOR_V3.format(
                    query=search_result.query,
                    results=search_result.results,
                    analyze_result=f"{analyze_result.reasoning_content}\n{analyze_result.final_content}",
                ),
            ),
        ]
        completion = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=[pydantic_function_tool(RemoveAds)],
            tool_choice="required",
        )
        args = completion.choices[0].message.tool_calls[0].function.arguments
        indices_to_remove = json.loads(args)["indices"]
        return indices_to_remove
