import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
import sys

# Enable line buffering for immediate log output
sys.stdout.reconfigure(line_buffering=True)

print("Runner script has started.")

UPLOADS_DIR = "uploads"  # Directory for uploaded scripts
SCRIPT_RUNNER_IMAGE = "python:3.9-slim"  # Base image for script execution

# Ensure the uploads directory exists
os.makedirs(UPLOADS_DIR, exist_ok=True)


def is_utf8(file_path):
    """
    Check if a file is UTF-8 encoded.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()
        return True
    except UnicodeDecodeError:
        return False


def run_script_in_container(script_name):
    """
    Start a Docker container to execute the given Python script.
    """
    print(f"Running script: {script_name}")
    script_path = os.path.join(UPLOADS_DIR, script_name)

    # Check if the file is UTF-8 encoded before execution
    if not is_utf8(script_path):
        print(f"Error: The file {script_name} is not UTF-8 encoded. Skipping execution.")
        return

    try:
        # Run the script inside a Docker container
        result = subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}/{UPLOADS_DIR}:/app/uploads",
            SCRIPT_RUNNER_IMAGE, "python", f"/app/uploads/{script_name}"
        ], check=True, capture_output=True, text=True)

        # Log the output of the script
        print(f"Output from {script_name}:\n{result.stdout}")
        print(f"Script {script_name} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error while running {script_name}: {e}")


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
