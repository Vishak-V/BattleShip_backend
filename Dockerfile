FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Make installation more verbose and ensure it doesn't use cache
RUN pip install --no-cache-dir -r requirements.txt --verbose

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]