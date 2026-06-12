from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user

from models import User, db

bp = Blueprint('auth', __name__, url_prefix='/auth')


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    login_manager.init_app(app)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('books.index'))

    if request.method == 'POST':
        login_value = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        user = db.session.execute(db.select(User).filter_by(login=login_value)).scalar_one_or_none()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_url = request.args.get('next')
            if next_url and not urlparse(next_url).netloc:
                return redirect(next_url)
            return redirect(url_for('books.index'))

        flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'success')
    next_url = request.referrer
    if next_url and not urlparse(next_url).netloc and '/auth/login' not in next_url:
        return redirect(next_url)
    return redirect(url_for('books.index'))
