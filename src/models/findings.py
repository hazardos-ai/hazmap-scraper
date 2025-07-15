"""Pydantic models for medical findings."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl # type: ignore


class Finding(BaseModel):
    """Model representing a medical finding."""

    uuid: Optional[UUID] = Field(None, description="Unique identifier for the finding")
    url: Optional[HttpUrl] = Field(None, description="URL reference for the finding")
    name: Optional[str] = Field(None, description="Name of the finding")
    description: Optional[str] = Field(None, description="Description of the finding")
    category: Optional[str] = Field(
        None, description="Category classification of the finding"
    )
    icd9_code: Optional[str] = Field(None, description="ICD-9 diagnostic code")
    icd10_code: Optional[str] = Field(None, description="ICD-10 diagnostic code")
    diseases: Optional[List[str]] = Field(
        None, description="List of associated diseases"
    )

    model_config = {
        "json_encoders": {UUID: str},
        "json_schema_extra": {
            "example": {
                "uuid": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://example.com/finding/123",
                "name": "Lung nodule",
                "description": "Small round opacity in lung tissue",
                "category": "Respiratory",
                "icd9_code": "793.1",
                "icd10_code": "R91.1",
                "diseases": ["Lung cancer", "Pulmonary infection"],
            }
        },
    }
