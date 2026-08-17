# Inwentaryzacja

Simple Django inventory management application for tracking assets, users, and assignments.

## Features

- Secure login/logout flow with Django authentication
- Asset list with search by tag, serial number, manufacturer, model, category, and user
- Asset detail view
- User list and user detail view
- Asset creation form
- Responsive admin-style interface

## Tech stack

- Python 3.11+
- Django 5.2.4
- SQLite database

## Project structure

- `inwentaryzacja/` – Django project configuration
- `assets/` – inventory application logic, templates, and static files
- `db.sqlite3` – local development database

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

4. Create a default admin account:

   ```bash
   python manage.py seed_admin
   ```

   Default credentials:
   - Username: `admin`
   - Password: `admin123`

5. Run the app:

   ```bash
   python manage.py runserver
   ```

6. Open the application in a browser:
   - Login page: `http://127.0.0.1:8000/accounts/login/`
   - Inventory list: `http://127.0.0.1:8000/assets/`

## Default login

Use the seeded admin account to access the application:

- Username: `admin`
- Password: `admin123`

## Notes

- The main entry point redirects to the inventory list after login.
- Search works across tags, models, serial numbers, categories, and user names.
- Category and assignment data are protected by the app model logic.
