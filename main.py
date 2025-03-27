from fastapi import FastAPI, File, UploadFile, Request
from typing import List
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from tournament import run_tournament
import os
import subprocess
import uuid
from pathlib import Path
import logging
from os import stat

app = FastAPI()

# Initialize Docker client
# client = docker.from_env()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://battleshiptournament.vercel.app"],  # Your Next.js app's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save uploaded Python files
UPLOAD_DIR = "./tmp/"

# Ensure the upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

os.chmod(UPLOAD_DIR, os.stat.S_IRWXU | stat.S_IRWXG | os.stat.S_IRWXO)


# def run_python_in_docker(python_file_path: str):
#     # Create a unique ID for the container to avoid name conflicts
#     container_name = f"python-container-{uuid.uuid4().hex[:6]}"

#     # Create a Docker container with Python and mount the Python file
#     container = client.containers.run(
#         "python:3.12",  # Python Docker image
#         f"python /mnt/{os.path.basename(python_file_path)}",
#         volumes={UPLOAD_DIR: {'bind': '/mnt', 'mode': 'rw'}},  # Mount the upload directory
#         name=container_name,
#         detach=True
#     )

#     # Wait for the container to finish running
#     container.wait()

#     # Get the output from the container's logs
#     logs = container.logs().decode("utf-8")
#     return logs

@app.get("/")
def hello():
    return "hello World"

# @app.post("/run-python/")
# async def run_python_file(file: UploadFile = File(...)):
#     try:
#         # Save the uploaded Python file to disk
#         file_path = os.path.join(UPLOAD_DIR, file.filename)
#         with open(file_path, "wb") as f:
#             f.write(await file.read())

#         # Run the Python file inside Docker
#         output = run_python_in_docker(file_path)

#         # Return the output as a response
#         return JSONResponse(content={"output": output})

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/tournament/")
async def upload_files(request: Request):
    form = await request.form()
    bot_files = []
    for key in form.keys():
        if key.startswith('file'):
            file = form[key]
        
            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            
            bot_files.append(file.filename)
            
    
    rankings = run_tournament(bot_files,3)
    return {"rankings": rankings}

@app.post("/upload/")
async def upload_files(request: Request):
    form = await request.form()

    for key in form.keys():
        if key.startswith('file'):
            file = form[key]
        
            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
            # Save file
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            

    return {"message": "Files uploaded successfully"}
            
    
    


@app.post("/play/")
async def play_two_bots(file1: UploadFile, file2: UploadFile,number_of_games: int = 3):
    bot_files = []
    logging.info("Received files for tournament")
    # Save both files
    for file in [file1, file2]:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        bot_files.append(file.filename)

    logging.info(f"Files saved: {bot_files}")
    
    # Run the tournament with the uploaded files
    rankings = run_tournament(bot_files, number_of_games)
    print(rankings)
    logging.info(f"Rankings: {rankings}")
    return {"rankings": rankings} # Return the rankings as a JSON response