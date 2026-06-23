from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


# User model for authentication and user management
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(db.String(100), unique=True, nullable=False)

    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)

    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)

    role: Mapped[str] = mapped_column(db.String(50), default='viewer')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
