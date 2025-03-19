from pydantic import BaseModel, Field


class RemoveAds(BaseModel):
    indices: list[int] = Field(
        description="对于 results 中需要删除的所有错误的广告内容以及有风险的第三方内容的 index"
    )
