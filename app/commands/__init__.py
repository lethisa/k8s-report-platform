from flask import Flask

from app.commands.admin import create_admin


def register_commands(app: Flask) -> None:
    app.cli.add_command(create_admin)
