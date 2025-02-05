# 🚀 Python Script Runner with FastAPI & Docker

This project provides a **FastAPI-powered Python script execution service** that:
- ✅ **Uploads and executes Python scripts inside Docker containers**
- ✅ **Automatically detects and runs scripts** placed in `/app/uploads`
- ✅ **Provides an API for manual execution and script monitoring**
- ✅ **Runs inside a Docker container for easy deployment**

---

## 📌 Prerequisites
Ensure you have the following installed on your system:
- **Docker**: [Install Docker](https://www.docker.com/)
- **Git** (for cloning the repository): [Install Git](https://git-scm.com/downloads)

---

## 📥 Installation & Setup

### 1️⃣ **Clone the Repository**
```
git clone https://github.com/Vishak-V/BattleShip_backend.git
cd BattleShip_backend
```

### 2️⃣ **Switch to the `docker-testing` Branch**
```
git checkout docker-testing
```

### 3️⃣ **Build and Start the Docker Containers**
```
docker-compose up --build
```
🔹 This will:
- Build the Python execution container
- Start the FastAPI server on port `8000`
- Begin monitoring the `/app/uploads/` folder for Python scripts

### 4️⃣ **Verify the API is Running**
Open your browser and visit:
```
http://localhost:8000/docs
```
Here, you can interact with the API and test its endpoints.

---

## 🚀 API Endpoints

### 📌 **1. Upload a Python Script**
Uploads a `.py` file to be executed.
```
curl -X 'POST'   'http://localhost:8000/upload-script/'   -H 'accept: application/json'   -H 'Content-Type: multipart/form-data'   -F 'file=@hello_world.py'
```
✅ **Response:**
```
{
  "message": "File 'hello_world.py' uploaded successfully."
}
```

---

### 📌 **2. Manually Execute a Script**
Run a specific script from `/app/uploads/`.
```
curl -X 'POST' 'http://localhost:8000/run-script/hello_world.py'
```
✅ **Response:**
```
{
  "message": "Script 'hello_world.py' is being executed."
}
```

---

### 📌 **3. Get Execution Logs**
Retrieve logs of all executed scripts.
```
curl -X 'GET' 'http://localhost:8000/script-outputs/'
```
✅ **Response:**
```
{
  "outputs": {
    "hello_world.py": "Hello, World!"
  }
}
```

---

## 🛑 Stopping the Server
To stop the server and containers:
```
docker-compose down
```

---

## 🔥 Troubleshooting

### ❌ **Port 8000 Already in Use?**
If another process is using port 8000, stop it or change the port in `docker-compose.yml`:
```
services:
  python-runner:
    ports:
      - "8080:8000"  # Change to an available port
```
Restart the container after the change:
```
docker-compose down && docker-compose up --build
```

### ❌ **Permission Issues with Docker?**
Try running Docker with `sudo`:
```
sudo docker-compose up --build
```

### ❌ **Script Not Executing?**
1. Ensure the script is inside the `/app/uploads/` directory.
2. Check logs for errors:
   ```
   docker-compose logs -f
   ```
3. Manually execute a script inside the container:
   ```
   docker exec -it python-runner sh
   python /app/uploads/hello_world.py
   ```

---

## 🎯 Summary
| **Feature**          | **Endpoint**                          | **Description**                      |
|----------------------|--------------------------------------|--------------------------------------|
| Upload script       | `POST /upload-script/`               | Uploads a Python script             |
| Run script manually | `POST /run-script/{script_name}`     | Runs a script inside Docker         |
| Get logs            | `GET /script-outputs/`               | View script execution logs          |
| API Documentation   | `GET /docs`                          | Open interactive API docs           |

Now you have a fully functional **Python script execution manager**! 🚀🔥

Let me know if you need any additional tweaks! 😊
