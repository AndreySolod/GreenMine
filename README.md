# GreenMine

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-supported-blue)

This is a completely redesigned project based on the well-known [Pentest Collaboration Framework](https://gitlab.com/invuls/pentest-projects/pcf), created as a separate project to fix many architectural flaws and errors of the original project while preserving its core ideas.

## Table of Contents

- [GreenMine](#greenmine)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
    - [Using Docker (Recommended)](#using-docker-recommended)
    - [Manual Installation](#manual-installation)
  - [Main Advantages](#main-advantages)
  - [What is not implemented from the original project, what is planned to be implemented](#what-is-not-implemented-from-the-original-project-what-is-planned-to-be-implemented)
  - [Installing Dependencies](#installing-dependencies)
    - [Debian-based systems](#debian-based-systems)
  - [Configuring Application Parameters](#configuring-application-parameters)
  - [Main Commands](#main-commands)
  - [Automatic Error Correction](#automatic-error-correction)
  - [User Logins](#user-logins)
  - [Running in Debug Mode](#running-in-debug-mode)
  - [Running via Docker](#running-via-docker)
  - [Hooks](#hooks)
  - [Acknowledgments](#acknowledgments)
  - [License](#license)

## Quick Start

### Using Docker (Recommended)
```bash
git clone https://gitverse.ru/NekiyUser/GreenMine
cd GreenMine
docker compose up
```
Access the application at http://localhost

Default credentials: admin/admin and worker/worker

### Manual Installation
1. Install Python 3.8+ and Redis
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Initialize database: `FLASK_APP=GreenMine flask greenmine db-init`
6. Load default value to database: `FLASK_APP=GreenMine flask greenmine update-database-value`
7. Run (develop mode): `./GreenMine.py`

## Main Advantages

1. **Completely rewritten migration system** – database changes are now handled via SQLAlchemy, which allows automatic database rebuilding during updates and avoids most of the original errors where incorrectly inserted values could not be corrected. Additionally, improvements and updates should become much easier;

2. **Added and improved task tab** – designed following the example of most project management applications;

3. **Added "Description" fields for most objects** – where additional data can be entered via a WYSIWYG editor;

4. **Added notes for objects** – where you can save your work process in text form;

5. **Added change history for most objects** – now all changes for most objects are logged and displayed in a separate tab;

6. **Replaced the standard object list display table (services, hosts, issues, etc.)** with an AJAX table that dynamically pulls data from the backend for page display. This solves both the problem of loading the entire table onto the page and unnecessary memory consumption (sometimes pages wouldn't load at all), as well as the problem of displaying long fields – the "hash" field for passwords was not filled precisely because otherwise other passwords would overflow beyond the page;

7. **Minor improvement** – when entering a hash into the list of compromised credentials, GreenMine now suggests its type. Additionally, when selecting a hash type, GreenMine suggests its HashCat and John modes;

8. **Introduced user roles for projects** similar to management systems, as well as the ability to configure action permissions for corresponding roles (e.g., for observers – set the ability to only view objects but not edit them). The concept of an "administrator" is introduced – a person who has all possible roles on the project and has access to all actions (as well as access to the administration panel). There is also a project leader – they have access to all actions, but only on their own project.

9. **Added an administration panel** where you can add enumeration objects (also called "Reference Books"), view the list of all files, delete some files, add report/task/issue templates, etc.;

10. **Due to changes in the migration system, report systems have been redesigned** – now each report template receives a "project" variable, which is an object of type "Project", containing all the necessary data for report creation;

11. **Added multilingual support**. The application is translated into Russian and English;

12. **Notes and note editing have been moved to WebSockets** – this avoids the problem of "unsaved" notes;

13. **Added fields for hosts**: "MAC address" (with automatic vendor detection by MAC address), "Device type", "Device manufacturer", "Device model";

14. **Added field for services**: "Web interface screenshot" – this should significantly speed up the inventory stage in an organization. Additionally, a "technical information" field is added, which is filled by Nmap import with its own data from scripts;

15. **Export utilities have been removed** – now export can be done directly on the page listing all objects. Additionally, filtering has been improved – now filtering can be performed both across all fields simultaneously and for each field individually;

16. **Removed almost all import utilities from other systems** (only the most basic one remains – import from Nmap/Masscan, with functionality partially redesigned to add information to new fields.) – due to a complete overhaul of the general data concept of these utilities. They are now background tasks, which should solve the problem of a "frozen" web interface for users when trying to import a large file. Additionally, an "Inventory Scanner" utility has been added – it allows specifying a list of ports for scanning and taking screenshots of their web interfaces (both http and https);

17. **Nmap import can now read even incomplete scan files** – if the file cannot be read, it attempts to complete and read it.

18. **Chat messages** – now via WebSockets, and, most importantly – they work!

19. **Minor interface improvements** – added user avatars, notifications (via WebSockets), theme selection (color scheme), automatic database population with initial values, traffic minification;

20. **Hashing type for password storage** – Streebog512;

21. **Improved logging** – now you can maintain a separate log of user actions, not just the standard Flask log.

22. **Added Content Security Policy**, increasing application security;

23. **The service inventory stage is now also conducted through a separate tab in the web interface**, allowing it to be performed faster;

24. **Improved state diagrams** – moved to a separate page in the project. They are now slightly more informative than in the original project;

25. **Added functionality for coordinating actions with the organization's security department** through creating research events and detection events;

26. **Added factory credentials functionality** – currently just as an automation module tab, will later extend to object cards with verification capability;

27. **Added commands** – objects that accelerate project creation and adding new roles to the project;

28. **Added utilities for quick RDP NLA absence checking, module for automatic hash retrieval from IPMI**;

29. **Implemented issue carousel functionality**, which will speed up the creation of a visual report on work done;

30. **Added proxy server authentication support**, allowing passwords not to be stored or remembered when using, for example, mTLS;

31. **Configured integration with MetaSploit Framework**, which will automate attack processes;

32. **Added ability to create custom code blocks – hooks**.

33. **Added ability to send notifications via WebPush**. Chat messages can be sent via this technology.

## What is not implemented from the original project, what is planned to be implemented

Current improvements:

- Add WebDAV – to simplify file storage in the project. Additionally, it is necessary to disable the right mouse button on files – due to Chrome/Firefox behavior they are displayed incorrectly;

- Improve security – endpoint for CSP reports;

## Installing Dependencies
### Debian-based systems
1. Google Chrome:
First, download dependency packages:

```bash
sudo apt install curl software-properties-common apt-transport-https ca-certificates -y
```

Next, add repositories and signing keys:

```bash
curl -fSsL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor | sudo tee /usr/share/keyrings/google-chrome.gpg > /dev/null
echo deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main | sudo tee /etc/apt/sources.list.d/google-chrome.list
```

Now update the package cache and install Google Chrome:

```bash
sudo apt update
sudo apt install google-chrome-stable
```

2. Nmap:
```bash
sudo apt install nmap
```

## Configuring Application Parameters

When creating a new application (after cloning the project), you first need to edit the config.py file to specify your preferred settings, or pass them via the following environment variables:
- `SECRET_KEY` – specifies the application secret key used to encrypt cookie files. It is advisable to set this, as without it cookies will not be valid between application start/stop;
- `SQLALCHEMY_DATABASE_URI` – path to the database. Specified as `DB_TYPE:///URI`. For example, for sqlite the value would be `sqlite:////opt/test_database.db`;
- `REST_FORBIDDEN_ATTRIBUTES` – object attributes that will not be returned or modified in REST requests. Default: `User.password_hash,User.token,User.token_expiration`;
- `TOKEN_EXPIRATION` – token lifetime for REST requests. Default – 1 year;
- `CELERY_BROKER_URL` – address of the database acting as Celery task broker. Redis is recommended. Specified as: `redis://username:password@localhost:6379/0`. Additionally, Redis Over TLS protocol can be specified: `rediss://username:password@localhost:6379/0?ssl_cert_reqs=required`;
- `CELERY_RESULT_BACKEND` – address of the database where Celery workers will store their results. Specified the same as `CELERY_BROKER_URL`;
- `CELERY_TASK_IGNORE_RESULT` – specifies whether to ignore task execution results or not. Set as `True` or `False`;
- `CELERY_WORKERS_COUNT` – specifies the number of workers that will be automatically started with the application. Default – 1. To disable worker startup, set this parameter to 0. The parameter works only in Debug mode;
- `CELERY_WORKERS_CONCURRENCY_COUNT` – number of threads per each Celery worker. Default – 4. The parameter works only in Debug mode;
- `DEFAULT_LANGUAGE` – language that will be used for the application when initializing the database. Default – `ru`;
- `CSP_ENABLED` – whether Content Security Policy will be active;
- `PAGINATION_ELEMENTS_COUNT_SELECT2` – number of pagination elements for the Select2 plugin (data is loaded dynamically into the select form). Default – 30;
- `USER_ACTION_LOGGING_IN_STDOUT` – whether user actions will be logged to STDOUT. Default – `True`;
- `USER_ACTION_LOGGING_FILE` – file where user actions will be additionally saved. Default (for Production config) this file is absent;
- `FLASK_LOGGING_ON_STDOUT` – whether Flask logs will be written to STDOUT. Default – True;
- `FLASK_LOGGING_FILE` – file where Flask logs will be additionally saved. Default – absent;
- `ERROR_LOGGING_FILE` – file where application errors (error 500) will be saved. Default – `/logs/error.log`;
- `METASPLOIT_HOST` – address of the host where the MetaSploit listener is running (usually via `msfrpcd -P <password> -p 55553`);
- `METASPLOIT_PORT` – port where the MetaSploit listener is running;
- `METASPLOIT_PASSWORD` – password for accessing the MetaSploit listener.

Additionally, you need to pass the `ENVIRONMENT` argument, setting it to `PRODUCTION`, since by default the Development server is used for development purposes.

You can also optionally pass the `APP_PORT` argument, specifying the port on which the application will listen. Default – 5000.

## Main Commands

After setting application parameters, you need to initialize the application database. The following commands are used for this:
- `FLASK_APP=GreenMine flask greenmine db-init` – initializes a new database (even if it didn't exist before, as with sqlite). This step can be skipped – the database can be created during the change entry stage;
- `FLASK_APP=GreenMine flask db migrate` – creates new migration scripts for writing data to the database. This step can be skipped – migrations will run with the application;
- `FLASK_APP=GreenMine flask db upgrade` – applies changes to the database;
- `FLASK_APP=GreenMine flask greenmine load-default-database` – loads default data into the database. If default data was not inserted during the upgrade stage – they will be inserted on the first application launch;

When updating the database (e.g., when updating the project), the following commands are used:
- `FLASK_APP=GreenMine flask db migrate` – creates new migration scripts;
- `FLASK_APP=GreenMine flask db upgrade` – applies changes to the database;
- `FLASK_APP=GreenMine flask greenmine update-database-value` – populates newly created tables in the database with values from the `initial_database_value.yml` file;

And when recreating the database:
- `FLASK_APP=GreenMine flask greenmine reset-database` – completely recreates the existing database, populating it with data from the `initial_database_value.yml` file;
- `FLASK_APP=GreenMine flask greenmine recreate-table --table <table_name>` – recreates the specified table in the database (first deletes, then recreates).

Additionally, if new tables with default data have been introduced, you can use the command:
```bash
FLASK_APP=GreenMine flask greenmine update-database-value
```

Which will load values from the `initial_database_value.yml` file into empty tables.

And to recreate a table and populate it with values from the `initial_database_value.yml` file, you can use the command:
```bash
FLASK_APP=GreenMine flask greenmine recreate-table --table <table_name> 
```

The `<table_name>` value is specified in the form described in the `default_database_value.yml` file.

For updating application translations, 2 commands are provided:
- `FLASK_APP=GreenMine flask translate update` – extracts all translations from source files and places them in the messages.pot file, then updates po-files in the app/translations directory;
- `FLASK_APP=GreenMine flask translate compile` – after the source po translation files are created, this command compiles them into a .mo file. Has the `-f` option, which allows including translations marked as `fuzzy` in the final compiled translation file.

## Automatic Error Correction

GreenMine can perform checks for minimum values in the database before the very first request, and if these values are missing – automatically insert them.
By default, the following checks are performed:

- There exists at least one user who is an administrator. If it doesn't exist – either a new user is created (Login/password – admin/admin), or an existing user with the login **admin** is given the flag indicating they are an administrator;

- There exists a Project Role called "Anonymous". If it doesn't exist – it is automatically added to the database;

- The database contains one instance of global settings;

- The database contains the application language with the slug "auto" – i.e., the application language will be determined based on user preferences.

## User Logins

User logins must start with a letter, and must contain alphabet characters, digits, "-" and "_" symbols. This is done so they can be mentioned via CKEditor.

Factory credentials for the application – `admin/admin` and `worker/worker`.

## Running in Debug Mode

To explore the project without building a Docker container, you can run it in debug mode as follows:
```bash
# First clone the project
git clone https://gitverse.ru/NekiyUser/GreenMine
cd GreenMine
# Install dependencies into a virtual environment
python -m venv ./venv
source ./venv/bin/activate
pip install -r ./requirements.txt
# Create and initialize the database with initial values:
FLASK_APP=GreenMine flask greenmine db-init
flask db migrate
flask db upgrade
FLASK_APP=GreenMine flask greenmine load-default-database
# Now we can run the application
./GreenMine.py
```

For background tasks to work in debug mode, you need to run Redis and Celery Worker in a separate window as follows:
```bash
docker run -d -p 6379:6379 redis
celery -A run_celery worker --loglevel=INFO
```

Then we can

## Running via Docker

To run the application via Docker, you need to build the container:

```bash
docker build . -t greenmine
```

Then the container with all dependencies can be launched via `Docker compose`:

```bash
docker compose up
```

After the initialization process completes (when initial values are inserted into the database), the project will be available on port 5000.

## Hooks

**Hooks** are custom code blocks that are called in response to corresponding events in the application: project creation, task creation, task modification, comment addition, etc.

In general, hooks receive the following variables with which they can interact:
- `db` – database;
- `this` – the object over which the change/addition/deletion etc. occurred;
- `session` – current session;
- `app` – current application.

## Acknowledgments

GreenMine is a complete redesign of the [Pentest Collaboration Framework (PCF)](https://gitlab.com/invuls/pentest-projects/pcf).

Special thanks to:
- The original PCF developers for the inspiration
- Contributors who have helped improve GreenMine
- The open-source community for valuable tools and libraries

## License

See `LICENSE.txt` for full license text. For commercial use, please contact the author.