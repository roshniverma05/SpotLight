from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.password import hash_password, verify_password
from src.auth.schemas import UserLogin, UserRegister
from src.models.user import User


def register_user(
    db: Session,
    user_data: UserRegister,
) -> User:
    """Create a new application user."""

    existing_user = db.scalar(
        select(User).where(
            User.email == user_data.email
        )
    )

    if existing_user:
        raise ValueError("Email already registered")

    user = User(
        email=user_data.email,
        password_hash=hash_password(
            user_data.password
        ),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    user_data: UserLogin,
) -> User | None:
    """Authenticate a user using email and password."""

    user = db.scalar(
        select(User).where(
            User.email == user_data.email
        )
    )

    if not user:
        return None

    if not verify_password(
        user_data.password,
        user.password_hash,
    ):
        return None

    if not user.is_active:
        return None

    return user