# Use Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . /app/

# Ensure the uploads directory exists inside the container
RUN mkdir -p /app/uploads

# Install dependencies (if any)
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Run the runner.py script as the container's default command
CMD ["python", "runner.py"]
