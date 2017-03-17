#单元测试
import unittest
from flask import current_app
from app import create_app, db


class BasicsTestCase(unittest.TestCase):
    # setUp()方法尝试创建一个测试环境，类似于运行中的程序
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context() #激活上下文
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_app_exists(self):
        self.assertFalse(current_app is None)

    def test_app_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
