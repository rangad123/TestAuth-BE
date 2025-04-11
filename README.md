# TesterAlly Backend

## Overview

TesterAlly Backend is a Django-based REST API application designed to manage the backend functionalities for the TesterAlly platform. It uses Django REST Framework (DRF) for building APIs and supports secure JWT-based authentication.

---

## Features

- RESTful API endpoints for CRUD operations.
- JWT-based authentication for secure API access.
- Support for CORS to enable frontend-backend integration.
- SMTP-based email functionality for notifications.
- Static file handling and efficient database integration.

---

## Databases Used

This project uses **MySQL** as the primary database. 



## Technologies Used

- **Framework:** Django, Django REST Framework
- **Database:** MySQL
- **Authentication:** JSON Web Tokens (JWT)
- **Other Libraries:**
  - `django-cors-headers`
  - `python-decouple`
  - `whitenoise` (for static file management)

---

## Prerequisites

Make sure you have the following installed:

- Python 3.x
- MySQL
- Pip (Python package manager)

---

## Set Up a Virtual Environment:

- python -m venv venv
- source venv/bin/activate   # For Linux/Mac
- venv\Scripts\activate      # For Windows

---

## Install Dependencies:

- pip install -r requirements.txt

---

## Set Up Environment Variables:

SECRET_KEY=your_django_secret_key
DEBUG=True
ALLOWED_HOSTS=*
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email
EMAIL_HOST_PASSWORD=your_email_password
JWT_SECRET_KEY=your_jwt_secret_key
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306

---

## Apply Migrations:

python manage.py makemigrations
python manage.py migrate

---

## Run the Development Server:

python manage.py runserver

---

## Setup Instructions

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/rangad123/TesterAlly-BE.git
   cd YourRepositoryName

