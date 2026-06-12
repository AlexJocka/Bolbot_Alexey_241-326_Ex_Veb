import os

from flask import Flask, send_from_directory, request, url_for
from flask_migrate import Migrate

from auth import bp as auth_bp, init_login_manager
from books import bp as books_bp
from models import Cover, db
from permissions import ADMIN, MODERATOR, USER, has_role
from utils import markdown_to_html

app = Flask(__name__)
application = app
app.config.from_pyfile('config.py')

os.makedirs(app.config['INSTANCE_DIR'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)
init_login_manager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)


@app.template_filter('markdown')
def markdown_filter(text):
    return markdown_to_html(text)


@app.context_processor
def inject_helpers():
    def url_for_page(endpoint, page):
        args = request.args.to_dict(flat=False)
        args['page'] = [page]
        return url_for(endpoint, **args)

    return {
        'url_for_page': url_for_page,
        'has_role': has_role,
        'ADMIN': ADMIN,
        'MODERATOR': MODERATOR,
        'USER': USER,
    }


@app.route('/covers/<int:cover_id>')
def cover_file(cover_id):
    cover = db.get_or_404(Cover, cover_id)
    return send_from_directory(app.config['UPLOAD_FOLDER'], cover.storage_filename)
