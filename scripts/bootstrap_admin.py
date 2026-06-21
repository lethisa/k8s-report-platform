import os

from app import create_app
from app.extensions.db import db
from app.models.user import User

app = create_app()

with app.app_context():

    username = os.getenv("ADMIN_USERNAME")
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    if not all([username, email, password]):
        print("Admin bootstrap skipped")
        exit(0)

    user = User.query.filter_by(
        username=username
    ).first()

    if user:
        print("Admin already exists")
        exit(0)

    admin = User(
        username=username, # type: ignore
        email=email, # type: ignore
        role="admin" # type: ignore
    )

    admin.set_password(password)

    db.session.add(admin)
    db.session.commit()

    print(
        f"Admin user created: {username}"
    )