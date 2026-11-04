from typing import Literal

from pydantic import BaseModel,ConfigDict,Field


class LLMProbeResult(BaseModel):
    model_config=ConfigDict(extra="forbid")
    status:Literal["READY"]
    message:str=Field(min_length=1,max_length=120)
