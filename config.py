#存储配置
import os
basedir = os.path.abspath(os.path.dirname(__file__))    #获取当前文件所在绝对路径

#通用配置
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    MAIL_SERVER = 'smtp.163.com'
    MAIL_PORT = 25
    MAIL_USE_TLS = True
    MAIL_USERNAME = 15243686281
    MAIL_PASSWORD = 'wcj1996827'
    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]' #邮件前缀配置
    FLASKY_MAIL_SENDER = '15243686281@163.com'
    FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN') or '15243686281@163.com'   #管理员邮件地址，用于判断是否是管理员
    FLASKY_POSTS_PER_PAGE = 15  #每一页显示的文章数量
    FLASKY_FOLLOWERS_PER_PAGE = 10  #每一页显示的关注者数量
    FLASKY_COMMENTS_PER_PAGE = 10   #枚一页显示的评论

    @staticmethod
    #执行对当前环境的初始化
    def init_app(app):
        pass

#定义不同的开发环境
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data.sqlite')


#注册不同的开发环境
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig    #默认开发环境
}
