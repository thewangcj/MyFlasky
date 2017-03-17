from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config   #导入配置
from flask_login import LoginManager
from flask_pagedown import PageDown

#初始化flask-login
login_manager = LoginManager()
#设为'strong' 时，Flask-Login 会记录客户端IP地址和浏览器的用户代理信息，如果发现异动就登出用户
login_manager.session_protection = 'strong'
#登录页面的端点，前面要加蓝图的名字
login_manager.login_view = 'auth.login'

bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
pagedown = PageDown()

# 程序的工厂函数，用于在不同的环境中显示调用创建程序，提高测试覆盖率
def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name]) # Flask app.config提供的函数，从类中直接导入配置
    config[config_name].init_app(app)

    # 配置各种拓展
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)    # 初始化数据库
    login_manager.init_app(app)
    pagedown.init_app(app)

    # 注册蓝图
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')  # 以后所有该蓝图下的路由前面都带有/auth

    return app

