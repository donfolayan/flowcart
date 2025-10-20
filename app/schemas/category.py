from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

from app.schemas.media import MediaResponse


class CategoryBase(BaseModel):
    name: str = Field(..., max_length=100, description="Name of the category")
    description: str | None = Field(None, description="Description of the category")
    is_default: bool = Field(
        False, description="Indicates if the category is the default category"
    )
    category_image_id: UUID | None = Field(None, description="ID of the category image")


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID = Field(..., description="Unique identifier of the category")
    category_image: MediaResponse | None = Field(
        None, description="Category image details"
    )
    model_config = ConfigDict(from_attributes=True)


class CategoryMinimalResponse(CategoryBase):
    id: UUID = Field(..., description="Unique identifier of the category")
    model_config = ConfigDict(from_attributes=True)
