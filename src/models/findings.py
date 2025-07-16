"""Pydantic models for medical findings."""

from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl  # type: ignore


class MedicalSubjectHeading(BaseModel):
    """Model representing a medical subject heading reference."""

    url: Optional[HttpUrl] = Field(
        None, description="URL reference for the medical subject heading"
    )
    name: Optional[str] = Field(None, description="Name of the medical subject heading")


class Disease(BaseModel):
    """Model representing a disease reference."""

    name: Optional[str] = Field(None, description="Name of the disease")
    uuid: Optional[UUID] = Field(None, description="Unique identifier for the disease")


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
    med_subj_heading: Optional[List[MedicalSubjectHeading]] = Field(
        None, description="List of medical subject headings"
    )
    diseases: Optional[List[Disease]] = Field(
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
                "med_subj_heading": [
                    {
                        "url": "https://example.com/mesh/D008175",
                        "name": "Lung Neoplasms",
                    },
                    {"url": "https://example.com/mesh/D011014", "name": "Pneumonia"},
                ],
                "diseases": [
                    {
                        "name": "Lung cancer",
                        "uuid": "456e7890-e89b-12d3-a456-426614174001",
                    },
                    {
                        "name": "Pulmonary infection",
                        "uuid": "789e0123-e89b-12d3-a456-426614174002",
                    },
                ],
            }
        },
    }
