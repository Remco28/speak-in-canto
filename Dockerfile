FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/instance /app/static/temp_audio

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -w ${GUNICORN_WORKERS:-2} -k gthread --threads ${GUNICORN_THREADS:-4} -b 0.0.0.0:${PORT:-8000} app:app"]
