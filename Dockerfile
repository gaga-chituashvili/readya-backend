FROM python:3.11-slim


RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kat \
    libtesseract-dev \
    libleptonica-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "readyasetup.wsgi:application", "--bind", "0.0.0.0:10000", "--workers", "4", "--threads", "2", "--timeout", "120"]



