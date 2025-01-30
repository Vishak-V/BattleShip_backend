import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
import threading
import sys

sys.stdout.reconfigure(line_buffering=True)

print("Runner script has started.")

UPLOADS_DIR = "uploads"  # Directory for uploaded scripts
SCRIPT_RUNNER_IMAGE = "python:3.9-slim"  # Base image for script execution

# Shared dictionary to store script outputs
script_outputs = {}
outputs_lock = threading.Lock()

# Ensure the uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)


def run_script_in_container(script_name):
    """
    Start a Docker container to execute the given Python script.
    """
    global script_outputs
    print(f"Running script: {script_name}")
    script_path = os.path.join(UPLOADS_DIR, script_name)

    try:
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}/{UPLOADS_DIR}:/app/uploads",
            SCRIPT_RUNNER_IMAGE, "python", f"/app/uploads/{script_name}"
        ], check=True, capture_output=True, text=True)

        # Store the output of the script in the dictionary
        with outputs_lock:
            script_outputs[script_name] = result.stdout.strip()

        print(f"Output from {script_name}:\n{result.stdout}")
        print(f"Script {script_name} executed successfully.")
    except subprocess.CalledProcessError as e:
        error_msg = f"Error running {script_name}: {e.stderr.strip()}"
        with outputs_lock:
            script_outputs[script_name] = error_msg
        print(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error while running {script_name}: {e}"
        with outputs_lock:
            script_outputs[script_name] = error_msg
        print(error_msg)


def monitor_and_run_scripts():
    """
    Continuously monitor the uploads directory and process new scripts.
    """
    processed_scripts = set()

    print(f"Monitoring directory: {UPLOADS_DIR}")
    while True:
        try:
            # Get the list of Python scripts in the uploads directory
            scripts = [f for f in os.listdir(UPLOADS_DIR) if f.endswith(".py")]
            print(f"Detected scripts: {scripts}")

            # Identify new scripts (not yet processed)
            new_scripts = [s for s in scripts if s not in processed_scripts]

            if new_scripts:
                print(f"New scripts detected: {new_scripts}")

            # Run each new script
            for script in new_scripts:
                try:
                    run_script_in_container(script)
                    processed_scripts.add(script)  # Mark as processed only if it runs successfully
                except Exception as e:
                    print(f"Error processing script {script}: {e}")

            time.sleep(2)  # Avoid overloading the CPU
        except KeyboardInterrupt:
            print("Monitoring stopped.")
            break


if __name__ == "__main__":
    monitor_and_run_scripts()
