# Battleship AI Backend

## Overview

This repository contains the backend for an app that allows users to submit their AI models designed to play Battleship and pits them against each other. The backend facilitates the submission of models, organizes games, and tracks the results of battles between the models.

## Features

- **Model Submission**: Allows users to submit their AI models that are built to play Battleship.
- **Game Management**: Orchestrates matches between AI models, including game state, turns, and results.
- **Leaderboard**: Tracks performance of submitted models and displays a leaderboard of the best models based on their win/loss record.
- **AI Model Evaluation**: Automatically evaluates the performance of submitted models in various scenarios.

## Technologies Used

- **Python**: Main programming language used for the backend logic and model evaluation.
- **FastAPI**: Fast and modern web framework to create APIs for communication between the frontend and backend.
- **SQLAlchemy**: ORM for database management.
- **PostgreSQL**: Relational database to store user data, AI models, game states, and results.
- **Docker**: Containerization of the application to ensure consistency across environments.
- **AI Model Interface**: Custom interface to communicate with the submitted AI models, ensuring they follow a standard format for the game.

## Setup

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Docker 

## Project Structure

Ensure your project has the following structure:

```
/your_project_directory
├── main.py               # Your FastAPI application
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker configuration
└── docker-compose.yml    # Docker Compose configuration
```

## Docker Files


## Running the Container

1. **Build and start the containers**:
   ```bash
   docker-compose up -d
   ```

2. **Check container status**:
   ```bash
   docker ps
   ```

3. **View logs**:
   ```bash
   docker-compose logs
   # Or for a specific service
   docker-compose logs api
   ```

4. **Stop the containers**:
   ```bash
   docker-compose down
   ```

## Testing Database Connection

1. **Access API endpoints**:
   ```bash
   curl http://localhost:8000
   ```

2. **If you've implemented a health check endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Connect to the database directly**:
   ```bash
   docker exec -it battleship_backend-db-1 psql -U postgres -d fastapi_db
   ```

## Rebuilding the Container

If you make changes to your code or dependencies:

```bash
# Rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

- **Container restarting**: Check logs using `docker-compose logs api`
- **Database connection issues**: Verify environment variables and network settings
- **Port conflicts**: Change the port mapping in docker-compose.yml
- **Missing dependencies**: Update requirements.txt and rebuild

## Environment Variables

- `DATABASE_URL`: Connection string for PostgreSQL
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_USER`: Database username
- `POSTGRES_DB`: Database name

## Accessing the Application

- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Database: localhost:5432

   The backend should now be running on `http://127.0.0.1:8000`.
