#!/usr/bin/env python
#用于启动程序
import os
from app import create_app, db
from app.models import User, Role,Post,Comment
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    # 为shell命令注册一个make_context回调函数
    # 该函数将shell自动导入数据库，程序，模型
    return dict(app=app, db=db, User=User, Role=Role,Post=Post,Comment=Comment)

# 初始化 Flask-Script、 Flask-Migrate 和为 Python shell 定义的上下文
manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
# 配置Migrate，，Flask-Migrate 提供了一个MigrateCommand 类，可附加到Flask-Script 的manager 对象上


@manager.command
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    manager.run()
