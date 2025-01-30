from fastapi import FastAPI, BackgroundTasks, UploadFile, File
import os
import time
import subprocess
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

app = FastAPI()

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Shared resources
processed_scripts = set()
script_outputs = {}
outputs_lock = Lock()

# Thread pool for executing scripts concurrently
executor = ThreadPoolExecutor(max_workers=5)


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


@app.post("/upload-script/")
async def upload_script(file: UploadFile = File(...)):
    """
    Upload a Python script and save it to the uploads directory.
    """
    file_path = os.path.join(UPLOADS_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    return {"message": f"File '{file.filename}' uploaded successfully."}


def run_script_in_docker(script_name):
    """
    Run a Python script inside a Docker container and capture its output.
    """
    global script_outputs
    print(f"Running script: {script_name}")
    script_path = os.path.join(UPLOADS_DIR, script_name)

    try:
        # Run the script inside a Docker container
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}/{UPLOADS_DIR}:/app/uploads",
            "python:3.9-slim", "python", f"/app/uploads/{script_name}"
        ], check=True, capture_output=True, text=True)

        # Store the output in the shared dictionary
        with outputs_lock:
            script_outputs[script_name] = result.stdout.strip()

        print(f"Output from {script_name}:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        error_message = f"Error running {script_name}: {e.stderr.strip()}"
        with outputs_lock:
            script_outputs[script_name] = error_message
        print(error_message)
    except Exception as e:
        unexpected_error = f"Unexpected error while running {script_name}: {e}"
        with outputs_lock:
            script_outputs[script_name] = unexpected_error
        print(unexpected_error)


def monitor_directory():
    """
    Monitor the uploads directory for new scripts and execute them.
    """
    global processed_scripts
    print(f"Monitoring directory: {UPLOADS_DIR}")
    while True:
        try:
            # Get the list of Python scripts in the uploads directory
            scripts = [f for f in os.listdir(UPLOADS_DIR) if f.endswith(".py")]
            new_scripts = [s for s in scripts if s not in processed_scripts]

            for script in new_scripts:
                # Submit the script for execution
                executor.submit(run_script_in_docker, script)
                processed_scripts.add(script)

            time.sleep(2)  # Avoid high CPU usage
        except Exception as e:
            print(f"Error monitoring directory: {e}")
            break


@app.get("/script-outputs/")
async def get_script_outputs():
    """
    Retrieve the outputs of all executed scripts.
    """
    with outputs_lock:
        return {"outputs": script_outputs}


@app.on_event("startup")
def start_monitoring():
    """
    Start monitoring the uploads directory when the FastAPI app starts.
    """
    print("Starting monitoring thread...")
    monitor_thread = Thread(target=monitor_directory, daemon=True)
    monitor_thread.start()
