FROM python:3.10-slim

WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ingestion script
COPY ingest.py .

CMD ["python", "-u", "ingest.py"]