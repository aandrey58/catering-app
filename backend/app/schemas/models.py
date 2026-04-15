from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class SelectionPayload(BaseModel):
    breakfast: str = ""
    soup: str = ""
    hot: str = ""
    side: str = ""
    salad: str = ""
    dessert: str = ""


class SaveSelectionsRequest(BaseModel):
    day: str
    selections: SelectionPayload = Field(default_factory=SelectionPayload)


class DeleteSelectionsRequest(BaseModel):
    day: str


class GetSelectionsRequest(BaseModel):
    day: str


class SaveFeedbackRequest(BaseModel):
    rating: int
    feedback_text: str
