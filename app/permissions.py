from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required

ADMIN = 'Администратор'
MODERATOR = 'Модератор'
USER = 'Пользователь'


def has_role(*roles):
    return current_user.is_authenticated and current_user.role_name in roles


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(*args, **kwargs):
            if not has_role(*roles):
                flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
                return redirect(url_for('books.index'))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
