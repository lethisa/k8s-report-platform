from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import current_user, login_user, logout_user

from app.auth.forms import LoginForm
from app.auth.services import authenticate

# Initialize the authentication blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# Route for user login
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = authenticate(form.username.data, form.password.data)

        if user:
            login_user(user, remember=form.remember.data)

            return redirect(url_for('dashboard.index'))

        flash('Invalid username or password', 'danger')

    return render_template('auth/login.html', form=form)


# Route for user logout
@auth_bp.route('/logout')
def logout():

    logout_user()

    session.pop('_flashes', None)

    return redirect(url_for('auth.login'))
