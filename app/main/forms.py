from flask_wtf import Form
from wtforms import StringField,TextAreaField,SubmitField,BooleanField,SelectField,ValidationError
from wtforms.validators import DataRequired,Length,Email,Regexp
from ..models import Role,User
from flask_pagedown.fields import PageDownField

class NameForm(Form):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')

class EditProfileForm(Form):
    name = StringField('Real name',validators=[Length(0,64)])
    location = StringField('Location',validators=[Length(0,64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

# 管理员编辑个人资料
class EditProfileAdminForm(Form):
    email = StringField('Email',validators=[DataRequired(),Length(1,64),Email()])
    username = StringField('Username',validators=[DataRequired(),Length(1,64),
                                                  Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters,'
                                                         'numbers,dots or underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role',coerce=int)   # 下拉列表，coerce=int 用于将默认的string转换为int，因为roleid是int
    name = StringField('Real name',validators=[Length(0,64)])
    location = StringField('Location',validators=[Length(0,64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self,user,*args,**kwargs):
        super(EditProfileAdminForm,self).__init__(*args,**kwargs)
        # SelectField 实例必须在其 choices 属性中设置各选项。选项必须是一个由元组组成的列表，
        # 各元组都包含两个元素：选项的标识符和显示在控件中的文本字符串
        self.role.choices = [(role.id,role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def vaildate_email(self,field):
        if field.data != self.user.email and \
            User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')

class PostForm(Form):
    # PageDownField Markdown 富文本编辑器
    body = PageDownField("What's on your mind?",validators=[DataRequired()])
    submit = SubmitField('Submit')

class CommentForm(Form):
    body = StringField('Enter your comment', validators=[DataRequired()])
    submit = SubmitField('Submit')