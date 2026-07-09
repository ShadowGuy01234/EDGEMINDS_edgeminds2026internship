# CodeGenome-Edge: NVIDIA Jetson Quickstart Guide

This guide contains the exact steps and commands to deploy and run **CodeGenome-Edge** in your Jetson Cloud Lab environment.

---

## Step 1: Configure Environment Variables
Since we are using a remote Ollama server, you do not need to install or run Ollama locally on the Jetson board. Instead, configure the application to connect to the remote Ollama service URL:

1. Navigate to the repository:
   ```bash
   cd ~/EDGEMINDS_edgeminds2026internship
   ```

2. Create and populate the `.env` file directly from the terminal. Run the following command (replace `http://172.17.0.1:11434` with your actual remote Ollama URL if it is different):
   ```bash
   cat << 'EOF' > .env
   OLLAMA_BASE_URL=http://172.17.0.1:11434
   OLLAMA_MODEL=llama3.2:1b
   DB_PATH=./index/codegenome.db
   MANIFEST_PATH=./index/manifest.json
   API_HOST=0.0.0.0
   API_PORT=8000
   FRONTEND_STATIC_DIR=frontend/dist
   ENV=prod
   EOF
   ```

---

## Step 2: Start ngrok in the Background
Download the ngrok binary and run it in the background to tunnel your application on port 8000:

```bash
# 1. Navigate to home directory
cd ~

# 2. Download the working ngrok Linux ARM64 package
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz

# 3. Extract the binary
tar -xvzf ngrok-v3-stable-linux-arm64.tgz

# 4. Authenticate ngrok (replace <token> with your personal ngrok auth token)
./ngrok config add-authtoken <your_ngrok_auth_token>

# 5. Start the tunnel in the background
./ngrok http 8000 --log=stdout > ngrok.log 2>&1 &
```

---

## Step 3: Get the ngrok Forwarding Link
To get the public URL to access the dashboard, search the ngrok log file:

```bash
cat ngrok.log | grep -o 'url=https://[a-zA-Z0-9.-]*'
```

---

## Step 4: Start the CodeGenome-Edge Backend Server
Enter your repository directory, activate the Python virtual environment, and start the FastAPI uvicorn server:

```bash
# 1. Navigate to the repository
cd ~/EDGEMINDS_edgeminds2026internship

# 2. Activate virtual environment
source venv/bin/activate

# 3. Start the server
python -m uvicorn server.api.main:app --host 0.0.0.0 --port 8000
```

You can now open the ngrok forwarding URL in any web browser to access the CodeGenome-Edge dashboard.
