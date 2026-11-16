from collections.abc import Iterable
from typing import Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):

    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_id: int) -> Optional[T]:
        return self.db.get(self.model, entity_id)

    def get_all(self) -> list[T]:
        return list(self.db.scalars(select(self.model)))

    def get_many(self, ids: Iterable[int]) -> list[T]:
        ids = list(ids)
        if not ids:
            return []
        return list(self.db.scalars(select(self.model).where(self.model.id.in_(ids))))

    def add(self, entity: T) -> T:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def save(self, entity: T) -> T:
        """Persist changes made to an already tracked entity."""
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: T) -> None:
        self.db.delete(entity)
        self.db.commit()