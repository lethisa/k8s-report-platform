from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from app.cluster.constants import ENVIRONMENTS


class ClusterCreateForm(FlaskForm):
    name = StringField(
        'Cluster Name',
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    environment = SelectField(
        'Environment',
        validators=[DataRequired()],
        choices=ENVIRONMENTS,
    )

    description = TextAreaField('Description')

    kubeconfig = FileField(
        'Kubeconfig',
        validators=[FileRequired()],
    )

    submit = SubmitField('Save Cluster')


class ClusterEditForm(FlaskForm):
    name = StringField(
        'Cluster Name',
        validators=[
            DataRequired(),
            Length(max=100),
        ],
    )

    environment = SelectField(
        'Environment',
        validators=[DataRequired()],
        choices=ENVIRONMENTS,
    )

    description = TextAreaField('Description')

    submit = SubmitField('Update Cluster')
