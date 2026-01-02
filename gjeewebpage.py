# import configparser
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import os, sys
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.secret_key = 'qkjfGTTT#ASUT78n45_813'  # Replace with a secure key in production
# config = configparser.ConfigParser()
# config.read(os.path.join(os.getcwd(),'./other/credentials.ini'))

Bootstrap(app)

# Azure SQL Database connection string
# Get this from Azure Portal → Your SQL Database → Connection strings → Python (pyodbc)
# Prefer environment variables for production; fallback to credentials.ini for local dev
# DRIVER = os.getenv('ODBC_DRIVER', config.get('ODBC', 'Driver', fallback='{ODBC Driver 18 for SQL Server}'))
# DRIVER = os.getenv('ODBC_DRIVER', config.get('ODBC', 'Driver'))
DRIVER = os.getenv('ODBC_DRIVER')
if not DRIVER:
    exception_msg = f"ODBC_DRIVER environment variable not set. Using value from credentials.ini: {DRIVER}"
    print(exception_msg, file=sys.stderr)
    exit(1)
SERVER = os.getenv('ODBC_SERVER')
DATABASE = os.getenv('ODBC_DATABASE')

USERNAME = os.getenv('ODBC_UID')
PASSWORD = os.getenv('ODBC_PWD')
albumTable = os.getenv('ALBUM_TABLE')
timeOutLimit = int(os.getenv('ODBC_TIMEOUT') or 60)
userTable = 'album_users'
qaTable = 'family_QA'
# SERVER = 'mangonallc.database.windows.net'  
# DRIVER = '{ODBC Driver 18 for SQL Server}'
# DATABASE = 'bp_records'
# USERNAME = 'webadmin813'
# PASSWORD = '#MangonaDB!813'
# albumTable = 'album_list'
# timeOutLimit = 60
# port = 1433
CONNECTION_STRING = f'DRIVER={DRIVER};SERVER=tcp:{SERVER},1433;DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}; \
        Encrypt=yes;TrustServerCertificate=no;Connection Timeout={timeOutLimit};'

def get_db_connection():
    return pyodbc.connect(CONNECTION_STRING)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Updated album_users table with new fields
    cursor.execute(f'''
        IF OBJECT_ID('{userTable}', 'U') IS NULL
        CREATE TABLE {userTable} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) UNIQUE NOT NULL,
            password_hash NVARCHAR(255) NOT NULL,
            password_hint NVARCHAR(255) NOT NULL,
            city NVARCHAR(100) NOT NULL,
            state NVARCHAR(100) NOT NULL,
            country NVARCHAR(100) NOT NULL
        )
    ''')
    
    # Add new columns if table already exists
    columns_to_add = ['password_hint', 'city', 'state', 'country']
    for col in columns_to_add:
        cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                           WHERE TABLE_NAME = '{userTable}' AND COLUMN_NAME = '{col}')
            BEGIN
                ALTER TABLE {userTable} ADD {col} NVARCHAR(100) NOT NULL DEFAULT ''
            END
        """)
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()
# Update /register route with full validation
@app.route('/register', methods=['POST'])
def register():
    username = request.form['new_username'].strip()
    password = request.form['new_password']
    hint = request.form['password_hint'].strip()
    city = request.form['city'].strip()
    state = request.form['state'].strip()
    country = request.form['country'].strip()
    question = request.form['question']
    answer = request.form['answer'].strip().lower()

    errors = []

    # Validation rules
    if len(username) < 6:
        errors.append("Username must be at least 6 characters.")
    if len(password) < 6:
        errors.append("Password must be at least 6 characters.")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character.")
    if len(hint) <= 3:
        errors.append("Password hint must be more than 3 characters.")
    if len(city) <= 3:
        errors.append("City must be more than 3 characters.")
    if len(state) <= 3:
        errors.append("State must be more than 3 characters.")
    if len(country) < 2:
        errors.append("Country must be at least 2 characters.")

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT answer FROM {qaTable} WHERE question = ?", question)
    result = cursor.fetchone()

    if result and result[0].lower() == answer:
        try:
            hashed = generate_password_hash(password)
            if hint == password:
                flash('Password hint cannot be the same as the password. Truncated to first 3 chars', 'danger')
                hint = password[:3]
            cursor.execute(f"""
                INSERT INTO {userTable} 
                (username, password_hash, password_hint, city, state, country) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (username, hashed, hint, city, state, country))
            conn.commit()
            flash('Account created successfully! You can now log in.', 'success')
        except pyodbc.IntegrityError:
            flash('Username already taken.', 'danger')
    else:
        flash('Wrong answer to security question.', 'danger')

    cursor.close()
    conn.close()
    return redirect(url_for('login'))
@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    error = None
    success = False

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        city = request.form.get('city', '').strip().lower()
        state = request.form.get('state', '').strip().lower()

        if not all([username, city, state]):
            error = "All fields are required."
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT username FROM {userTable} 
                WHERE LOWER(username) = ? 
                  AND LOWER(city) = ? 
                  AND LOWER(state) = ?
            """, (username, city, state))
            user = cursor.fetchone()
            
            if user:
                cursor.execute(f"DELETE FROM {userTable} WHERE LOWER(username) = ?", (username,))
                conn.commit()
                success = True
            else:
                error = "No matching account found with provided details."
            
            cursor.close()
            conn.close()

    return render_template('delete_account.html', error=error, success=success)
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('main'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    login_failed = False
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT question FROM {qaTable}")
    questions = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT password_hash FROM {userTable} WHERE username = ?", username)
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['username'] = username
            return redirect(url_for('main'))
        else:
            login_failed = True
            flash('Invalid username or password', 'danger')

    return render_template('login.html', questions=questions, login_failed=login_failed)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    hint = None
    username = None
    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        if not username:
            error = "Please enter a username."
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT password_hint FROM {userTable} WHERE username = ?", (username,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result and result[0]:
                hint = result[0]
            else:
                error = "No hint found for that username (or user doesn't exist)."

    return render_template('forgot_password.html', hint=hint, username=username, error=error)

@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # === New Curated Categories Tab ===
    curated_groups = {}  # row_num → list of albums (tuples)

    # Row 1: Manual featured albums (from tab_name = 'Categories')
    cursor.execute(f"""
        SELECT TOP (4) id, album_name, endpoint, thumbnail_url
        FROM [{albumTable}]
        WHERE tab_name = 'Categories'
        ORDER BY row_num, col_num
    """)
    row1_albums = cursor.fetchall()
    # Add row_num and col_num manually
    row1_with_pos = [(album[0], album[1], album[2], album[3], 1, idx+1) for idx, album in enumerate(row1_albums)]
    curated_groups[1] = row1_with_pos

    # Helper: Get top 4 latest albums from a category
    def get_top_4_from_category(category, row_num):
        cursor.execute(f"""
            SELECT TOP (4) id, album_name, endpoint, thumbnail_url
            FROM [{albumTable}]
            WHERE tab_name = 'All' AND category = ?
            ORDER BY 
                CASE WHEN oldest_photo_date IS NULL THEN 1 ELSE 0 END ASC,
                oldest_photo_date DESC,
                album_name ASC
        """, (category,))
        albums = cursor.fetchall()
        return [(album[0], album[1], album[2], album[3], row_num, idx+1) for idx, album in enumerate(albums)]

    # Row 2: Family
    curated_groups[2] = get_top_4_from_category('Family', 2)

    # Row 3: Travel
    curated_groups[3] = get_top_4_from_category('Travel', 3)

    # Row 4: Friends
    curated_groups[4] = get_top_4_from_category('Friends', 4)

    # Row 5: Hobby
    curated_groups[5] = get_top_4_from_category('Hobby', 5)

    # === Dynamic Category Tabs (Family, Travel, Hobby, Friends) ===
    valid_categories = ['Family', 'Travel', 'Hobby', 'Friends']
    
    category_groups = {}
    category_album_counts = {}
    
    for cat in valid_categories:
        cursor.execute(f"""
            SELECT id, album_name, endpoint, thumbnail_url, row_num, col_num
            FROM [{albumTable}]
            WHERE tab_name = 'All' AND category = ?
            ORDER BY 
                CASE WHEN oldest_photo_date IS NULL THEN 1 ELSE 0 END ASC,
                oldest_photo_date DESC,
                album_name ASC
        """, (cat,))
        albums = cursor.fetchall()
        
        if albums:
            groups = []
            row = []
            for album in albums:
                row.append(album)
                if len(row) == 4:
                    groups.append(row)
                    row = []
            if row:
                groups.append(row)
            
            category_groups[cat] = groups
            category_album_counts[cat] = len(albums)

    cursor.close()
    conn.close()

    category_titles = {
        1: 'Featured Albums',
        2: 'Recent Family Moments',
        3: 'Latest Travel Adventures',
        4: 'Friends & Gatherings',
        5: 'Hobby Highlights'
    }

    return render_template('main.html',
                           categories_groups=curated_groups,
                           category_titles=category_titles,
                           category_groups=category_groups,
                           category_album_counts=category_album_counts,
                           valid_categories=valid_categories)
    
@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='127.0.0.2', port=5000, debug=False)