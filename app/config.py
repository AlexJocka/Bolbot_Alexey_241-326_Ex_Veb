import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'covers')

SECRET_KEY = 'dev-secret-key'
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'library.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False
