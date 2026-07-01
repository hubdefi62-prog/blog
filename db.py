import sqlite3
from settings import *

conn = None
cursor = None

def open_db():
    global conn, cursor
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON')

def close_db():
    if cursor:
        cursor.close()
    if conn:
        conn.close()

def execute(query, params=None):
    if params is None:
        cursor.execute(query)
    else:
        cursor.execute(query, params)
    conn.commit()

def create_tables():
    open_db()
    execute('''
        CREATE TABLE IF NOT EXISTS categories (
            category_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT NOT NULL
        )
    ''')
    execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image TEXT,
            login TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            description_short TEXT,
            description TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    execute('''
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT "Без заголовку",
            text TEXT NOT NULL,
            datetime TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
        )
    ''')
    execute('''
        CREATE TABLE IF NOT EXISTS post_images (
            image_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            is_main INTEGER DEFAULT 0,
            FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
        )
    ''')
    execute('''
        CREATE TABLE IF NOT EXISTS comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            text TEXT NOT NULL,
            datetime TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE
        )
    ''')
    execute('''
        CREATE TABLE IF NOT EXISTS likes (
            like_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(post_id) ON DELETE CASCADE,
            UNIQUE(user_id, post_id)
        )
    ''')
    close_db()

def get_categories():
    open_db()
    cursor.execute('SELECT * FROM categories ORDER BY category_id')
    categories = cursor.fetchall()
    close_db()
    return categories

def add_category(category_name):
    open_db()
    execute('INSERT INTO categories (category_name) VALUES (?)', [category_name])
    close_db()

def delete_category(category_id):
    open_db()
    execute('DELETE FROM categories WHERE category_id = ?', [category_id])
    close_db()

def add_post(category_id, text, title="Без заголовку", images=None, datetime=None):
    open_db()
    if datetime is None:
        cursor.execute('INSERT INTO posts (category_id, title, text) VALUES (?, ?, ?)', [category_id, title, text])
    else:
        cursor.execute('INSERT INTO posts (category_id, title, text, datetime) VALUES (?, ?, ?, ?)', [category_id, title, text, datetime])
    post_id = cursor.lastrowid
    if images:
        for index, img_path in enumerate(images):
            is_main = 1 if index == 0 else 0
            cursor.execute('INSERT INTO post_images (post_id, image_path, is_main) VALUES (?, ?, ?)', [post_id, img_path, is_main])
    conn.commit()
    close_db()
    return post_id

def update_post(post_id, category_id, title, text, new_images=None, delete_image_ids=None, main_image_id=None):
    open_db()
    cursor.execute('UPDATE posts SET category_id = ?, title = ?, text = ? WHERE post_id = ?', [category_id, title, text, post_id])
    if delete_image_ids:
        for img_id in delete_image_ids:
            cursor.execute('DELETE FROM post_images WHERE image_id = ?', [img_id])
    if main_image_id:
        cursor.execute('UPDATE post_images SET is_main = 0 WHERE post_id = ?', [post_id])
        cursor.execute('UPDATE post_images SET is_main = 1 WHERE image_id = ?', [main_image_id])
    if new_images:
        cursor.execute('SELECT COUNT(*) FROM post_images WHERE post_id = ? AND is_main = 1', [post_id])
        has_main = cursor.fetchone()[0] > 0
        for index, img_path in enumerate(new_images):
            is_main = 1 if (index == 0 and not has_main) else 0
            cursor.execute('INSERT INTO post_images (post_id, image_path, is_main) VALUES (?, ?, ?)', [post_id, img_path, is_main])
    cursor.execute('SELECT COUNT(*) FROM post_images WHERE post_id = ? AND is_main = 1', [post_id])
    if cursor.fetchone()[0] == 0:
        cursor.execute('SELECT image_id FROM post_images WHERE post_id = ? LIMIT 1', [post_id])
        first_img = cursor.fetchone()
        if first_img:
            cursor.execute('UPDATE post_images SET is_main = 1 WHERE image_id = ?', [first_img['image_id']])
    conn.commit()
    close_db()

def delete_post(post_id):
    open_db()
    execute('DELETE FROM posts WHERE post_id = ?', [post_id])
    close_db()

def get_posts(category_id=None):
    open_db()
    if category_id:
        cursor.execute('''
            SELECT posts.*, categories.category_name, post_images.image_path as main_image
            FROM posts 
            JOIN categories ON posts.category_id = categories.category_id
            LEFT JOIN post_images ON posts.post_id = post_images.post_id AND post_images.is_main = 1
            WHERE posts.category_id = ? 
            ORDER BY posts.post_id DESC
        ''', [category_id])
    else:
        cursor.execute('''
            SELECT posts.*, categories.category_name, post_images.image_path as main_image
            FROM posts 
            JOIN categories ON posts.category_id = categories.category_id
            LEFT JOIN post_images ON posts.post_id = post_images.post_id AND post_images.is_main = 1
            ORDER BY posts.post_id DESC
        ''')
    posts = cursor.fetchall()
    close_db()
    return posts

def get_post_by_id(post_id):
    open_db()
    cursor.execute('''
        SELECT posts.*, categories.category_name 
        FROM posts 
        JOIN categories ON posts.category_id = categories.category_id
        WHERE posts.post_id = ?
    ''', [post_id])
    post = cursor.fetchone()
    close_db()
    return post

def get_post_images(post_id):
    open_db()
    cursor.execute('SELECT * FROM post_images WHERE post_id = ? ORDER BY is_main DESC, image_id ASC', [post_id])
    images = cursor.fetchall()
    close_db()
    return images

def add_comment(post_id, user_name, text):
    open_db()
    execute('INSERT INTO comments (post_id, user_name, text) VALUES (?, ?, ?)', [post_id, user_name, text])
    close_db()

def get_comments(post_id):
    open_db()
    cursor.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY comment_id DESC', [post_id])
    comments = cursor.fetchall()
    close_db()
    return comments

def delete_comment(comment_id):
    open_db()
    execute('DELETE FROM comments WHERE comment_id = ?', [comment_id])
    close_db()

def get_user_by_id(user_id):
    open_db()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', [user_id])
    user = cursor.fetchone()
    close_db()
    return user

def update_user_profile(user_id, name, description_short, description, image=None):
    open_db()
    if image:
        execute('''
            UPDATE users 
            SET name = ?, description_short = ?, description = ?, image = ? 
            WHERE user_id = ?
        ''', [name, description_short, description, image, user_id])
    else:
        execute('''
            UPDATE users 
            SET name = ?, description_short = ?, description =? 
            WHERE user_id = ?
        ''', [name, description_short, description, user_id])
    close_db()

def toggle_like(user_id, post_id):
    open_db()
    cursor.execute('SELECT like_id FROM likes WHERE user_id = ? AND post_id = ?', [user_id, post_id])
    like = cursor.fetchone()
    if like:
        execute('DELETE FROM likes WHERE user_id = ? AND post_id = ?', [user_id, post_id])
    else:
        execute('INSERT INTO likes (user_id, post_id) VALUES (?, ?)', [user_id, post_id])
    close_db()

def get_post_likes_count(post_id):
    open_db()
    cursor.execute('SELECT COUNT(*) as count FROM likes WHERE post_id = ?', [post_id])
    result = cursor.fetchone()
    close_db()
    return result['count'] if result else 0

def check_user_liked(user_id, post_id):
    open_db()
    cursor.execute('SELECT like_id FROM likes WHERE user_id = ? AND post_id = ?', [user_id, post_id])
    liked = cursor.fetchone()
    close_db()
    return True if liked else False

def update_comment(comment_id, text):
    open_db()
    execute('UPDATE comments SET text = ? WHERE comment_id = ?', [text, comment_id])
    close_db()

def get_comment_by_id(comment_id):
    open_db()
    cursor.execute('SELECT * FROM comments WHERE comment_id = ?', [comment_id])
    comment = cursor.fetchone()
    close_db()
    return comment

if __name__ == "__main__":
    create_tables()