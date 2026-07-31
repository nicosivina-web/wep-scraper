FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

ENV DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "app.py"]
