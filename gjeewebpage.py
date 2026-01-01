import configparser
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import os, sys
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.secret_key = 'qkjfGTTT#ASUT78n45_813'  # Replace with a secure key in production
config = configparser.ConfigParser()
config.read(os.path.join(os.getcwd(),'credentials.ini'))

Bootstrap(app)

# Azure SQL Database connection string
# Get this from Azure Portal → Your SQL Database → Connection strings → Python (pyodbc)
# Prefer environment variables for production; fallback to credentials.ini for local dev
# DRIVER = os.getenv('ODBC_DRIVER', config.get('ODBC', 'Driver', fallback='{ODBC Driver 18 for SQL Server}'))
# DRIVER = os.getenv('ODBC_DRIVER', config.get('ODBC', 'Driver'))
DRIVER = os.getenv('ODBC_DRIVER')
if not DRIVER:
    DRIVER = config.get('ODBC', 'Driver')
    exception_msg = f"ODBC_DRIVER environment variable not set. Using value from credentials.ini: {DRIVER}"
    print(exception_msg, file=sys.stderr)
    exit(1)
SERVER = os.getenv('ODBC_SERVER', config.get('ODBC', 'Server'))
DATABASE = os.getenv('ODBC_DATABASE', config.get('ODBC', 'Database'))
USERNAME = os.getenv('ODBC_UID', config.get('ODBC', 'Uid'))
PASSWORD = os.getenv('ODBC_PWD', config.get('ODBC', 'Pwd'))
albumTable = os.getenv('ALBUM_TABLE', config.get('ODBC', 'albumTable'))
timeOutLimit = int(os.getenv('ODBC_TIMEOUT', config.get('ODBC', 'timeOutLimit', fallback='60')))

# SERVER = 'mangonallc.database.windows.net'  
# DRIVER = '{ODBC Driver 18 for SQL Server}'
# DATABASE = 'bp_records'
# USERNAME = 'webadmin813'
# PASSWORD = '#MangonaDB!813'
# albumTable = 'album_list'
# timeOutLimit = 60
port = 1433
CONNECTION_STRING = f'DRIVER={DRIVER};SERVER=tcp:{SERVER},1433;DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}; \
        Encrypt=yes;TrustServerCertificate=no;Connection Timeout={timeOutLimit};'

def get_db_connection():
    return pyodbc.connect(CONNECTION_STRING)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table with password_hint
    cursor.execute('''
        IF OBJECT_ID('album_users', 'U') IS NULL
        CREATE TABLE album_users (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) UNIQUE NOT NULL,
            password_hash NVARCHAR(255) NOT NULL,
            password_hint NVARCHAR(255) NULL
        )
    ''')
    
    # Add password_hint if not exists
    cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'album_users' AND COLUMN_NAME = 'password_hint'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("ALTER TABLE album_users ADD password_hint NVARCHAR(255) NULL")
    
    # Family Q&A
    cursor.execute('''
        IF OBJECT_ID('family_QA', 'U') IS NULL
        CREATE TABLE family_QA (
            id INT IDENTITY(1,1) PRIMARY KEY,
            question NVARCHAR(255) NOT NULL,
            answer NVARCHAR(255) NOT NULL
        )
    ''')
    
    # Album list
    cursor.execute('''
        IF OBJECT_ID('album_list', 'U') IS NULL
        CREATE TABLE album_list (
            id INT IDENTITY(1,1) PRIMARY KEY,
            album_name NVARCHAR(255) NOT NULL,
            endpoint NVARCHAR(MAX) NOT NULL,
            thumbnail_url NVARCHAR(MAX),
            tab_name NVARCHAR(50) NOT NULL,
            row_num INT NOT NULL,
            col_num INT NOT NULL,
            created_at DATETIME NULL,
            oldest_photo_date DATETIME NULL,
            category NVARCHAR(50) DEFAULT 'Family'
        )
    ''')
    
    # Sample questions
    cursor.execute("SELECT COUNT(*) FROM family_QA")
    if cursor.fetchone()[0] == 0:
        sample_qa = [
            ('What is your favorite color?', 'blue'),
            ('What is the name of your first pet?', 'fluffy'),
            ('Where were you born?', 'city'),
            ('What is your mother\'s maiden name?', 'patel'),
            ('What was your first car?', 'honda')
        ]
        cursor.executemany("INSERT INTO family_QA (question, answer) VALUES (?, ?)", sample_qa)
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()

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
    cursor.execute("SELECT question FROM family_QA")
    questions = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM album_users WHERE username = ?", username)
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

@app.route('/register', methods=['POST'])
def register():
    username = request.form['new_username'].strip()
    password = request.form['new_password']
    hint = request.form['password_hint'].strip()  # New required hint
    question = request.form['question']
    answer = request.form['answer'].strip().lower()

    if not hint:
        flash('Password hint is required.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM family_QA WHERE question = ?", question)
    result = cursor.fetchone()

    if result and result[0].lower() == answer:
        try:
            hashed = generate_password_hash(password)
            cursor.execute("INSERT INTO album_users (username, password_hash, password_hint) VALUES (?, ?, ?)", (username, hashed, hint))
            conn.commit()
            flash('Account created! You can now log in.', 'success')
        except pyodbc.IntegrityError:
            flash('Username already taken.', 'danger')
    else:
        flash('Wrong answer to security question.', 'danger')

    cursor.close()
    conn.close()
    return redirect(url_for('login'))

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
            cursor.execute("SELECT password_hint FROM album_users WHERE username = ?", (username,))
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