from flask import Blueprint

main = Blueprint('main', __name__)  # 实例化一个蓝图


# 导入views和errors,将其与main连接起来，因为在views和erros中导入了main，所以将其放在底部，防止循环导入依赖
from . import views, errors
from ..models import Permission


# 将Permission类加入模板上下文，上下文处理器能让变量在所有模板中全局可访问
@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)
