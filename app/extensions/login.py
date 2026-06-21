from flask_login import LoginManager

from app.models.user import User

# Initialize login manager
login_manager = LoginManager()

# Configure login manager
login_manager.login_view = 'auth.login'  # pyright: ignore
login_manager.login_message = 'Please login first'


# User loader callback for login manager
@login_manager.user_loader
def load_user(user_id):

    return User.query.get(int(user_id))
