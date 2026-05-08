FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py .

# Storage volume mount point
VOLUME /app/data

CMD ["python", "main.py"]
