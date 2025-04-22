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

- `FRONTEND_URL`: Connection string for frontend



## Accessing the Application

- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Database: localhost:5432

   The backend should now be running on `http://127.0.0.1:8000`.

# V2 Features

## 1. User Authentication
First, the user must be authenticated through OAuth (Google, GitHub, etc.). This creates a User record in the database with their information.

## 2. Bot Upload Workflow
The user needs to upload their bot files first:

1. **Upload Bot File** (`POST /api/v2/bots/`):
   - User uploads a Python file containing their bot's logic
   - File is saved to disk with a unique filename
   - A `BotUpload` record is created in the database with:
     - Reference to the file on disk
     - User as the uploader
     - Original filename
     - Optional description
   - User can now see this bot in their list of available bots

## 3. Tournament Creation Workflow
Once the user has uploaded bot(s), they can create and run tournaments:

1. **Create Tournament** (`POST /api/v2/tournaments/`):
   - User creates a new tournament by providing:
     - Tournament name
     - Description (optional)
     - Number of rounds (default: 3)
     - List of bot IDs (optional - can add later)
   - A `Tournament` record is created with status "pending"
   
2. **Register Bots to Tournament** (`POST /api/v2/tournaments/{tournament_id}/register`):
   - If bots weren't added during creation, users can register bots to their tournament
   - Creates `TournamentEntry` records linking bots to the tournament
   - Can only be done when tournament status is "pending"

3. **Start Tournament** (`POST /api/v2/tournaments/{tournament_id}/start`):
   - User initiates the tournament execution
   - System verifies there are at least 2 bots registered
   - Tournament status changes to "running"
   - Backend executes the tournament logic:
     - Gets all bot filenames from database
     - Runs the tournament using the existing `run_tournament` function
     - Creates `TournamentResult` records with rankings, wins, losses, scores
   - Tournament status updates to "completed" (or "failed" if error occurs)

4. **View Results** (`GET /api/v2/tournaments/{tournament_id}`):
   - User can retrieve tournament details and results
   - Results include bot rankings, win/loss records, and scores

## 4. Single Match Workflow (Alternative to Tournament)
Users can also run individual matches between two bots:

1. **Create Match** (`POST /api/v2/matches/`):
   - User selects two bots they want to match
   - Provides number of rounds
   - Match is automatically executed
   - A `Match` record is created with:
     - Both bot references
     - Match status (pending → running → completed)
     - Winner information
     - Win counts for each bot
     - Game logs (if available)

2. **View Match Results** (`GET /api/v2/matches/{match_id}`):
   - User can see detailed match information and results

## 5. User Dashboard Experience
Throughout this process, users can:

- View all their uploaded bots (`GET /api/v2/bots/`)
- See their tournament history (`GET /api/v2/tournaments/`)
- Check their match history (`GET /api/v2/matches/`)
- Get profile statistics (`GET /api/v2/users/me`)

The key improvement in this v2 API is that all data is persisted in the database, allowing users to:
- Keep track of their bot history
- Store tournament results for later analysis
- Review past matches
- Manage multiple tournaments without losing data

The database design supports relationships between users, bots, tournaments, and matches, ensuring data integrity and enabling more sophisticated features in the future (like leaderboards, statistics analysis, etc.).
