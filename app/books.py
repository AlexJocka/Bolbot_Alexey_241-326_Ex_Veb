import hashlib
import os

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from models import Book, Cover, Genre, Review, db
from permissions import ADMIN, MODERATOR, USER, role_required
from utils import sanitize_markdown_text

bp = Blueprint('books', __name__)

RATING_OPTIONS = [
    (5, 'отлично'),
    (4, 'хорошо'),
    (3, 'удовлетворительно'),
    (2, 'неудовлетворительно'),
    (1, 'плохо'),
    (0, 'ужасно'),
]


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_int_list(values):
    result = []
    for value in values:
        number = parse_int(value)
        if number is not None:
            result.append(number)
    return result


def all_genres():
    return db.session.execute(db.select(Genre).order_by(Genre.name)).scalars().all()


def search_params():
    return {
        'title': request.args.get('title', '').strip(),
        'author': request.args.get('author', '').strip(),
        'genre_ids': request.args.getlist('genre_ids'),
        'years': request.args.getlist('years'),
        'pages_from': request.args.get('pages_from', '').strip(),
        'pages_to': request.args.get('pages_to', '').strip(),
    }


def filtered_books_query(params):
    query = db.select(Book).order_by(Book.year.desc(), Book.id.desc())

    if params['title']:
        query = query.filter(Book.title.ilike(f'%{params["title"]}%'))

    if params['author']:
        query = query.filter(Book.author.ilike(f'%{params["author"]}%'))

    genre_ids = parse_int_list(params['genre_ids'])
    if genre_ids:
        query = query.join(Book.genres).filter(Genre.id.in_(genre_ids)).distinct()

    years = parse_int_list(params['years'])
    if years:
        query = query.filter(Book.year.in_(years))

    pages_from = parse_int(params['pages_from'])
    if pages_from is not None:
        query = query.filter(Book.pages >= pages_from)

    pages_to = parse_int(params['pages_to'])
    if pages_to is not None:
        query = query.filter(Book.pages <= pages_to)

    return query


def book_form_data(book=None):
    if book is None:
        return {
            'title': '',
            'short_description': '',
            'year': '',
            'publisher': '',
            'author': '',
            'pages': '',
        }

    return {
        'title': book.title,
        'short_description': book.short_description,
        'year': str(book.year),
        'publisher': book.publisher,
        'author': book.author,
        'pages': str(book.pages),
    }


def request_book_form_data():
    return {
        'title': request.form.get('title', '').strip(),
        'short_description': request.form.get('short_description', '').strip(),
        'year': request.form.get('year', '').strip(),
        'publisher': request.form.get('publisher', '').strip(),
        'author': request.form.get('author', '').strip(),
        'pages': request.form.get('pages', '').strip(),
    }


def validate_book_data(form, selected_genre_ids, cover_required=False):
    required_fields = ['title', 'short_description', 'year', 'publisher', 'author', 'pages']
    if any(not form[field] for field in required_fields):
        raise ValueError('required fields')

    year = parse_int(form['year'])
    pages = parse_int(form['pages'])
    if year is None or pages is None or pages <= 0:
        raise ValueError('invalid numbers')

    if not selected_genre_ids:
        raise ValueError('genres required')

    if cover_required:
        cover_file = request.files.get('cover')
        if not cover_file or not cover_file.filename:
            raise ValueError('cover required')

    return year, pages


def selected_genres_from_form():
    return parse_int_list(request.form.getlist('genre_ids'))


def load_selected_genres(selected_genre_ids):
    genres = db.session.execute(
        db.select(Genre).filter(Genre.id.in_(selected_genre_ids))
    ).scalars().all()
    if len(genres) != len(set(selected_genre_ids)):
        raise ValueError('invalid genres')
    return genres


def current_user_review(book_id):
    if not current_user.is_authenticated:
        return None
    return db.session.execute(
        db.select(Review).filter_by(book_id=book_id, user_id=current_user.id)
    ).scalar_one_or_none()


def save_cover(cover_file, book):
    file_content = cover_file.read()
    if not file_content:
        raise ValueError('empty cover')

    md5_hash = hashlib.md5(file_content).hexdigest()
    existing_cover = db.session.execute(
        db.select(Cover).filter_by(md5_hash=md5_hash)
    ).scalar_one_or_none()

    if existing_cover:
        file_name = existing_cover.file_name
        should_save_file = False
    else:
        file_name = secure_filename(cover_file.filename)
        should_save_file = True

    if not file_name:
        file_name = 'cover.img'

    cover = Cover(
        file_name=file_name,
        mime_type=cover_file.mimetype or 'application/octet-stream',
        md5_hash=md5_hash,
        book=book,
    )
    db.session.add(cover)

    if should_save_file:
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cover.storage_filename)
        with open(file_path, 'wb') as file:
            file.write(file_content)
        return file_path

    return None


@bp.route('/')
def index():
    params = search_params()
    page = request.args.get('page', 1, type=int)
    pagination = db.paginate(filtered_books_query(params), page=page, per_page=10, error_out=False)

    return render_template(
        'books/index.html',
        books=pagination.items,
        pagination=pagination,
        genres=all_genres(),
        years=Book.years_query(),
        search=params,
    )


@bp.route('/books/new', methods=['GET', 'POST'])
@role_required(ADMIN)
def new():
    form = book_form_data()
    selected_genre_ids = []
    new_file_path = None

    if request.method == 'POST':
        form = request_book_form_data()
        selected_genre_ids = selected_genres_from_form()
        try:
            year, pages = validate_book_data(form, selected_genre_ids, cover_required=True)
            genres = load_selected_genres(selected_genre_ids)
            book = Book(
                title=form['title'],
                short_description=sanitize_markdown_text(form['short_description']),
                year=year,
                publisher=form['publisher'],
                author=form['author'],
                pages=pages,
            )
            book.genres = genres
            db.session.add(book)
            db.session.flush()
            new_file_path = save_cover(request.files['cover'], book)
            db.session.commit()
            flash('Книга успешно добавлена.', 'success')
            return redirect(url_for('books.show', book_id=book.id))
        except (ValueError, SQLAlchemyError):
            db.session.rollback()
            if new_file_path and os.path.exists(new_file_path):
                os.remove(new_file_path)
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')

    return render_template(
        'books/form.html',
        title='Добавление книги',
        form=form,
        genres=all_genres(),
        selected_genre_ids=selected_genre_ids,
        action=url_for('books.new'),
        with_cover=True,
    )


@bp.route('/books/<int:book_id>')
def show(book_id):
    book = db.get_or_404(Book, book_id)
    reviews = db.session.execute(
        db.select(Review).filter_by(book_id=book.id).order_by(Review.created_at.desc())
    ).scalars().all()

    return render_template(
        'books/show.html',
        book=book,
        reviews=reviews,
        current_review=current_user_review(book.id),
    )


@bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@role_required(ADMIN, MODERATOR)
def edit(book_id):
    book = db.get_or_404(Book, book_id)
    form = book_form_data(book)
    selected_genre_ids = [genre.id for genre in book.genres]

    if request.method == 'POST':
        form = request_book_form_data()
        selected_genre_ids = selected_genres_from_form()
        try:
            year, pages = validate_book_data(form, selected_genre_ids)
            book.title = form['title']
            book.short_description = sanitize_markdown_text(form['short_description'])
            book.year = year
            book.publisher = form['publisher']
            book.author = form['author']
            book.pages = pages
            book.genres = load_selected_genres(selected_genre_ids)
            db.session.commit()
            flash('Данные книги успешно обновлены.', 'success')
            return redirect(url_for('books.show', book_id=book.id))
        except (ValueError, SQLAlchemyError):
            db.session.rollback()
            flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')

    return render_template(
        'books/form.html',
        title='Редактирование книги',
        form=form,
        genres=all_genres(),
        selected_genre_ids=selected_genre_ids,
        action=url_for('books.edit', book_id=book.id),
        with_cover=False,
    )


@bp.route('/books/<int:book_id>/delete', methods=['POST'])
@role_required(ADMIN)
def delete(book_id):
    book = db.get_or_404(Book, book_id)
    cover = book.cover
    cover_file_path = None

    try:
        if cover:
            same_hash_count = db.session.scalar(
                db.select(func.count(Cover.id)).filter(Cover.md5_hash == cover.md5_hash)
            )
            if not same_hash_count or same_hash_count <= 1:
                cover_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cover.storage_filename)

        db.session.delete(book)
        db.session.commit()

        if cover_file_path and os.path.exists(cover_file_path):
            os.remove(cover_file_path)

        flash('Книга успешно удалена.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('При удалении книги возникла ошибка.', 'danger')

    return redirect(url_for('books.index'))


@bp.route('/books/<int:book_id>/reviews/new', methods=['GET', 'POST'])
@role_required(ADMIN, MODERATOR, USER)
def new_review(book_id):
    book = db.get_or_404(Book, book_id)
    if current_user_review(book.id):
        flash('Вы уже написали рецензию на эту книгу.', 'warning')
        return redirect(url_for('books.show', book_id=book.id))

    form = {
        'rating': '5',
        'text': '',
    }

    if request.method == 'POST':
        form = {
            'rating': request.form.get('rating', '5'),
            'text': request.form.get('text', '').strip(),
        }
        rating = parse_int(form['rating'])
        text = sanitize_markdown_text(form['text'])

        try:
            if rating is None or rating < 0 or rating > 5 or not text:
                raise ValueError('invalid review')

            review = Review(
                book=book,
                user=current_user,
                rating=rating,
                text=text,
            )
            db.session.add(review)
            db.session.commit()
            flash('Рецензия успешно добавлена.', 'success')
            return redirect(url_for('books.show', book_id=book.id))
        except (ValueError, SQLAlchemyError):
            db.session.rollback()
            flash('При сохранении рецензии возникла ошибка.', 'danger')

    return render_template(
        'books/review_form.html',
        book=book,
        form=form,
        rating_options=RATING_OPTIONS,
    )
