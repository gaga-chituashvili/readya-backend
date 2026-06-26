
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
├── apt.txt                    # System dependencies for Fly.io
├── Dockerfile                 # Docker configuration for containerized deployment
├── fly.toml                   # Fly.io deployment configuration
├── keys
│   └── keepz_public.pem       # Public key for Keepz payment encryption
├── manage.py                  # Django management entry point
├── README.md                  # Project documentation
├── readyaapp                  # Main Django app
│   ├── __init__.py
│   ├── admin.py               # Django admin configuration
│   ├── apps.py                # App configuration
│   ├── authentication.py      # Custom JWT authentication backend
│   ├── migrations             # Database migration files
│   ├── models.py              # Database models
│   ├── serializers            # DRF serializers
│   │   └── sign_serializer.py # User registration/login serializer
│   ├── services               # Business logic (TTS, OCR, email, payments)
│   │   ├── azure.py
│   │   ├── docx_reader.py
│   │   ├── email.py
│   │   ├── google_cts.py
│   │   ├── image_reader.py
│   │   ├── keepz_crypto.py
│   │   ├── keepz.py
│   │   ├── markupread.py
│   │   ├── openai_chat.py
│   │   ├── payment_service.py
│   │   ├── pdf_reader.py
│   │   ├── services.py
│   │   └── voice.py
│   ├── tests.py               # Unit tests
│   ├── urls.py                # App-level routes
│   └── views                  # API views split by feature
│       ├── __init__.py        # Home view
│       ├── chunk_split.py     # Chunked document upload view
│       ├── generatevoice_view.py # TTS voice generation view
│       ├── library_view.py    # User document library view
│       ├── openai_view.py     # OpenAI chat view
│       ├── payment_view.py    # Payment processing view
│       ├── sign_view.py       # Auth views (login/register/profile)
│       └── streammp3_view.py  # MP3 audio streaming view
├── readyasetup                # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                # ASGI config (async server support)
│   ├── settings.py            # Main Django settings
│   ├── urls.py                # Project-level routes
│   └── wsgi.py                # WSGI config (Gunicorn)
├── requirements.txt           # Python dependencies
└── test.py                    # Local test script
```
## Tech Stack

### Backend

- Django  
- Django REST Framework  
- python-dotenv  
- psycopg2-binary  
- gunicorn  
- whitenoise  
- django-cors-headers  
- dj-database-url  

### AI / APIs

- OpenAI  
- Google Generative AI  
- ElevenLabs  
- Azure Cognitive Services Speech  
- Google Cloud Text-to-Speech  

### File Processing

- PyPDF2  
- python-docx  
- pytesseract  
- Pillow  

### Audio Processing

- pydub  

### Documentation

- drf-spectacular  

### Security

- cryptography  

### Utilities

- requests

