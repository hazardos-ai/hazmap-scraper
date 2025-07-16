"""Pydantic models for the entity registry."""

from typing import Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, HttpUrl


class EntityEntry(BaseModel):
    """Model representing a single entity in the registry."""

    uuid: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the entity"
    )
    name: str = Field(..., description="Name of the entity")
    url: HttpUrl = Field(..., description="Source URL for the entity")

    class Config:
        """Pydantic configuration."""

        json_encoders = {UUID: str}


class CategoryRegistry(BaseModel):
    """Model representing all entities in a category."""

    category_name: str = Field(..., description="Name of the category")
    category_description: str = Field(..., description="Description of the category")
    root_url: HttpUrl = Field(..., description="Base URL for the category")
    total_expected: int = Field(..., description="Expected total number of entities")
    entities: List[EntityEntry] = Field(
        default_factory=list, description="List of entities in this category"
    )

    @property
    def total_scraped(self) -> int:
        """Return the number of entities actually scraped."""
        return len(self.entities)

    class Config:
        """Pydantic configuration."""

        json_encoders = {UUID: str}


class EntityRegistry(BaseModel):
    """Model representing the complete entity registry."""

    categories: Dict[str, CategoryRegistry] = Field(
        default_factory=dict, description="Registry of all categories"
    )

    @property
    def total_entities(self) -> int:
        """Return the total number of entities across all categories."""
        return sum(len(category.entities) for category in self.categories.values())

    def get_entity_by_uuid(self, entity_uuid: UUID) -> Optional[EntityEntry]:
        """Find an entity by its UUID."""
        for category in self.categories.values():
            for entity in category.entities:
                if entity.uuid == entity_uuid:
                    return entity
        return None

    def get_entities_by_category(self, category: str) -> List[EntityEntry]:
        """Get all entities in a specific category."""
        if category in self.categories:
            return self.categories[category].entities
        return []

    def save_to_yaml(self, file_path: str) -> None:
        """Save the registry to a YAML file."""
        import yaml

        # Convert to dictionary for YAML serialization
        registry_dict = {
            "entity_registry": {
                category_key: {
                    "category_name": category.category_name,
                    "category_description": category.category_description,
                    "root_url": str(category.root_url),
                    "total_expected": category.total_expected,
                    "total_scraped": category.total_scraped,
                    "entities": [
                        {
                            "uuid": str(entity.uuid),
                            "name": entity.name,
                            "url": str(entity.url),
                            "category": entity.category,
                        }
                        for entity in category.entities
                    ],
                }
                for category_key, category in self.categories.items()
            }
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                registry_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    class Config:
        """Pydantic configuration."""

        json_encoders = {UUID: str}
