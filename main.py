from fastapi import FastAPI, File, UploadFile
from typing import List
from fastapi.responses import JSONResponse
from tournament import run_tournament
import os
import subprocess
import uuid
import docker
from pathlib import Path

app = FastAPI()

# Initialize Docker client
# client = docker.from_env()


# Directory to save uploaded Python files
UPLOAD_DIR = "./"

# Ensure the upload directory exists
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


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

@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    bot_files = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        bot_files.append(file.filename)
    
    rankings = run_tournament(bot_files)
    return {"rankings": rankings}
