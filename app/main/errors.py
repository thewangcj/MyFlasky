from flask import render_template
from . import main

#在蓝图中，只有该蓝图的错误才会被触发，而全局的错误要用app_errorhandler()
@main.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
