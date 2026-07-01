import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from settings import PATH_DB

auth_bp = Blueprint('auth', __name__)

def get_current_user():
    if 'user_id' in session:
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', [session['user_id']])
        user = cursor.fetchone()
        conn.close()
        return user
    return None

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        login = request.form.get('login')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error="Паролі не збігаються!")
            
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect(PATH_DB)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        is_admin_value = 1 if count == 0 else 0
        
        try:
            cursor.execute('''
                INSERT INTO users (name, login, password, image, description_short, description, is_admin) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [name, login, hashed_password, '', 'Блогер', 'Привіт усім!', is_admin_value])
            conn.commit()
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Цей логін уже зайнятий!")
        except sqlite3.Error as e:
            return render_template('register.html', error=f"Помилка бази даних: {e}")
        finally:
            conn.close()
            
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        
        conn = sqlite3.connect(PATH_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE login = ?', [login])
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Неправильний логін або пароль!")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))