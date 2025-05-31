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

* **Python 3.8+** installed (download from [python.org](https://www.python.org/downloads)).
* **MySQL** server installed and running. Download the installer from [MySQL Downloads](https://dev.mysql.com/downloads/installer/).
* **Virtual environment** tool (included with Python).

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/ecg-django-app.git
   cd ecg-django-app
   ```
2. **Create a virtual environment** (if not already created)

   ```bash
   py -m venv venv
   ```
3. **Activate the virtual environment**

   * On Windows (PowerShell):

     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * On Windows (CMD):

     ```cmd
     .\venv\Scripts\activate.bat
     ```
   * On macOS/Linux:

     ```bash
     source venv/bin/activate
     ```
4. **Install dependencies**

   ```bash
   pip install Django mysqlclient colorama
   ```

---

## Configuration

1. **Database settings**

   * Open `webowe/settings.py`.
   * Under the `DATABASES` section, configure your MySQL credentials:

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

1. **Create migrations**

   ```bash
   python manage.py makemigrations accounts ecg
   ```
2. **Apply migrations**

   ```bash
   python manage.py migrate
   ```

---

## Running the Development Server

```bash
python manage.py runserver
```

Visit: [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)

---

## Usage

1. **Register or login** at `/login/`.
2. **Upload an ECG file** via the "Dodaj wynik" page.
3. **View your results** on "Twoje wyniki", click a title to see detailed analysis.

---

## Project Structure

```
├── accounts/            # User accounts, CSVResult model, upload views
├── ecg/                 # ECGSignal, AnalysisResult models, ML code
├── webowe/              # Django project settings & URLs
├── media/               # Uploaded files
├── templates/           # HTML templates
└── manage.py            # Django management script
```

---

## Troubleshooting

* **`ModuleNotFoundError: No module named 'mysqlclient'`**
  Install with `pip install mysqlclient`.
* **Media files not served**
  Ensure `DEBUG = True` and `urlpatterns += static(...)` in `webowe/urls.py`.
* **AttributeError: 'CSVResult' object has no attribute 'analysis'**
  Run migrations after adding `analysis = JSONField(...)` in your model.

---

## License

MIT License © 2025 pddusza





## Simple Outline


To run the program locally: 
1. Install MySql https://dev.mysql.com/downloads/installer/
2. Set up the MySQL user as root, and password as strong_password (otherwise change in the webowe/settings.py file of the project)
3. Open terminal powershell -> Navigate to working directory of this project (cd folder_path)
4. If not existing, create a python environment -> py -m venv WEB_ECG_ENV
5. Activate the venv -> .\WEB_ECG_ENV\Scripts\activate.bat
6. Install Django -> py -m pip install Django
7. Install Colorama ->  py -m pip install "colorama >= 0.4.6"
8. Install For signal analysis -> py -m pip install neurokit2 numpy PyWavelets tensorflow
9. Install MySQLClient -> py -m pip install mysqlclient
10. Still run migrations in order to create the SQL Database -> py -m manage makemigrations accounts ecg; py -m manage migrate
11. Still in the working directory of this project run ->  py -m manage runserver
12. Please visit this url to see the project: "http://127.0.0.1:8000/login/"
