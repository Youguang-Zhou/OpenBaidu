import re

from browser_use import Browser
from pydantic import BaseModel


class Result(BaseModel):
    index: int
    source: str
    description: str


class SearchResult(BaseModel):
    query: str
    results: list[Result]


class BrowserAgent:

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def search(self, query: str) -> SearchResult:
        """根据 query 执行搜索功能，并返回 search_result 。

        Args:
            query: 用户查询的搜索关键词。

        Returns:
            search_result: SearchResult类。
        """
        # 初始化
        if self.browser is None or self.context is None or self.page is None:
            self.browser = Browser()
            self.context = await self.browser.new_context()
            self.page = await self.context.get_current_page()
            await self.page.goto("https://www.baidu.com")

        # 输入框：<input id="kw" ...>
        await self.page.fill("#kw", query)
        # “百度一下”按钮：<input id="su" ...>
        await self.page.click("#su")

        # 获取当前页面
        await self.page.reload()

        # 删除左边栏的广告，但是一旦运行了百度会额外补充4个广告
        content_left = await self.page.wait_for_selector("#content_left")
        await content_left.eval_on_selector_all(
            ":scope > :not(.result):not(.result-op)",
            "nodes => nodes.forEach(n => n.remove())",
        )

        # 等待百度补充广告
        await self.page.wait_for_selector(
            "(//a[text()='广告'] | //span[text()='广告'])",
            timeout=5000,
        )

        # 删除右边栏里的所有内容，之后模型的推理过程会在右边栏里渲染
        content_right = await self.page.wait_for_selector("#content_right")
        await content_right.evaluate("node => node.children[0].remove()")

        # 获取所有搜索结果里的 innerText 并做简单的处理
        inner_texts: list[str] = await content_left.eval_on_selector_all(
            ":scope > div",
            "nodes => nodes.map(n => n.innerText)",
        )
        inner_texts = [text.replace("\ue62b", " ") for text in inner_texts]

        # 构造 search_result
        search_result = SearchResult(
            query=query,
            results=[
                {
                    "index": i,
                    "source": re.sub(r"广告$", "", text.split("\n")[-1]).strip(),
                    "description": text.replace("\n", " ").strip(),
                }
                for i, text in enumerate(inner_texts)
            ],
        )

        return search_result

    async def render(self, content: str):
        """把模型的输出显示在浏览器的右边栏位置。

        Args:
            content: 需要渲染的内容。
        """
        if "\n" in content:
            # 需要在HTML里换行
            for char in content.split("\n"):
                if char == "":
                    await self.page.eval_on_selector(
                        "#content_right",
                        'node => node.append(document.createElement("br"))',
                    )
                else:
                    await self.page.eval_on_selector(
                        "#content_right",
                        f'node => node.append("{char}")',
                    )
        else:
            # 正常输出
            await self.page.eval_on_selector(
                "#content_right",
                f'node => node.append("{content}")',
            )

    async def remove(self, index: int):
        """将索引为 index 的 div 替换为空内容。

        Args:
            index: 标记为广告的索引。
        """
        await self.page.eval_on_selector_all(
            "#content_left > div",
            f'nodes => nodes[{index}].replaceWith(document.createElement("div"))',
        )
