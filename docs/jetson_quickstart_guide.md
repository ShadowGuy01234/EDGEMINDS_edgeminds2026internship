# CodeGenome-Edge: NVIDIA Jetson Quickstart Guide

This guide contains the exact steps and commands to deploy and run **CodeGenome-Edge** in your Jetson Cloud Lab environment.

---

## Step 1: Install Ollama (User-space)
Since the root directory is read-only, download and extract Ollama directly into your home directory:

```bash
# 1. Install zstd (required to extract the .tar.zst archive)
sudo apt-get update && sudo apt-get install -y zstd

# 2. Download the Ollama Linux ARM64 package
wget https://ollama.com/download/ollama-linux-arm64.tar.zst

# 3. Extract the binary to your home directory (~/bin/ollama)
tar --zstd -xvf ollama-linux-arm64.tar.zst -C ~

# 4. Add the bin folder to your current session PATH
export PATH=$PATH:$HOME/bin
```

---

## Step 2: Start Ollama in the Background (CPU Mode)
Run Ollama in CPU mode to prevent Out-of-Memory (OOM) conflicts with the PyTorch CUDA backend:

```bash
# 1. Clean up any existing instances
kill -9 $(pgrep ollama)
kill -9 $(pgrep llama)

# 2. Start Ollama in the background bound to all network interfaces
CUDA_VISIBLE_DEVICES="" OLLAMA_HOST="0.0.0.0" ollama serve > ~/ollama.log 2>&1 &

# 3. Wait 5 seconds and verify Ollama is responding on the Jetson bridge IP
curl http://172.17.0.1:11434/

# 4. Pull the Llama 3.2 1B model
ollama pull llama3.2:1b
```

---

## Step 3: Start ngrok in the Background
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

## Step 4: Get the ngrok Forwarding Link
To get the public URL to access the dashboard, search the ngrok log file:

```bash
cat ngrok.log | grep -o 'url=https://[a-zA-Z0-9.-]*'
```

---

## Step 5: Start the CodeGenome-Edge Backend Server
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
