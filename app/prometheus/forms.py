from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, PasswordField, SelectField, StringField
from wtforms.validators import URL, DataRequired, Length, NumberRange, Optional


class PrometheusConfigForm(FlaskForm):
    endpoint = StringField(
        'Endpoint',
        validators=[
            DataRequired(),
            URL(),
            Length(max=255),
        ],
    )

    auth_type = SelectField(
        'Authentication',
        choices=[
            ('none', 'None'),
            ('basic', 'Basic Auth'),
            ('bearer', 'Bearer Token'),
        ],
        default='none',
    )

    username = StringField(
        'Username',
        validators=[
            Optional(),
            Length(max=255),
        ],
    )

    password = PasswordField(
        'Password',
        validators=[
            Optional(),
            Length(max=255),
        ],
    )

    bearer_token = PasswordField(
        'Bearer Token',
        validators=[
            Optional(),
            Length(max=4096),
        ],
    )

    timeout = IntegerField(
        'Timeout',
        validators=[
            DataRequired(),
            NumberRange(
                min=1,
                max=300,
            ),
        ],
        default=30,
    )

    verify_ssl = BooleanField(
        'Verify SSL',
        default=True,
    )
