from flask_wtf import FlaskForm
from wtforms.fields import StringField, SubmitField
from wtforms.validators import Required, DataRequired, Email
from wtforms.fields.html5 import EmailField, DateField

# from wtforms import StringField, DateField, IntegerField
# from wtforms.fields.html5 import EmailField, DateField
# from wtforms.validators import DataRequired, Email


class MyForm(FlaskForm):
    firstname = StringField('firstname', validators=[DataRequired("Please specify your firstname")])
    surname = StringField('surname', validators=[DataRequired("Please specify your surname")])
    email = EmailField('email', validators=[DataRequired("A valid email address is required"), Email("A valid email address is required")])
    dob = DateField('dob')
    phone = StringField('phone', validators=[DataRequired("Please specify your phone number")])

class LoginForm(FlaskForm):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[Required()])
    # room = StringField('Room', validators=[Required()])
    submit = SubmitField('Enter Chatroom')
