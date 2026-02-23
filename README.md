
# Readya 🚀

ReadyA is a full-stack web application currently under active development.

## 📌 Project Status

⚠️ This project is in active development.  
New features, improvements, and optimizations are continuously being added.

---

## 🛠 Tech Stack

### Frontend
- React.js
- Typescript
- HTML5
- CSS3

### Backend
- Django
- Django REST Framework
- Python

### Database
- SQLite (development)
- PostgreSQL (planned for production)

### Other Tools
- Axios
- Git & GitHub
- Docker (planned)

---

## 📂 Project Structure

```
├── Dockerfile                 # Docker configuration for containerized deployment
├── README.md                  # Project documentation
├── google-tts.json            # Google service account key (⚠️ should NOT be in repo)
├── keys
│   └── keepz_public.pem       # Public key for Keepz payment encryption
├── manage.py                  # Django management entry point
├── media
│   └── uploads                # User uploaded files & generated media
├── readyaapp                  # Main Django app
│   ├── __init__.py
│   ├── __pycache__            # Python compiled cache (auto-generated)
│   ├── admin.py               # Django admin configuration
│   ├── apps.py                # App configuration
│   ├── migrations             # Database migration files
│   ├── models.py              # Database models
│   ├── services               # Business logic (TTS, OCR, email, etc.)
│   ├── tests.py               # Unit tests
│   ├── urls.py                # App-level routes
│   └── views.py               # API views & endpoints
├── readyasetup                # Django project configuration folder
│   ├── __init__.py
│   ├── __pycache__
│   ├── asgi.py                # ASGI config (async server support)
│   ├── settings.py            # Main Django settings
│   ├── urls.py                # Project-level routes
│   └── wsgi.py                # WSGI config (Gunicorn uses this)
├── requirements.txt           # Python dependencies
├── staticfiles                # Collected static files (for production)
│   ├── admin                  # Django admin static
│   └── rest_framework         # DRF static assets
├── test.py                    # Probably local test script
└── uploads                    # Additional upload directory
```
