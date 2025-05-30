# TesterAlly Backend

## Overview

TesterAlly Backend is a Django-based REST API application designed to manage the backend functionalities for the TesterAlly platform. It uses Django REST Framework (DRF) for building APIs and supports secure JWT-based authentication.

For a complete understanding of the platform flow, refer to the [Workflow Documentation](./docs/TesterAlly_Agent_Workflow_Documentation.docx).

---

## Features

- RESTful API endpoints for CRUD operations.
- JWT-based authentication for secure API access.
- SMTP-based email functionality for notifications.
- Static file handling and efficient MySQL database integration.
- GitHub repo linking with agent-based local execution.
- Agent `.exe` for isolated environment setup.
- Member invitation and access control via cloud.

---

## AI-Powered Automation Stack

We integrate a variety of powerful libraries and tools to build the automation capabilities in TesterAlly:

- [`PyAutoGUI`](https://pyautogui.readthedocs.io/en/latest/) – GUI automation and interaction.
- [`PyGetWindow`](https://pypi.org/project/PyGetWindow/) – Window management.
- [`pywinauto`](https://pywinauto.readthedocs.io/en/latest/) – Windows GUI automation.
- [`Omniparser`](https://github.com/Hexagon/omniparser) – Universal ETL framework.
- [`Replicate`](https://replicate.com/) – AI model integration (e.g., for test generation or analysis).
- [`Django`](https://www.djangoproject.com/) & [`DRF`](https://www.django-rest-framework.org/) – Backend framework and REST API support.

---

## Databases Used

This project uses **MySQL** as the primary database.

---

## Technologies Used

- **Framework:** Django, Django REST Framework
- **Database:** MySQL
- **Authentication:** JSON Web Tokens (JWT)
- **Libraries:**
  - `django-cors-headers`
  - `python-decouple`
  - `whitenoise` (for static file management)

---

## Prerequisites

Ensure the following are installed:

- Python 3.x
- MySQL
- Pip

---

## Set Up a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
