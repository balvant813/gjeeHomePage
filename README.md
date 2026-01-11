# Balvant Patel's Photo Albums Portal

A Flask-based web application for managing and viewing personal photo albums. This portal allows authenticated users to browse categorized photo albums (Family, Travel, Hobby, Friends), search by album name or year, and includes additional features like password recovery.

## Features

- **User Authentication**: Secure login, registration, and account management
- **Album Categories**: Organized albums into Family, Travel, Hobby, and Friends
- **Search Functionality**: Search albums by name or year range
- **Curated Sections**: Featured albums and recent highlights
- **Password Recovery**: Forgot password with security questions
- **Account Deletion**: Secure account removal process
- **Responsive Design**: Bootstrap-based UI with custom styling

## Technology Stack

- **Backend**: Python Flask
- **Database**: Azure SQL Database (via pyodbc)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Authentication**: Werkzeug security
- **Deployment**: Gunicorn (Procfile included)

## Project Structure

```
GjeeHomePage/
├── .gitignore
├── gjeewebpage.py              # Main Flask application
├── gjeewebpage_local.py        # Local development version
├── Procfile                    # Heroku deployment config
├── requirements.txt            # Python dependencies
├── startup.txt                 # Startup instructions
├── static/                     # Static assets
│   ├── css/
│   ├── js/
│   └── [image files]           # Background images and thumbnails
└── templates/                  # Jinja2 templates
    ├── delete_account.html
    ├── forgot_password.html
    ├── login.html
    └── main.html
```

## Setup and Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/balvant813/gjeeHomePage.git
    cd gjeeHomePage
    ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   Create a `.env` file or set environment variables for database connection:
   - `ODBC_DRIVER`: ODBC driver name
   - `ODBC_SERVER`: Azure SQL server
   - `ODBC_DATABASE`: Database name
   - `ODBC_UID`: Username
   - `ODBC_PWD`: Password
   - `ALBUM_TABLE`: Album table name (default: 'album_list')
   - `ODBC_TIMEOUT`: Connection timeout (default: 60)

5. **Run the application**:
   ```bash
   python gjeewebpage.py
   ```
   Or for local development:
   ```bash
   python gjeewebpage_local.py
   ```

6. **Access the application**:
   Open http://127.0.0.2:5000 in your browser

## Database Schema

The application expects the following tables in Azure SQL Database:
- `album_list`: Contains album metadata (id, album_name, endpoint, thumbnail_url, category, tab_name, oldest_photo_date)
- `album_users`: User accounts (username, password_hash, password_hint, city, state, country, last_login_time, last_login_ip)
- `family_QA`: Security questions for registration

## Deployment

This application is configured for deployment on Heroku with the included Procfile. Ensure all environment variables are set in your Heroku app settings.

## Security Features

- Password hashing with Werkzeug
- IP address logging for security
- Secure account deletion process
- Environment variable-based configuration
- No sensitive data in version control

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is private and intended for personal/family use only. All content is protected under copyright.

## Version

Current version: v2026.1.4

---

**Content Protection Notice**: All photographs and media on this website are the private property of Balvant Patel and/or Mangona LLC, USA. These materials are shared exclusively for personal, non-commercial viewing by family members and invited guests. Any reproduction, distribution, public display, or use for commercial purposes is strictly prohibited without explicit written permission.