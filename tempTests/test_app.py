import os
import subprocess
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

# Temporary scripts directory for testing
UPLOAD_DIR = "scripts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Hello from test_app!"}

@app.post("/upload/")
async def upload_script(file: bytes, filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(file)
    return {"message": f"File '{filename}' uploaded successfully."}

@app.post("/process/")
async def process_script(filename: str, background_tasks: BackgroundTasks):
    script_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(script_path):
        return {"error": f"File '{filename}' does not exist."}

    # Add script execution as a background task
    background_tasks.add_task(run_script_in_docker, script_path)

    return {"message": f"Script '{filename}' is being processed."}


def run_script_in_docker(script_path: str):
    # Run the script inside a Docker container
    container_name = f"python_runner_{os.path.basename(script_path)}"
    subprocess.run([
        "docker", "run", "--rm",
        "-v", f"{os.getcwd()}/scripts:/app/scripts",
        "battleship_backend",
        "python", f"/app/scripts/{os.path.basename(script_path)}"
    ])
