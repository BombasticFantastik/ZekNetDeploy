from pydantic import BaseModel, ConfigDict


class UnitCreate(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)