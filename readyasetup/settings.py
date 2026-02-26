import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

DEBUG = False

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "readya-backend.onrender.com",
    "www.readya-backend.onrender.com",
]

CSRF_TRUSTED_ORIGINS = [
    "https://readya-backend.onrender.com",
    "https://www.readya-backend.onrender.com",
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

load_dotenv(os.path.join(BASE_DIR, '.env')) 

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',  
    'rest_framework',
    'readyaapp',
    'drf_spectacular',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",   
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",  
    "http://127.0.0.1:3000",
    "https://readya.netlify.app",
    "https://www.readya.netlify.app",
    "https://www.readya.me",
    "https://readya.me",
]


CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

ROOT_URLCONF = 'readyasetup.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'readyasetup.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# EMAIL_FROM = os.getenv("EMAIL_FROM")


AZURE_SPEECH_KEY_KA = os.getenv("AZURE_SPEECH_KEY_KA")
AZURE_SPEECH_REGION_KA = os.getenv("AZURE_SPEECH_REGION_KA")


AZURE_SPEECH_KEY_EN = os.getenv("AZURE_SPEECH_KEY_EN")
AZURE_SPEECH_REGION_EN = os.getenv("AZURE_SPEECH_REGION_EN")




EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")



# Keepz API credentials
KEEPZ_PRIVATE_KEY = os.getenv("KEEPZ_PRIVATE_KEY")
if KEEPZ_PRIVATE_KEY:
    KEEPZ_PRIVATE_KEY = KEEPZ_PRIVATE_KEY.replace("\\n", "\n").strip()

KEEPZ_PUBLIC_KEY = os.getenv("KEEPZ_PROD_PUBLIC_KEY")
if KEEPZ_PUBLIC_KEY:
    KEEPZ_PUBLIC_KEY = KEEPZ_PUBLIC_KEY.replace("\\n", "\n").strip()

KEEPZ_INTEGRATOR_ID = os.getenv("KEEPZ_PROD_INTEGRATOR_ID")
KEEPZ_BASE_URL = "https://gateway.keepz.me/ecommerce-service"

KEEPZ_RECEIVER_ID = os.getenv("KEEPZ_RECEIVER_ID")

SITE_URL = os.getenv("SITE_URL")
BACKEND_URL = os.getenv("BACKEND_URL")


# GOOGLE API KEY for Text-to-Speech

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

GOOGLE_APPLICATION_CREDENTIALS = os.path.join(BASE_DIR, "google-tts.json")


# DRF Spectacular settings for API documentation

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Readya API',
    'DESCRIPTION': 'Text to Speech API',
    'VERSION': '1.0.0',
}





