from flask import Flask, render_template, request, session, redirect, url_for, flash
from werkzeug.exceptions import abort
import base64
import sqlite3
import os
import hashlib

app = Flask(__name__)
app.secret_key = 'yourmom'  # your mom

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_pathpost = os.path.join(BASE_DIR, 'db', 'databasepost.db')
db_pathusers = os.path.join(BASE_DIR, 'db', 'databaseusers.db')
Error = None


@app.template_filter('b64encode')
def b64encode_filter(data):
    return base64.b64encode(data).decode('utf-8')


#BUFER for situation, if something goes wrong
# @app.route("/")
# def mainpage():
#     posts=[]
#     with sqlite3.connect(db_pathusers) as db:
#         conn = sqlite3.connect(db_pathpost)
#         conn.row_factory = sqlite3.Row
#         posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()  # Сортируем посты по id в порядке убывания
#         conn.close()
#         if 'user_id' in session:
#             cursor = db.cursor()
#             cursor.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],))
#             user = cursor.fetchone()
#             if user:
#                 username = user[0]
#             return render_template("mainpage.html", username=username, posts=posts)
            
#     return render_template("mainpage.html", username=None, posts=posts)




@app.route("/")
def mainpage():
    posts = []
    conn = sqlite3.connect(db_pathpost)
    conn.row_factory = sqlite3.Row
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    conn.close()

    username = None
    profile_image = None
    if 'user_id' in session:
        conn = sqlite3.connect(db_pathusers)
        cursor = conn.cursor()
        cursor.execute("SELECT username, profile_image FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        if user:
            username = user[0]
            profile_image = user[1]  # Получаем аватар пользователя

    return render_template("mainpage.html", username=username, profile_image=profile_image, posts=posts)

# Маршрут для editposts
@app.route('/editposts')
def editposts():
    posts = []
    profile_image = None
    username = None
    uniq_id = None

    if 'user_id' in session:
        conn = sqlite3.connect(db_pathusers)
        cursor = conn.cursor()
        cursor.execute("SELECT username, profile_image, uniq_id FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()

        if user:
            username = user[0]
            profile_image = user[1]  # Получаем аватар пользователя
            uniq_id = user[2]       # Получаем uniq_id пользователя

    if uniq_id:
        conn = sqlite3.connect(db_pathpost)
        conn.row_factory = sqlite3.Row
        posts = conn.execute(
            'SELECT * FROM posts WHERE user_uniq_id = ? ORDER BY id DESC', 
            (uniq_id,)
        ).fetchall()  # Выбираем только посты текущего пользователя
        conn.close()

    return render_template('editposts.html', posts=posts, username=username, profile_image=profile_image, uniq_id=uniq_id)


# @app.route('/profile')
# def profile():
#     if 'user_id' in session:
#         with sqlite3.connect(db_pathusers) as db:
#             cursor = db.cursor()
#             cursor.execute("SELECT username FROM users WHERE id = ?", (session['user_id'],))
#             user = cursor.fetchone()
#             if user:
#                 username = user[0]
#                 return render_template("profile.html", username=username)
#     return render_template("mainpage.html", username=None)

@app.route('/profile')
def profile():
    if 'user_id' in session:
        with sqlite3.connect(db_pathusers) as db:
            cursor = db.cursor()
            cursor.execute("SELECT username, profile_image FROM users WHERE id = ?", (session['user_id'],))
            user = cursor.fetchone()
            if user:
                username = user[0]
                profile_image = user[1] if user[1] else None  # Изображение профиля
                return render_template("profile.html", username=username, profile_image=profile_image)
    flash('User not logged in. Please login.')
    return redirect(url_for('login'))



#profile_update
@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'user_id' not in session:
        flash('User not logged in. Please login.')
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(db_pathusers)
    cursor = conn.cursor()
    cursor.execute("SELECT username, email FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()

    if not user:
        flash('User not found.')
        return redirect(url_for('profile'))

    username, email = user

    if request.method == 'POST':
        new_username = request.form.get('username', username)
        new_email = request.form.get('email', email)
        new_password = request.form.get('password')
        profile_image = request.files.get('profile_image')

        update_query = "UPDATE users SET username = ?, email = ?"
        params = [new_username, new_email]

        if new_password:
            update_query += ", password = ?"
            params.append(new_password)

        if profile_image:
            profile_image_data = profile_image.read()
            update_query += ", profile_image = ?"
            params.append(profile_image_data)

        update_query += " WHERE id = ?"
        params.append(session['user_id'])

        conn = sqlite3.connect(db_pathusers)
        conn.execute(update_query, params)
        conn.commit()
        conn.close()

        flash('Profile updated successfully!')
        return redirect(url_for('profile'))

    return render_template("update_profile.html", username=username, email=email)



def encrypt_username(username):
    return hashlib.sha256(username.encode()).hexdigest()



@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        uniq_id = encrypt_username(username)
        try:
            with sqlite3.connect(db_pathusers) as db:
                cursor = db.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                existing_user = cursor.fetchone()
                if existing_user:
                    return render_template('register.html', error=Error)
                cursor = db.cursor()
                query = """ INSERT INTO users (username, email, password, uniq_id) VALUES (?, ?, ?, ?) """
                cursor.execute(query, (username, email, password, uniq_id))
                db.commit()
                session['user_id'] = cursor.lastrowid

            return redirect(url_for('mainpage'))

        except sqlite3.IntegrityError:
            return "Ошибка: пользователь с таким email уже существует!"

    return render_template("register.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        try:
            with sqlite3.connect(db_pathusers) as db:
                cursor = db.cursor()
                cursor.execute("SELECT id, username FROM users WHERE email = ? AND password = ?", (email, password))
                user = cursor.fetchone()
                if user:
                    session['user_id'] = user[0]
                    username = user[1]
                    return redirect(url_for('mainpage', username=username))
                else:
                   return render_template("login.html", error=Error) 

        except sqlite3.IntegrityError:
            return "Ошибка: пользователь с таким email уже существует!"
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('mainpage'))

#getting post
def get_post(post_id):
    try:
        
        

        conn = sqlite3.connect(db_pathpost)
        conn.row_factory = sqlite3.Row
        post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
        conn.close()
        if post is None:
            abort(404)  # Пост не найден
        return post
    except sqlite3.Error as e:
        abort(500, description=f"Database error: {e}")




@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)  # Получаем пост по ID
    username = None
    profile_image = None
    if 'user_id' in session:
        conn = sqlite3.connect(db_pathusers)
        cursor = conn.cursor()
        cursor.execute("SELECT username, profile_image FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        if user:
            username = user[0]
            profile_image = user[1]  # Получаем аватар пользователя
    
    return render_template('post.html', post=post, username=username, profile_image=profile_image)
    



@app.route('/create', methods=('GET', 'POST'))
def create():
    # Проверяем, авторизован ли пользователь
    if 'user_id' not in session:
        flash('You must be logged in to create a post!')
        return redirect(url_for('login'))

    username = None
    uniq_id = None
    if 'user_id' in session:
        # Получаем имя пользователя и uniq_id из базы данных
        conn = sqlite3.connect(db_pathusers)
        cursor = conn.cursor()
        cursor.execute("SELECT username, uniq_id FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        if user:
            username = user[0]
            uniq_id = user[1]
    
    user_uniq_id = uniq_id
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_image = request.files['image']

        # Проверяем данные
        if not title:
            flash('Title is required!')
        elif not content:
            flash('Content is required!')
        else:
            # Преобразуем изображение в бинарные данные
            image_blob = post_image.read()

            # Сохраняем пост в базу данных
            conn = sqlite3.connect(db_pathpost)
            conn.execute(
                'INSERT INTO posts (title, content, user_uniq_id, post_image) VALUES (?, ?, ?, ?)',
                (title, content, user_uniq_id, image_blob)
            )
            conn.commit()
            conn.close()

            flash('Post created successfully!')
            return redirect(url_for('mainpage'))

    return render_template('create.html', username=username)




@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    # Get the post to be edited by its id
    post = get_post(id)

    if 'user_id' not in session:
        flash('You must be logged in to edit a post!')
        return redirect(url_for('login'))

    username = None
    conn1 = sqlite3.connect(db_pathusers)
    cg = conn1.cursor()
    cg.execute('SELECT uniq_id, username FROM users WHERE id = ?', (session['user_id'],))
    user1 = cg.fetchone()
    conn1.close()

    if user1:
        uniq_id = user1[0]
        username = user1[1]

    if user1:
        uniq_id = user1[0]

    conn = sqlite3.connect(db_pathpost)
    cursor = conn.cursor()
    cursor.execute('SELECT user_uniq_id FROM posts WHERE id = ?', (id, ))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_uniq_id = user[0]

    if uniq_id != user_uniq_id:
        flash('You do not have permission to edit this post!')
        return redirect(url_for('mainpage'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = sqlite3.connect(db_pathpost)
            # Update the table 
            conn.execute('UPDATE posts SET title = ?, content = ? WHERE id = ?', (title, content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('mainpage'))

    return render_template('edit.html', post=post, username=username)
    


@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    post = get_post(id)
    conn = sqlite3.connect(db_pathpost)
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('editposts'))




if __name__ == "__main__":
    app.run(debug=True, port=5501)
