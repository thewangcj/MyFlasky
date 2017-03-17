from flask import render_template,redirect,request,url_for,flash
from flask_login import login_user,login_required,logout_user,current_user
from . import auth
from .forms import *
from ..email import send_email
from .. import db

# 针对全局请求的钩子，用于过滤未确认的账户
@auth.before_app_request
def before_request():
    # 用户已登录但未确认且请求的端点不在认证蓝本中
    if current_user.is_authenticated:
        # 更新已登录用户的访问时间
        current_user.ping()
        # endpoint用于获取请求端点
        if  not current_user.confirmed\
            and request.endpoint[:5]!='auth.'\
            and request.endpoint!='static':
                return redirect(url_for('auth.unconfirmed'))

# 用户未认证
@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            #调用Flask-Login 中的login_user() 函数，在用户会话中把用户标记为已登录
            login_user(user,form.remember_me.data)
            #用户访问未授权的 URL 时会显示登录表单，Flask-Login 会把原地址保存在查询字符串的 next 参数中，
            #这个参数可从 request.args 字典中读取。
            #如果查询字符串中没有 next 参数，则重定向到首页
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('Invaild username or password')
    return render_template('auth/login.html',form = form)

@auth.route('/logout')
@login_required # Flask-Login 提供了一个 login_required 修饰器用于保护路由只让认证用户使用
def logout():
    logout_user()
    flash('You hava been logged out.')
    return redirect(url_for('main.index'))

# 注册用户并发送激活邮件
@auth.route('/register',methods=['GET','POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit() #这里一定要写这句，提交数据库才能分配id,确认令牌的生成要用到，所以要写在前面
        token = user.generate_confirmation_token()
        #发送验证邮件
        send_email(user.email,'Confirm Your Account',
                   'auth/email/confirm',user=user,token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html',form=form)

# 确认用户的账户
@auth.route('/confirm/<token>')
@login_required # 要先登录才能认证
def confirm(token):
    if current_user.confirmed:  #检测用户是否已经认证过
        return redirect(url_for('main.index'))
    if current_user.confirm(token): #调用用户模型中的 confirm 方法
        flash('You have confirmed your account.Thanks!')
    else:
        flash('The confirmation link is invalid or has expired')
    return redirect(url_for('main.index'))

# 重新发送账户确认邮件
@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token();
    send_email(current_user.email,'Confirm Your Account',
               'auth/email/confirm',user=current_user,token=token)
    flash('A new confirmation email has been sent to you by email')
    return redirect(url_for('main.index'))

# 修改密码
@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # 验证旧密码
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template("auth/change_password.html", form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)

# 修改邮箱
@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            # 发送确认邮件
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)

# 验证修改邮箱邮件
@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))



















