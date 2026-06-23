import os

import click
from flask.cli import with_appcontext

from app.extensions.db import db
from app.models.user import User


@click.command('create-admin')
@with_appcontext
def create_admin():

    username = os.getenv('ADMIN_USERNAME')
    email = os.getenv('ADMIN_EMAIL')
    password = os.getenv('ADMIN_PASSWORD')

    if not username:
        raise click.ClickException('ADMIN_USERNAME is not configured')

    if not email:
        raise click.ClickException('ADMIN_EMAIL is not configured')

    if not password:
        raise click.ClickException('ADMIN_PASSWORD is not configured')

    user = User.query.filter_by(username=username).first()

    if user:
        click.echo('Admin already exists')
        return

    user = User()

    user.username = username
    user.email = email
    user.role = 'admin'

    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    click.echo(f'Admin {username} created')
