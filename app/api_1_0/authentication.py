from flask_httpauth import HTTPBasicAuth
from flask import g, jsonify
from ..models import User, AnonymousUser
from .errors import unauthorized, forbidden
from . import api
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    # 未登录时设置为匿名用户
    if email_or_token == '':
        g.current_user = AnonymousUser()
        return True
    if password == '':  # 验证令牌
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    user = User.query.filter_by(email=email_or_token).first()
    if not user:
        return False
    g.current_user = user
    g.token_used = False
    # 验证密码
    return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')  # 401错误


# 整个路由的认证
@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and \
            not g.current_user.confirmed:
        return forbidden('Unconfirmed account')


# 生成认证令牌，g.token_used用于避免使用就令牌请求新令牌
@api.route('/token')
def get_token():
    if g.current_user.is_anonymous() or g.token_used:
        return unauthorized('Invalid credentials')
    return jsonify({'token': g.current_user.generate_auth_token(
        expiration=3600), 'expiration': 3600})















