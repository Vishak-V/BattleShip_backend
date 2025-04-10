FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add gunicorn to requirements if not already there
RUN pip install gunicorn

# Set environment variables
ENV PORT=8080

# Run the application
CMD exec gunicorn --bind :$PORT main:app