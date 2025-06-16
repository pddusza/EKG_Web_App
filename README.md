# ECG Analysis Django Project

A simple Django web application for uploading ECG signal files, running ML-based statistical analysis, and visualizing results.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Database Setup & Migrations](#database-setup--migrations)
5. [Running the Development Server](#running-the-development-server)
6. [Usage](#usage)
7. [Project Structure](#project-structure)
8. [Troubleshooting](#troubleshooting)
9. [License](#license)

---

## Prerequisites

Before you begin, ensure you have the following installed and configured on your system:

* **Python 3.12** (download from [python.org](https://www.python.org/downloads)).
* **MySQL Server**: Install from [MySQL Downloads](https://dev.mysql.com/downloads/installer/), and ensure the service is running.
* **Virtual environment** tool (included with Python).

---

## Installation

Follow these steps to set up the project locally:

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/ecg-django-app.git
   cd ecg-django-app
   ```
2. **Install MySQL** (if not already installed)

   * Download and run the MySQL Installer from [https://dev.mysql.com/downloads/installer/](https://dev.mysql.com/downloads/installer/)
   * During setup, create a root user with a strong password (or note your own credentials for later).
3. **Set up the MySQL user and database**

   * Log in to MySQL:

     ```bash
     mysql -u root -p
     ```
   * Create the database:

     ```sql
     CREATE DATABASE ecgdb;
     ```
   * Grant privileges (if using a custom user):

     ```sql
     GRANT ALL PRIVILEGES ON ecgdb.* TO 'root'@'localhost' IDENTIFIED BY 'strong_password';
     FLUSH PRIVILEGES;
     ```
4. **Create and activate a virtual environment**

   ```bash
   # On Windows (PowerShell)
   py -m venv venv
   .\venv\Scripts\Activate.ps1

   # On Windows (CMD)
   py -m venv venv
   .\venv\Scripts\activate.bat

   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```
5. **Install project dependencies**

   ```bash
   pip install Django mysqlclient colorama neurokit2 numpy PyWavelets tensorflow reportlab openpyxl
   ```
   or
   ```bash
   py -m pip Django mysqlclient colorama neurokit2 numpy PyWavelets tensorflow reportlab openpyxl
   ```
7. **Verify installations**

   * Django: `python -m django --version`
   * MySQL client: attempt `pip show mysqlclient`

---

## Configuration

1. **Database settings**

   * Open `webowe/settings.py`.
   * Under the `DATABASES` section, update your credentials:

     ```python
     DATABASES = {
         'default': {
             'ENGINE': 'django.db.backends.mysql',
             'NAME': 'ecgdb',
             'USER': 'root',
             'PASSWORD': 'strong_password',
             'HOST': 'localhost',
             'PORT': '3306',
         }
     }
     ```
   * If you use a different username/password, update accordingly.
2. **Secret key & debug mode** (development only)

   * In `webowe/settings.py`, verify:

     ```python
     SECRET_KEY = 'your-secret-key'
     DEBUG = True
     ```

---

## Database Setup & Migrations

Run the following commands to prepare the database schema:

1. **Create migrations**

   ```bash
   python manage.py makemigrations
   ```
   or
   ```bash
   py -m manage makemigrations
   ```
3. **Apply migrations**

   ```bash
   python manage.py migrate
   ```
    or
   ```bash
   py -m manage migrate
   ```

---

## Running the Development Server

Start the Django development server:

```bash
python manage.py runserver
```
 or
   ```bash
   py -m manage runserver
   ```

Then visit:

[http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)

---

## Usage

1. **Register or log in** at `/login/`.
2. **Upload an ECG file** via the "Dodaj wynik" page.
3. **View your results** on "Twoje wyniki"; click a title to see detailed analysis.

---

## Project Structure

```
├── accounts/            # User accounts, CSVResult model, upload views
├── ecg/                 # ECGSignal, AnalysisResult models, ML code
├── webowe/              # Django project settings & URLs
├── media/               # Uploaded files
├── reports/             # Section for reports / fonts
└── manage.py            # Django management script
```

---

## Troubleshooting

* **`ModuleNotFoundError: No module named 'mysqlclient'`**

  * Ensure `mysqlclient` is installed: `pip install mysqlclient`.
* **Media files not served**

  * Confirm `DEBUG = True` in `webowe/settings.py` and add:

    ```python
    from django.conf import settings
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    ```
* **AttributeError: 'CSVResult' object has no attribute 'analysis'**

  * Add `analysis = JSONField(...)` in your `CSVResult` model and re-run migrations.

---

## License

MIT License © 2025 pddusza
