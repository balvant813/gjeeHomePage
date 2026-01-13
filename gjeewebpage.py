# gjeewebpage.py - Balvant Patel's Photo Albums Portal
from flask import Flask, render_template, request, redirect, url_for, session, flash
import pyodbc
from werkzeug.security import generate_password_hash, check_password_hash
import os, sys
from flask_bootstrap import Bootstrap
from datetime import datetime, timedelta, timezone
from flask import jsonify
import random
import time

app = Flask(__name__)
app.secret_key = 'qkjfGTTT#ASUT78n45_813'  # CHANGE THIS IN PRODUCTION!
app.jinja_env.filters['strftime'] = lambda dt, fmt: datetime.now().strftime(fmt)

# Application Version
# appVer = 'v2026.1.3'  # Clickable cards + header thumbnail
# appVer = 'v2026.1.4'  # Account deletion enhancement, and password reveal toggle
appVer = 'v2026.1.5'  # Azure SQL Database connection enhancement, and logout on inactivity added
Bootstrap(app)

@app.before_request
def check_inactivity():
    if 'username' in session and request.endpoint not in ['login', 'logout', 'static']:
        if 'last_activity' in session:
            if datetime.now(timezone.utc) - session['last_activity'] > timedelta(minutes=15):
                session.pop('username', None)
                flash('You have been logged out due to inactivity.', 'info')
                return redirect(url_for('login'))
        session['last_activity'] = datetime.now(timezone.utc)

# Azure SQL Database connection
DRIVER = os.getenv('ODBC_DRIVER')
if not DRIVER:
    print("ODBC_DRIVER environment variable not set - exiting", file=sys.stderr)
    sys.exit(1)

SERVER = os.getenv('ODBC_SERVER')
DATABASE = os.getenv('ODBC_DATABASE')
USERNAME = os.getenv('ODBC_UID')
PASSWORD = os.getenv('ODBC_PWD')
albumTable = os.getenv('ALBUM_TABLE', 'album_list')
userTable = 'album_users'
timeOutLimit = int(os.getenv('ODBC_TIMEOUT') or 60)

CONNECTION_STRING = (
    f'DRIVER={DRIVER};'
    f'SERVER=tcp:{SERVER},1433;'
    f'DATABASE={DATABASE};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    f'Encrypt=yes;TrustServerCertificate=no;Connection Timeout={timeOutLimit};'
)

def get_db_connection(retries=3):
    for attempt in range(retries):
        try:
            return pyodbc.connect(CONNECTION_STRING)
        except pyodbc.OperationalError as e:
            if "timeout" in str(e).lower() and attempt < retries - 1:
                time.sleep(1)
                continue
            else:
                raise

# Shared function for main data (curated + categories)
def get_main_data():
    conn = get_db_connection()
    cursor = conn.cursor()

    curated_groups = {}

    # Featured (manual)
    cursor.execute(f"""
        SELECT TOP (4) id, album_name, endpoint, thumbnail_url
        FROM [{albumTable}]
        WHERE tab_name = 'Categories'
        ORDER BY row_num, col_num
    """)
    row1 = cursor.fetchall()
    curated_groups[1] = [(a[0], a[1], a[2], a[3], 1, idx+1) for idx, a in enumerate(row1)]

    def get_top_4(cat, row):
        cursor.execute(f"""
            SELECT TOP (4) id, album_name, endpoint, thumbnail_url
            FROM [{albumTable}]
            WHERE tab_name = 'All' AND category = ?
            ORDER BY CASE WHEN oldest_photo_date IS NULL THEN 1 ELSE 0 END ASC,
                     oldest_photo_date DESC, album_name ASC
        """, (cat,))
        albums = cursor.fetchall()
        return [(a[0], a[1], a[2], a[3], row, idx+1) for idx, a in enumerate(albums)]

    curated_groups[2] = get_top_4('Family', 2)
    curated_groups[3] = get_top_4('Travel', 3)
    curated_groups[4] = get_top_4('Friends', 4)
    curated_groups[5] = get_top_4('Hobby', 5)

    # Category tabs
    valid_categories = ['Family', 'Travel', 'Hobby', 'Friends']
    category_groups = {}
    category_album_counts = {}

    for cat in valid_categories:
        cursor.execute(f"""
            SELECT id, album_name, endpoint, thumbnail_url
            FROM [{albumTable}]
            WHERE tab_name = 'All' AND category = ?
            ORDER BY CASE WHEN oldest_photo_date IS NULL THEN 1 ELSE 0 END ASC,
                     oldest_photo_date DESC, album_name ASC
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

    return {
        'curated_groups': curated_groups,
        'category_titles': category_titles,
        'category_groups': category_groups,
        'category_album_counts': category_album_counts,
        'valid_categories': valid_categories
    }
# Random album thumbnails for header (now returns name + url)
@app.route('/random_album_thumbs')
def random_album_thumbs():
    if 'username' not in session:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT album_name, thumbnail_url, endpoint FROM [{albumTable}] WHERE thumbnail_url IS NOT NULL AND thumbnail_url != '' AND tab_name = 'All'")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    items = [{"name": row[0], "url": row[1], "endpoint": row[2]} for row in rows]
    random.shuffle(items)
    return jsonify(items[:20])

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('main'))
    else:
        return redirect(url_for('login'))
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_failed = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question FROM family_QA")
        questions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database connection error: {e}", file=sys.stderr)
        flash("Database connection error. Please try again later.", "danger")
        return render_template('login.html', questions=[], login_failed=False)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Get real client IP (handles Azure proxy)
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            client_ip = request.remote_addr or 'Unknown'

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT password_hash, last_login_time, last_login_ip FROM [{userTable}] WHERE username = ?", username)
        user = cursor.fetchone()

        if user and check_password_hash(user[0], password):
            session['username'] = username

            # Update last login
            cursor.execute(f"""
                UPDATE [{userTable}] 
                SET last_login_time = GETDATE(), last_login_ip = ?
                WHERE username = ?
            """, (client_ip, username))
            conn.commit()

            cursor.close()
            conn.close()

            return redirect(url_for('main'))
        else:
            login_failed = True
            flash('Invalid username or password', 'danger')

    return render_template('login.html', questions=questions, login_failed=login_failed)

@app.route('/main')
def main():
    if 'username' not in session:
        return redirect(url_for('login'))

    data = get_main_data()
    query = request.args.get('q', '').strip()
    year_input = request.args.get('year', '').strip()
    is_search = bool(query or year_input)

    search_results = None
    sorted_years = None
    total_results = 0
    search_query = query
    search_year = year_input

    if is_search:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = f"SELECT album_name, endpoint, thumbnail_url, oldest_photo_date FROM [{albumTable}] WHERE tab_name = 'All'"
        params = []

        if query:
            sql += " AND album_name LIKE ?"
            params.append(f"%{query}%")

        year_conditions = []
        year_params = []

        if year_input:
            parts = [p.strip() for p in year_input.split(',')]
            for part in parts:
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        if start <= end:
                            year_conditions.append("(YEAR(oldest_photo_date) BETWEEN ? AND ?)")
                            year_params.extend([start, end])
                    except:
                        flash(f"Invalid range: {part}", "danger")
                else:
                    try:
                        y = int(part)
                        year_conditions.append("YEAR(oldest_photo_date) = ?")
                        year_params.append(y)
                    except:
                        flash(f"Invalid year: {part}", "danger")

        if year_conditions:
            sql += " AND (" + " OR ".join(year_conditions) + ")"
            params.extend(year_params)

        if query or year_conditions:
            sql += " ORDER BY oldest_photo_date DESC, album_name"
            cursor.execute(sql, params)
            results = cursor.fetchall()

            results_by_year = {}
            for row in results:
                name, endpoint, thumb, date = row
                y = date.year if date else "Unknown"
                results_by_year.setdefault(y, []).append((name, endpoint, thumb))

            sorted_years = sorted(results_by_year.keys(), reverse=True)
            total_results = sum(len(v) for v in results_by_year.values())
            search_results = results_by_year if results else None

            if not results:
                flash("No albums found.", "info")

        cursor.close()
        conn.close()
    # Get last login info for current user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT last_login_time, last_login_ip FROM [{userTable}] WHERE username = ?", session['username'])
    login_info = cursor.fetchone()
    cursor.close()
    conn.close()

    last_login_str = ""
    if login_info and login_info[0]:
        dt = login_info[0]
        ip = login_info[1] or "unknown IP"
        last_login_str = f"Last login: {dt.strftime('%b %d, %Y at %I:%M %p')} from {ip}"
    return render_template('main.html',
                           categories_groups=data['curated_groups'],
                           category_titles=data['category_titles'],
                           category_groups=data['category_groups'],
                           category_album_counts=data['category_album_counts'],
                           valid_categories=data['valid_categories'],
                           last_login_str=last_login_str,
                           appVer=appVer,
                           search_results=search_results,
                           sorted_years=sorted_years,
                           total_results=total_results,
                           search_query=search_query,
                           search_year=search_year,
                           is_search=is_search)
    
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

    # Existing validations
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

    # NEW: Check if password is in hint (case-insensitive)
    if password.lower() in hint.lower():
        flash("Warning: Your hint contained your password. It has been automatically shortened for security.", "warning")
        hint = hint[:4]  # Truncate to first 4 characters

    if errors:
        for err in errors:
            flash(err, 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM family_QA WHERE question = ?", question)
    result = cursor.fetchone()

    if result and result[0].lower() == answer.lower():
        try:
            hashed = generate_password_hash(password)
            cursor.execute(f"""
                INSERT INTO [{userTable}] 
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

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
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
            cursor.execute(f"SELECT password_hint FROM [{userTable}] WHERE username = ?", (username,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result and result[0]:
                hint = result[0]
            else:
                error = "No hint found for that username (or user doesn't exist)."

    return render_template('forgot_password.html', hint=hint, username=username, error=error)

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
            # Prepare the first 3 chars (safe even if input is shorter than 3)
            city_prefix = city[:3]
            state_prefix = state[:3]

            conn = get_db_connection()
            cursor = conn.cursor()

            # Compare first 3 lowercase characters for city and state
            cursor.execute(f"""
                SELECT username 
                FROM [{userTable}] 
                WHERE LOWER(username) = ? 
                  AND LOWER(LEFT(city, 3)) = ? 
                  AND LOWER(LEFT(state, 3)) = ?
            """, (username, city_prefix, state_prefix))

            user = cursor.fetchone()

            if user:
                # Optional: Log the deletion attempt (good practice)
                # cursor.execute("INSERT INTO deletion_log (username, deleted_at) VALUES (?, GETDATE())", (username,))
                # conn.commit()

                cursor.execute(f"DELETE FROM [{userTable}] WHERE LOWER(username) = ?", (username,))
                conn.commit()
                success = True
                flash('Your account has been successfully deleted.', 'success')
            else:
                error = "No matching account found. Please check your details (city/state are matched using first 3 letters)."

            cursor.close()
            conn.close()

    return render_template('delete_account.html', error=error, success=success)

@app.route('/gradient-generator')
def gradient_generator():
    """CSS Gradient Generator - Create custom gradients with live preview"""
    return render_template('gradient_generator.html')

if __name__ == '__main__':
    app.run(host='127.0.0.2', port=5000, debug=False)