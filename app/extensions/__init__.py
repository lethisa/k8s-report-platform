from app.extensions.db import db
from app.extensions.login import login_manager
from app.extensions.migrate import migrate

__all__ = ['db', 'login_manager', 'migrate']
