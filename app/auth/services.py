from app.models import User


# Service function to authenticate a user based on username and password
def authenticate(username, password):

    user = User.query.filter_by(username=username).first()

    if not user:
        return None

    if not user.check_password(password):
        return None

    return user
