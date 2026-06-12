import hashlib
import os
from datetime import datetime

from app import app
from models import Book, Cover, Genre, Review, Role, User, db


def make_svg_cover(title, index):
    colors = ['#243b53', '#7c2d12', '#14532d', '#3b0764', '#1e3a8a', '#713f12']
    color = colors[index % len(colors)]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="900" viewBox="0 0 640 900">
<rect width="640" height="900" fill="{color}"/>
<circle cx="520" cy="120" r="150" fill="rgba(255,255,255,0.12)"/>
<circle cx="90" cy="760" r="210" fill="rgba(255,255,255,0.10)"/>
<text x="70" y="420" font-family="Arial" font-size="54" fill="white" font-weight="700">{title}</text>
<text x="70" y="500" font-family="Arial" font-size="28" fill="rgba(255,255,255,0.75)">Электронная библиотека</text>
</svg>'''


def add_cover(book, index):
    svg = make_svg_cover(book.title, index).encode('utf-8')
    md5_hash = hashlib.md5(svg).hexdigest()
    file_name = f'cover-{index}.svg'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{md5_hash}.svg')

    if not os.path.exists(file_path):
        with open(file_path, 'wb') as file:
            file.write(svg)

    book.cover = Cover(
        file_name=file_name,
        mime_type='image/svg+xml',
        md5_hash=md5_hash,
    )


def seed():
    os.makedirs(app.config['INSTANCE_DIR'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.drop_all()
    db.create_all()

    roles = {
        'Администратор': Role(
            name='Администратор',
            description='Суперпользователь, имеет полный доступ к системе.'
        ),
        'Модератор': Role(
            name='Модератор',
            description='Может редактировать данные книг и модерировать рецензии.'
        ),
        'Пользователь': Role(
            name='Пользователь',
            description='Может оставлять рецензии.'
        ),
    }
    db.session.add_all(roles.values())

    users = [
        User(login='admin', last_name='Админов', first_name='Алексей', middle_name='Петрович', role=roles['Администратор']),
        User(login='moderator', last_name='Модераторов', first_name='Иван', middle_name='Иванович', role=roles['Модератор']),
        User(login='user', last_name='Пользователев', first_name='Пётр', middle_name='Сергеевич', role=roles['Пользователь']),
    ]
    for user in users:
        user.set_password('qwerty')
    db.session.add_all(users)

    genre_names = ['Роман', 'Фантастика', 'Детектив', 'Научная литература', 'История', 'Программирование']
    genres = {name: Genre(name=name) for name in genre_names}
    db.session.add_all(genres.values())
    db.session.flush()

    books_data = [
        ('Преступление и наказание', 'Роман о выборе, вине и внутренней борьбе человека.', 1866, 'Русский вестник', 'Фёдор Достоевский', 672, ['Роман']),
        ('Мастер и Маргарита', 'Мистический роман о Москве, любви и свободе.', 1967, 'Москва', 'Михаил Булгаков', 480, ['Роман', 'Фантастика']),
        ('Пикник на обочине', 'Фантастическая история о Зоне и людях рядом с ней.', 1972, 'Аврора', 'Аркадий и Борис Стругацкие', 256, ['Фантастика']),
        ('Чистый код', 'Практическая книга о понятном и поддерживаемом коде.', 2008, 'Питер', 'Роберт Мартин', 464, ['Программирование']),
        ('Грокаем алгоритмы', 'Простое введение в алгоритмы с понятными иллюстрациями.', 2016, 'Питер', 'Адитья Бхаргава', 288, ['Программирование']),
        ('Шерлок Холмс', 'Сборник детективных историй о знаменитом сыщике.', 1892, 'George Newnes', 'Артур Конан Дойл', 384, ['Детектив']),
        ('Краткая история времени', 'Популярное объяснение космологии и устройства Вселенной.', 1988, 'Bantam Books', 'Стивен Хокинг', 256, ['Научная литература']),
        ('Sapiens', 'История развития человечества от древности до современности.', 2011, 'Dvir', 'Юваль Ной Харари', 512, ['История', 'Научная литература']),
        ('Дюна', 'Эпическая фантастика о власти, пустынной планете и пророчестве.', 1965, 'Chilton Books', 'Фрэнк Герберт', 704, ['Фантастика']),
        ('451 градус по Фаренгейту', 'Антиутопия о мире, где книги запрещены.', 1953, 'Ballantine Books', 'Рэй Брэдбери', 256, ['Фантастика']),
        ('Имя розы', 'Исторический детектив в стенах средневекового монастыря.', 1980, 'Bompiani', 'Умберто Эко', 640, ['Детектив', 'История']),
        ('Python к вершинам мастерства', 'Книга о возможностях языка Python и хороших практиках.', 2015, 'O’Reilly', 'Лучано Рамальо', 792, ['Программирование']),
    ]

    books = []
    for index, data in enumerate(books_data, start=1):
        title, description, year, publisher, author, pages, book_genres = data
        book = Book(
            title=title,
            short_description=description,
            year=year,
            publisher=publisher,
            author=author,
            pages=pages,
            genres=[genres[name] for name in book_genres],
        )
        add_cover(book, index)
        books.append(book)

    db.session.add_all(books)
    db.session.flush()

    reviews = [
        Review(book=books[0], user=users[2], rating=5, text='Сильная книга, читается тяжело, но очень цепляет.'),
        Review(book=books[1], user=users[2], rating=5, text='Очень атмосферно. Особенно понравилась линия Маргариты.'),
        Review(book=books[3], user=users[1], rating=4, text='Полезно для понимания качества кода.'),
        Review(book=books[4], user=users[2], rating=5, text='Хорошо подходит для старта в алгоритмах.'),
        Review(book=books[8], user=users[1], rating=5, text='Большой мир и классная атмосфера.'),
    ]
    db.session.add_all(reviews)
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        seed()
        print('База данных создана и заполнена.')
        print('Пользователи: admin/qwerty, moderator/qwerty, user/qwerty')
