FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
    flask \
    peewee \
    psycopg2-binary \
    python-dotenv \
    faker \
    pytest \
    pytest-cov

COPY . .

EXPOSE 5000

CMD ["python", "run.py"]