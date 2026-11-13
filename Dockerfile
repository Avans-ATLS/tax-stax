FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050
ENV PYTHONPATH=/app/src
CMD ["gunicorn", "--chdir", "/app/src/taxstax", "--bind", "0.0.0.0:8050", "--workers", "1", "app:server"]
