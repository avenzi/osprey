from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, DecimalField
from wtforms.validators import DataRequired, Optional

class LoginForm(FlaskForm):
    # DataRequired() validator method checks that fields are not submitted empty
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class TriggerSettingsForm(FlaskForm):
    audio = IntegerField('Audio (dB):')
    temperature = DecimalField('Temperature (&#8457):', places=1)
    submit = SubmitField('OK')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password_confirm = PasswordField('Password Confirmation', validators=[DataRequired()])
    submit = SubmitField('Submit')