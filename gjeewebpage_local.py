import configparser
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'CHANGE_THIS_TO_SOMETHING_VERY_SECURE_813!'  # CHANGE THIS!

# Load credentials
config = configparser.ConfigParser()
config.read('credentials.ini')

db_config = {
    'host': config['mysql']['host'],
    'user': config['mysql']['user'],
    'password': config['mysql']['password'],
    'database': config['mysql']['database'],
    'port': int(config['mysql']['port'])
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Initialize DB tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS album_users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS family_QA (
            id INT AUTO_INCREMENT PRIMARY KEY,
            question VARCHAR(255) NOT NULL,
            answer VARCHAR(255) NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS album_list (
            id INT AUTO_INCREMENT PRIMARY KEY,
            album_name VARCHAR(255) NOT NULL,
            endpoint TEXT NOT NULL,
            thumbnail_url TEXT,
            tab_name VARCHAR(50) NOT NULL,
            row_num INT NOT NULL,
            col_num INT NOT NULL,
            created_at DATETIME NULL,
            oldest_photo_date DATETIME NULL,
            category VARCHAR(50) DEFAULT 'Family'
        )
    ''')
    
    # Add missing columns if needed
    try:
        cursor.execute("ALTER TABLE album_list ADD COLUMN category VARCHAR(50) DEFAULT 'Family'")
    except mysql.connector.Error:
        pass
    
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
        cursor.executemany("INSERT INTO family_QA (question, answer) VALUES (%s, %s)", sample_qa)

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
        cursor.execute("SELECT password_hash FROM album_users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[0], password):
            session['username'] = username
            return redirect(url_for('main'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html', questions=questions)

@app.route('/register', methods=['POST'])
def register():
    username = request.form['new_username'].strip()
    password = request.form['new_password']
    question = request.form['question']
    answer = request.form['answer'].strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM family_QA WHERE question = %s", (question,))
    result = cursor.fetchone()

    if result and result[0].lower() == answer:
        try:
            hashed = generate_password_hash(password)
            cursor.execute("INSERT INTO album_users (username, password_hash) VALUES (%s, %s)", (username, hashed))
            conn.commit()
            flash('Account created! You can now log in.', 'success')
        except mysql.connector.IntegrityError:
            flash('Username already taken.', 'danger')
    else:
        flash('Wrong answer to security question.', 'danger')

    cursor.close()
    conn.close()
    return redirect(url_for('login'))

@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # === New Curated Categories Tab ===
    curated_groups = {}  # row_num → list of albums (tuples)

    # Row 1: Manual featured albums (from tab_name = 'Categories')
    cursor.execute("""
        SELECT id, album_name, endpoint, thumbnail_url
        FROM album_list
        WHERE tab_name = 'Categories'
        ORDER BY row_num, col_num
        LIMIT 4
    """)
    row1_albums = cursor.fetchall()
    # Add row_num and col_num manually
    row1_with_pos = [(album[0], album[1], album[2], album[3], 1, idx+1) for idx, album in enumerate(row1_albums)]
    curated_groups[1] = row1_with_pos

    # Helper: Get top 4 latest albums from a category
    def get_top_4_from_category(category, row_num):
        cursor.execute("""
            SELECT id, album_name, endpoint, thumbnail_url
            FROM album_list
            WHERE tab_name = 'All' AND category = %s
            ORDER BY 
                CASE WHEN oldest_photo_date IS NULL THEN 1 ELSE 0 END ASC,  -- NULLs last
                oldest_photo_date DESC,                                      -- Latest photos first
                album_name ASC
            LIMIT 4
        """, (category,))
        albums = cursor.fetchall()
        # Add row_num and col_num (1 to 4)
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
        cursor.execute("""
            SELECT id, album_name, endpoint, thumbnail_url, row_num, col_num
            FROM album_list
            WHERE tab_name = 'All' AND category = %s
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