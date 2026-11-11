from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from datetime import datetime
import os

app = Flask(__name__, static_folder='static', static_url_path='')

# Настройка для Render (использует переменную PORT)
port = int(os.environ.get('PORT', 5000))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///detailing.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'shadow-detailing-secret-key-2026')

CORS(app)

db = SQLAlchemy(app)

# --- ЛОГИН И ПАРОЛЬ АДМИНКИ ---
ADMIN_LOGIN = 'admin'
ADMIN_PASSWORD = 'shadow2026'

# --- МОДЕЛЬ ЗАЯВКИ ---
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    car_brand = db.Column(db.String(100), nullable=False)
    service = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"Заявка #{self.id}: {self.car_brand}"

    def to_dict(self):
        return {
            'id': self.id,
            'car_brand': self.car_brand,
            'service': self.service,
            'contact': self.contact,
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None
        }

# --- ЗАЩИЩЁННЫЙ VIEW ---
class SecureModelView(ModelView):
    def is_accessible(self):
        return session.get('logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login', next=request.url))

class LeadView(SecureModelView):
    column_list = ('id', 'car_brand', 'service', 'contact', 'created_at')
    column_labels = {
        'id': 'ID',
        'car_brand': 'Марка авто',
        'service': 'Услуга',
        'contact': 'Контакт',
        'created_at': 'Дата заявки'
    }
    column_searchable_list = ('car_brand', 'contact')
    column_filters = ('service', 'created_at')
    column_default_sort = ('created_at', True)
    form_columns = ('car_brand', 'service', 'contact')
    can_delete = True
    can_edit = True
    can_create = True

    def _service_formatter(view, context, model, name):
        services = {
            'polishing': 'Полировка ЛКП',
            'film': 'Оклейка пленкой',
            'interior': 'Детейлинг салона'
        }
        return services.get(model.service, model.service)

    column_formatters = {
        'service': _service_formatter
    }

# --- ЗАЩИЩЁННАЯ ГЛАВНАЯ АДМИНКИ ---
class SecureAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return session.get('logged_in')

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login', next=request.url))

# --- СОЗДАЁМ ТАБЛИЦЫ ---
with app.app_context():
    db.create_all()

# --- АДМИН-ПАНЕЛЬ ---
admin = Admin(app, name='Shadow Detailing', index_view=SecureAdminIndexView(url='/admin'))
admin.add_view(LeadView(Lead, db, name='Заявки', url='/admin/lead'))

# --- СТРАНИЦА ЛОГИНА ---
LOGIN_PAGE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Вход в админ-панель</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #0d0d0d;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .login-box {
            background: #1a1a1a;
            padding: 40px;
            border-radius: 15px;
            border: 2px solid #ccff00;
            box-shadow: 0 0 30px rgba(204, 255, 0, 0.3);
            width: 380px;
        }
        h2 { text-align: center; margin-bottom: 25px; color: #ccff00; letter-spacing: 2px; }
        input {
            width: 100%; padding: 12px; margin-bottom: 15px;
            background: #222; border: 1px solid #333; border-radius: 5px;
            color: white; font-size: 14px;
        }
        input:focus { outline: none; border-color: #ccff00; }
        button {
            width: 100%; padding: 12px; background: #ccff00; color: #000;
            border: none; border-radius: 5px; font-weight: 900;
            font-size: 14px; cursor: pointer; letter-spacing: 1px;
        }
        button:hover { background: #b3e600; }
        .error { color: #ff4444; text-align: center; margin-bottom: 15px; font-size: 13px; }
        .back { display: block; text-align: center; margin-top: 15px; color: #888; text-decoration: none; font-size: 13px; }
        .back:hover { color: #ccff00; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 ВХОД В АДМИН-ПАНЕЛЬ</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Логин" required autofocus>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">ВОЙТИ</button>
        </form>
        <a href="/" class="back">← Вернуться на сайт</a>
    </div>
</body>
</html>
'''

# --- РОУТ ЛОГИНА ---
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            next_url = request.args.get('next', '/admin')
            return redirect(next_url)
        else:
            return render_template_string(LOGIN_PAGE, error='Неверный логин или пароль')

    return render_template_string(LOGIN_PAGE, error=None)

# --- РОУТ ВЫХОДА ---
@app.route('/admin-logout')
def admin_logout():
    session.clear()
    return redirect('/admin-login')

# --- ПРИЁМ ЗАЯВКИ ---
@app.route('/api/submit', methods=['POST'])
def submit_lead():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Нет данных'}), 400

        new_lead = Lead(
            car_brand=data.get('car_brand'),
            service=data.get('service'),
            contact=data.get('contact')
        )

        db.session.add(new_lead)
        db.session.commit()

        return jsonify({
            'message': 'Заявка успешно отправлена!',
            'lead': new_lead.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- ПОЛУЧИТЬ ВСЕ ЗАЯВКИ ---
@app.route('/api/leads', methods=['GET'])
def get_leads():
    leads = Lead.query.order_by(Lead.id.desc()).all()
    return jsonify([lead.to_dict() for lead in leads])

# --- РАЗДАЧА САЙТА ---
@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=False)