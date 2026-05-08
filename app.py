"""
Главный файл Flask приложения
Веб-сайт с кейсами, формой обратной связи и админ-панелью
"""
import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, TextAreaField, EmailField, TelField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_wtf import FlaskForm, CSRFProtect
from config import Config
from backend.rag_index import generate_answer as rag_generate_answer

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
login_manager.login_message_category = 'info'

# Модели базы данных
class Contact(db.Model):
    """Модель для хранения заявок из формы обратной связи"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Contact {self.name} - {self.subject}>'
    
    def to_dict(self):
        """Преобразование объекта в словарь для JSON"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'subject': self.subject,
            'message': self.message,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'is_read': self.is_read
        }

class AdminUser(UserMixin):
    """Модель пользователя для админ-панели"""
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    if user_id == 'admin':
        return AdminUser('admin')
    return None

# Формы
class ContactForm(FlaskForm):
    """Форма обратной связи"""
    name = StringField('Имя', validators=[DataRequired(message='Поле обязательно для заполнения'), 
                                          Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')])
    email = EmailField('Email', validators=[DataRequired(message='Поле обязательно для заполнения'), 
                                            Email(message='Введите корректный email адрес')])
    phone = TelField('Телефон', validators=[DataRequired(message='Поле обязательно для заполнения')])
    subject = SelectField('Тема сообщения', 
                         choices=[
                             ('', 'Выберите тему'),
                             ('telegram_bot', 'Разработка Telegram-бота'),
                             ('online_store', 'Создание интернет-магазина'),
                             ('crm_automation', 'Автоматизация CRM'),
                             ('corporate_site', 'Разработка корпоративного сайта'),
                             ('ai_assistant', 'AI-ассистент для поддержки клиентов'),
                             ('other', 'Другое')
                         ],
                         validators=[DataRequired(message='Выберите тему сообщения')],
                         default='')
    message = TextAreaField('Сообщение', validators=[DataRequired(message='Поле обязательно для заполнения'),
                                                     Length(min=10, max=1000, message='Сообщение должно быть от 10 до 1000 символов')])
    submit = SubmitField('Отправить')

class AdminLoginForm(FlaskForm):
    """Форма входа в админ-панель"""
    username = StringField('Логин', validators=[DataRequired()])
    password = StringField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

# Данные кейсов
CASES_DATA = {
    'telegram_bot': {
        'id': 'telegram_bot',
        'title': 'Разработка Telegram-бота для бизнеса',
        'short_description': 'Автоматизация бизнес-процессов через Telegram',
        'description': '''
        <p>Разработан полнофункциональный Telegram-бот для автоматизации бизнес-процессов компании. 
        Бот позволяет клиентам получать информацию о компании</p>
        <p>Ссылка: https://t.me/ragassistant_simple_bot</p>
        
        <h4>Основные возможности:</h4>
        <ul>
            <li>Интеграция с базой данных товаров</li>
            <li>Система заказов и оплаты</li>
            <li>Уведомления о статусе заказа</li>
            <li>Многоязычная поддержка</li>
            <li>Админ-панель для управления</li>
        </ul>
        
        <h4>Технологии:</h4>
        <p>Python, aiogram, PostgreSQL, Redis, Docker</p>
        
        <h4>Результат:</h4>
        <p>Сокращение времени обработки заказов на 70%, увеличение конверсии на 45%</p>
        ''',
        'image': 'telegram-bot.jpg'
    },
    'online_store': {
        'id': 'online_store',
        'title': 'Создание интернет-магазина',
        'short_description': 'Современный интернет-магазин с полным функционалом',
        'description': '''
        <p>Разработан полнофункциональный интернет-магазин с современным дизайном и удобным интерфейсом. 
        Магазин включает систему управления товарами, корзину покупок, интеграцию с платежными системами 
        и систему управления заказами.</p>
        
        <h4>Основные возможности:</h4>
        <ul>
            <li>Каталог товаров с фильтрацией и поиском</li>
            <li>Корзина покупок и оформление заказа</li>
            <li>Интеграция с платежными системами</li>
            <li>Личный кабинет пользователя</li>
            <li>Админ-панель для управления</li>
            <li>Система отзывов и рейтингов</li>
        </ul>
        
        <h4>Технологии:</h4>
        <p>Python, Flask/Django, PostgreSQL, Stripe, Redis, Celery</p>
        
        <h4>Результат:</h4>
        <p>Запуск магазина за 2 месяца, первые продажи в первую неделю</p>
        ''',
        'image': 'online-store.jpg'
    },
    'crm_automation': {
        'id': 'crm_automation',
        'title': 'Автоматизация CRM',
        'short_description': 'Автоматизация процессов управления клиентами',
        'description': '''
        <p>Разработана система автоматизации CRM для оптимизации работы с клиентами. 
        Система автоматизирует процессы обработки заявок, отправки уведомлений, 
        ведения истории взаимодействий и аналитики.</p>
        
        <h4>Основные возможности:</h4>
        <ul>
            <li>Автоматическая обработка заявок</li>
            <li>Интеграция с email и мессенджерами</li>
            <li>Автоматические напоминания и уведомления</li>
            <li>Аналитика и отчетность</li>
            <li>Распределение задач между менеджерами</li>
            <li>Интеграция с внешними сервисами</li>
        </ul>
        
        <h4>Технологии:</h4>
        <p>Python, Django, PostgreSQL, Celery, RabbitMQ, REST API</p>
        
        <h4>Результат:</h4>
        <p>Сокращение времени обработки заявок на 60%, увеличение конверсии на 35%</p>
        ''',
        'image': 'crm-automation.jpg'
    },
    'corporate_site': {
        'id': 'corporate_site',
        'title': 'Разработка корпоративного сайта',
        'short_description': 'Современный корпоративный сайт с админ-панелью',
        'description': '''
        <p>Разработан современный корпоративный сайт с адаптивным дизайном и удобной админ-панелью. 
        Сайт включает систему управления контентом, блог, форму обратной связи и интеграцию 
        с социальными сетями.</p>
        
        <h4>Основные возможности:</h4>
        <ul>
            <li>Адаптивный дизайн для всех устройств</li>
            <li>Система управления контентом (CMS)</li>
            <li>Блог с категориями и тегами</li>
            <li>Форма обратной связи</li>
            <li>Интеграция с социальными сетями</li>
            <li>SEO-оптимизация</li>
            <li>Многоязычная поддержка</li>
        </ul>
        
        <h4>Технологии:</h4>
        <p>Python, Flask, PostgreSQL, Bootstrap, JavaScript</p>
        
        <h4>Результат:</h4>
        <p>Увеличение трафика на 200%, улучшение позиций в поисковых системах</p>
        ''',
        'image': 'corporate-site.jpg'
    },
    'ai_assistant': {
        'id': 'ai_assistant',
        'title': 'RAG AI-ассистент для сайта',
        'short_description': 'Чат-виджет для сайта с ответами по базе знаний в реальном времени',
        'description': '''
        <p>В проект встроен AI-ассистент, который работает прямо на страницах сайта:
        пользователь задает вопрос в диалоговом окне и получает ответ на основе RAG-поиска
        по подготовленной базе знаний.</p>
        
        <h4>Основные возможности:</h4>
        <ul>
            <li>Диалоговый виджет доступен на всех основных страницах</li>
            <li>Ответы на базе FAQ/документов через FAISS-поиск</li>
            <li>Контекстные ответы через OpenAI с ограничением по смыслу</li>
            <li>Стабильный fallback-режим при недоступности модели</li>
            <li>Удобный API-эндпоинт для дальнейшего расширения логики</li>
        </ul>
        
        <h4>Технологии:</h4>
        <p>Python, Flask, OpenAI API, FAISS, JavaScript</p>
        
        <h4>Результат:</h4>
        <p>Пользователь получает быстрый ответ сразу на сайте, а команда экономит время
        на первичной коммуникации и обработке типовых вопросов.</p>
        ''',
        'image': 'ai-assistant.jpg'
    }
}

# Роуты для основных страниц
@app.route('/')
def index():
    """Главная страница"""
    logger.info('Главная страница запрошена')
    return render_template('index.html', cases=CASES_DATA)

@app.route('/cases')
def cases():
    """Страница со всеми кейсами"""
    logger.info('Страница кейсов запрошена')
    return render_template('cases.html', cases=CASES_DATA)

@app.route('/case/<case_id>')
def case_detail(case_id):
    """Страница с детальным описанием кейса"""
    case = CASES_DATA.get(case_id)
    if not case:
        flash('Кейс не найден', 'error')
        return redirect(url_for('cases'))
    logger.info(f'Детальная страница кейса {case_id} запрошена')
    return render_template('case_detail.html', case=case)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Страница с формой обратной связи"""
    form = ContactForm()
    
    if form.validate_on_submit():
        try:
            # Создание новой заявки
            contact = Contact(
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data,
                subject=form.subject.data,
                message=form.message.data
            )
            db.session.add(contact)
            db.session.commit()
            
            logger.info(f'Новая заявка создана: {contact.name} - {contact.subject}')
            flash('Спасибо! Ваше сообщение успешно отправлено. Мы свяжемся с вами в ближайшее время.', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Ошибка при создании заявки: {str(e)}')
            flash('Произошла ошибка при отправке сообщения. Попробуйте позже.', 'error')
    
    return render_template('contact.html', form=form)

# Роуты для админ-панели
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Страница входа в админ-панель"""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    
    form = AdminLoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        # Проверка учетных данных
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            user = AdminUser('admin')
            login_user(user, remember=True)
            logger.info(f'Администратор {username} вошел в систему')
            flash('Вы успешно вошли в систему', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            logger.warning(f'Неудачная попытка входа: {username}')
            flash('Неверный логин или пароль', 'error')
    
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Выход из админ-панели"""
    logger.info(f'Администратор {current_user.id} вышел из системы')
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Главная страница админ-панели"""
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    unread_count = Contact.query.filter_by(is_read=False).count()
    total_count = Contact.query.count()
    
    logger.info('Админ-панель запрошена')
    return render_template('admin/dashboard.html', 
                         contacts=contacts, 
                         unread_count=unread_count,
                         total_count=total_count)

@app.route('/admin/contact/<int:contact_id>/read', methods=['POST'])
@login_required
def mark_as_read(contact_id):
    """Отметить заявку как прочитанную"""
    contact = Contact.query.get_or_404(contact_id)
    contact.is_read = True
    db.session.commit()
    logger.info(f'Заявка {contact_id} отмечена как прочитанная')
    return jsonify({'success': True})

@app.route('/admin/contact/<int:contact_id>/delete', methods=['POST'])
@login_required
def delete_contact(contact_id):
    """Удалить заявку"""
    contact = Contact.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    logger.info(f'Заявка {contact_id} удалена')
    flash('Заявка успешно удалена', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/chat', methods=['POST'])
@csrf.exempt
def chat():
    """API-эндпоинт для RAG-чатбота на главной странице."""
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    top_k = data.get('top_k') or 3

    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = 3

    if not message:
        return jsonify({'error': 'Пустое сообщение'}), 400

    try:
        result = rag_generate_answer(message, top_k=top_k)
        logger.info('Чат-бот обработал сообщение пользователя')
        return jsonify(result)
    except Exception as e:
        logger.exception(f'Ошибка RAG-чатбота: {e}')
        return jsonify({'error': 'Ошибка при обработке запроса чат-бота'}), 500

# Инициализация базы данных
def init_db():
    """Создание таблиц базы данных"""
    with app.app_context():
        db.create_all()
        logger.info('База данных инициализирована')

# Обработчик ошибок
@app.errorhandler(404)
def not_found_error(error):
    """Обработка ошибки 404"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработка ошибки 500"""
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    # Создание таблиц при запуске
    init_db()
    logger.info('Приложение запущено')
    app.run(debug=True, host='0.0.0.0', port=5000)

