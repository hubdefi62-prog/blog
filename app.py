from flask import Flask, render_template, request, redirect, url_for, session, abort
import sqlite3
from settings import PATH_DB
from db import (create_tables, get_categories, add_post, get_posts, 
                get_post_by_id, add_comment, get_comments, update_post, delete_post, delete_comment,
                get_user_by_id, update_user_profile,
                toggle_like, get_post_likes_count, check_user_liked, update_comment, get_comment_by_id,
                add_category, delete_category)
from auth import auth_bp, get_current_user

app = Flask(__name__)
app.secret_key = 'super-secret-key-change-me-in-production'

app.register_blueprint(auth_bp)
create_tables()

def get_admin_info():
    conn = sqlite3.connect(PATH_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE is_admin = 1 LIMIT 1')
    admin = cursor.fetchone()
    conn.close()
    return admin

@app.route('/', methods=['GET', 'POST'])
def index():
    user = get_current_user() 
    admin = get_admin_info()  

    if request.method == 'POST':
        if not user or user['is_admin'] != 1:
            abort(403)
            
        category_id = request.form.get('category_id')
        title = request.form.get('title')
        post_text = request.form.get('text')
        
        if category_id and post_text and title:
            add_post(int(category_id), post_text, title=title)
        return redirect(url_for('index'))

    selected_category = request.args.get('category_id', type=int)
    categories = get_categories()
    
    if selected_category:
        posts = get_posts(category_id=selected_category)
    else:
        posts = get_posts()

    return render_template('index.html', 
                           user=user, 
                           admin=admin, 
                           categories=categories, 
                           posts=posts, 
                           selected_category=selected_category)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post_detail(post_id):
    user = get_current_user()
    post = get_post_by_id(post_id)
    
    if not post:
        abort(404)

    if request.method == 'POST':
        comment_text = request.form.get('comment_text')
        if comment_text:
            author_name = user['name'] if user else "Анонімний гість"
            add_comment(post_id, author_name, comment_text)
        return redirect(url_for('post_detail', post_id=post_id))

    comments = get_comments(post_id)
    likes_count = get_post_likes_count(post_id)
    has_liked = check_user_liked(user['user_id'], post_id) if user else False

    return render_template('post_detail.html', 
                           user=user, 
                           post=post, 
                           comments=comments, 
                           likes_count=likes_count, 
                           has_liked=has_liked)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post_route(post_id):
    user = get_current_user()
    if not user or user['is_admin'] != 1:
        abort(403)
    delete_post(post_id)
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/edit', methods=['GET', 'POST'])
def edit_post(post_id):
    user = get_current_user()
    if not user or user['is_admin'] != 1:
        abort(403)
        
    post = get_post_by_id(post_id)
    if not post:
        abort(404)
        
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        title = request.form.get('title')
        post_text = request.form.get('text')
        
        if category_id and title and post_text:
            update_post(post_id, int(category_id), title, post_text)
            return redirect(url_for('post_detail', post_id=post_id))
            
    categories = get_categories()
    return render_template('edit_post.html', user=user, post=post, categories=categories)

@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment_route(comment_id):
    user = get_current_user()
    post_id = request.form.get('post_id')
    
    if not user or user['is_admin'] != 1:
        abort(403)
        
    delete_comment(comment_id)
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('auth_bp.login'))
        
    toggle_like(user['user_id'], post_id)
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/comment/<int:comment_id>/edit', methods=['GET', 'POST'])
def edit_comment_route(comment_id):
    user = get_current_user()
    comment = get_comment_by_id(comment_id)
    
    if not comment:
        abort(404)
        
    if not user or (user['name'] != comment['user_name'] and user['is_admin'] != 1):
        abort(403)
        
    if request.method == 'POST':
        new_text = request.form.get('comment_text')
        if new_text:
            update_comment(comment_id, new_text)
        return redirect(url_for('post_detail', post_id=comment['post_id']))
        
    return render_template('edit_comment.html', user=user, comment=comment)


@app.route('/admin/categories', methods=['GET', 'POST'])
def manage_categories():
    user = get_current_user()
    if not user or user['is_admin'] != 1:
        abort(403)
        
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        if category_name:
            add_category(category_name.strip())
        return redirect(url_for('manage_categories'))
        
    categories = get_categories()
    return render_template('manage_categories.html', user=user, categories=categories)

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
def delete_category_route(category_id):
    user = get_current_user()
    if not user or user['is_admin'] != 1:
        abort(403)
        
    delete_category(category_id)
    return redirect(url_for('manage_categories'))

@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = get_current_user()
    account = get_user_by_id(user_id)
    
    if not account:
        abort(404)
        
    return render_template('profile.html', user=user, account=account)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    user = get_current_user()
    if not user:
        return redirect(url_for('auth_bp.login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        description_short = request.form.get('description_short')
        description = request.form.get('description')
        image = request.form.get('image')
        
        update_user_profile(user['user_id'], name, description_short, description, image)
        session['user'] = dict(get_user_by_id(user['user_id']))
        
        return redirect(url_for('profile', user_id=user['user_id']))
        
    return render_template('settings.html', user=user)

@app.route('/about')
def about():
    user = get_current_user() 
    admin = get_admin_info()  
    return render_template('about.html', user=user, admin=admin)

if __name__ == '__main__':
    app.run(debug=True)