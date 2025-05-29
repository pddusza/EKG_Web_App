To run the program locally: 
1. Install MySql https://dev.mysql.com/downloads/installer/
2. Set up the MySQL user as root, and password as strong_password (otherwise change in the webowe/settings.py file of the project)
3. Open terminal powershell -> Navigate to working directory of this project (cd folder_path)
4. If not existing, create a python environment -> py -m venv WEB_ECG_ENV
5. Activate the venv -> .\WEB_ECG_ENV\Scripts\activate.bat
6. Install Django -> py -m pip install Django
7. Install Colorama ->  py -m pip install "colorama >= 0.4.6"
8. Install MySQLClient -> py -m pip install mysqlclient
9. Still run migrations in order to create the SQL Database -> py -m manage makemigrations accounts ecg; py -m manage migrate
10. Still in the working directory of this project run ->  py -m manage runserver
