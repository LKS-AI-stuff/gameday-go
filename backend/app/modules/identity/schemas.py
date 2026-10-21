import uuid

from pydantic import BaseModel

from app.db.models import User


class Me(BaseModel):
    id: uuid.UUID
    email: str
    age_confirmed: bool
    timezone: str | None

    @classmethod
    def from_user(cls, user: User) -> "Me":
        return cls(
            id=user.id,
            email=user.email,
            age_confirmed=user.age_confirmed_at is not None,
            timezone=user.timezone,
        )
