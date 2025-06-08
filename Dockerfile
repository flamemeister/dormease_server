FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgirepository1.0-dev \
    libcairo2 \
    libpango1.0-0 \
    libpangocairo-1.0-0 \
    gir1.2-glib-2.0 \
    gir1.2-gtk-3.0 \
    python3-gi \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
