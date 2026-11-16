from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class LoanLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    equipment_id: UUID
    quantity: int = Field(ge=1, le=1000000)


class LoanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    due_at: AwareDatetime
    items: list[LoanLine] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def distinct_items(self):
        if len({x.equipment_id for x in self.items}) != len(self.items):
            raise ValueError("Mỗi thiết bị chỉ được xuất hiện một lần")
        return self


class TransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reason: str | None = Field(default=None, min_length=1, max_length=1000)
    due_at: AwareDatetime | None = None
