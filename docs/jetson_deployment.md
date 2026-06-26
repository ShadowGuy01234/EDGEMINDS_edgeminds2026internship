# CodeGenome-Edge: NVIDIA Jetson Deployment Guide

This guide provides step-by-step instructions for deploying and running **CodeGenome-Edge** on a remote NVIDIA Jetson board (e.g., Jetson Nano, Xavier, Orin Nano, or Orin AGX) running JetPack.

---

## Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Step 1: SSH into the Jetson Board](#2-step-1-ssh-into-the-jetson-board)
3. [Step 2: Install System Dependencies](#3-step-2-install-system-dependencies)
4. [Step 3: Setup Ollama on Jetson](#4-step-3-setup-ollama-on-jetson)
5. [Step 4: Configure PyTorch & CUDA Acceleration](#5-step-4-configure-pytorch--cuda-acceleration)
6. [Step 5: Deploy Frontend Assets](#6-step-5-deploy-frontend-assets)
7. [Step 6: Deploy Backend & Configure Application](#7-step-6-deploy-backend--configure-application)
8. [Step 7: Start CodeGenome-Edge](#8-step-7-start-codegenome-edge)
9. [Step 8: Configure as a Background System Service](#9-step-8-configure-as-a-background-system-service)
10. [Troubleshooting & Optimizations](#10-troubleshooting--optimizations)

---

## 1. Prerequisites

- **Jetson Hardware**: NVIDIA Jetson Board.
- **Operating System**: JetPack 5.x (Ubuntu 20.04) or JetPack 6.x (Ubuntu 22.04).
- **Network**: Both the Jetson board and your local machine must be connected to the same network (or accessible via a VPN/SSH tunnel).
- **Disk Space**: At least 10–15 GB of free space (required for Ollama LLM model files and HuggingFace SentenceTransformer models). We recommend configuring an external NVMe SSD or USB 3.0 drive as the primary partition.

---

## 2. Step 1: SSH into the Jetson Board

Find your Jetson board's local IP address (e.g., from your router dashboard or by running `hostname -I` directly on the board). 

Connect from your developer machine using SSH:

```bash
ssh username@<jetson_ip_address>
```

*(Replace `username` with your Jetson system user, e.g. `nvidia` or `jetson`, and `<jetson_ip_address>` with the actual IP address.)*

---

## 3. Step 2: Install System Dependencies

Update the package lists and install basic build tools, compilers, and SQLite/Python packages. Python native modules (like `tree-sitter`) require compiler tools.

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    libsqlite3-dev \
    git \
    curl \
    build-essential \
    libopenblas-base \
    libopenmpi-dev
```

---

## 4. Step 3: Setup Ollama on Jetson

Ollama supports Linux ARM64 architectures and detects Jetson's integrated NVIDIA GPU under JetPack.

### Install Ollama
Run the official Linux installation script:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Verify Ollama Status
Check if the service is running:

```bash
sudo systemctl status ollama
```

### Pull the Model
Download the required model. Since the default configuration uses `llama3.2:1b`, pull that model:

```bash
ollama pull llama3.2:1b
```

To verify the installation and test the model:
```bash
ollama run llama3.2:1b "Hello, how are you?"
```
*(Type `/exit` to close the interactive session).*

---

## 5. Step 4: Configure PyTorch & CUDA Acceleration

`sentence-transformers` relies on PyTorch. Standard `pip install torch` will install a CPU-only version on ARM64 Linux, which will make embedding generation slow. To utilize the Jetson GPU, you must install NVIDIA's Jetson-optimized PyTorch wheels.

### 1. Identify your JetPack Version
Determine which version of JetPack you are running:
```bash
sudo apt-cache show nvidia-l4t-core | grep Version
```
* Or check `/etc/nv_tegra_release`.
  - JetPack 5.x = Ubuntu 20.04 (L4T 35.x)
  - JetPack 6.x = Ubuntu 22.04 (L4T 36.x)

### 2. Install PyTorch with GPU Support
NVIDIA hosts pre-built PyTorch wheel binaries. Refer to the [NVIDIA PyTorch for Jetson Forums Guide](https://forums.developer.nvidia.com/t/pytorch-for-jetson/72047) for the exact URLs. 

Example download and installation for **JetPack 6.0 (Python 3.10)**:
```bash
# Setup virtual environment first
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install prerequisite packages
pip install --upgrade pip
pip install setuptools testresources

# Download and install NVIDIA PyTorch wheel (example URL)
wget https://developer.download.nvidia.com/compute/redist/jp/v60/pytorch/torch-2.3.0a0+40ec155e.nv24.05-cp310-cp310-linux_aarch64.whl
pip install torch-2.3.0a0+40ec155e.nv24.05-cp310-cp310-linux_aarch64.whl
```

Example download and installation for **JetPack 5.1.2 (Python 3.8)**:
```bash
wget https://developer.download.nvidia.com/compute/redist/jp/v512/pytorch/torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl
pip install torch-2.1.0a0+41361538.nv23.06-cp38-cp38-linux_aarch64.whl
```

### 3. Verify PyTorch CUDA Detection
Check that PyTorch sees the Jetson GPU:
```bash
python3 -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```
**Expected Output:**
```text
CUDA Available: True
Device Name: NVIDIA Tegra Orin (or similar)
```

---

## 6. Step 5: Deploy Frontend Assets

Building the frontend directly on Jetson is not recommended because Node.js compilation on low-memory embedded boards can freeze or exhaust system RAM. Instead, build locally and copy the assets.

### Option A: Local Build & Deploy (Recommended)
1. On your **local developer machine**, run the build:
   ```bash
   cd Edge_minds/frontend
   npm run build
   ```
2. Compress and transfer the built directory (`frontend/dist/`) to the Jetson board using `scp` or `rsync`:
   ```bash
   # From your local machine
   rsync -avz dist/ username@<jetson_ip_address>:/home/username/Edge_minds/frontend/dist/
   ```

### Option B: Build Directly on Jetson
If you must build on the Jetson, install Node.js and NPM, then run the build locally:
```bash
# Add NodeSource repository (Node.js v20)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Build
cd /home/username/Edge_minds/frontend
npm install
npm run build
```

---

## 7. Step 6: Deploy Backend & Configure Application

### 1. Transfer Backend Files
Copy the `server/`, `scripts/`, `requirements.txt`, and `.env.prod` files from your local machine to the `/home/username/Edge_minds/` folder on your Jetson board.

Depending on your access method, choose one of the following options:

#### Option A: Direct Local Shell (If your local terminal has network access to the Jetson)
Run `rsync` or `scp` directly from your developer machine's terminal:
```bash
# From your local machine, sync backend folders
rsync -avz --exclude 'node_modules' --exclude '.git' --exclude '__pycache__' --exclude 'venv' --exclude 'index' \
  Edge_minds/ username@<jetson_ip_address>:/home/username/Edge_minds/
```

#### Option B: Using Git Clone (Recommended for Browser-based SSH)
If you are connected via a browser-based SSH window and cannot push files from your laptop, push your code to a Git repository (like a private GitHub repository) and clone it on the Jetson:
```bash
# On the Jetson SSH terminal
git clone https://github.com/your-username/your-repo.git /home/username/Edge_minds
```
*(If it is a private repository, you can configure a Personal Access Token or upload a deploy key to GitHub).*

#### Option C: Packaging and downloading via URL (For Browser-based SSH)
If you do not want to use Git, create a tarball/zip archive of the code on your developer machine, upload it to a temporary file host (e.g. `file.io`, a private server, or secure cloud storage), and download/extract it on the Jetson:
```bash
# 1. On your developer laptop, package the app:
tar -czf app.tar.gz --exclude="node_modules" --exclude=".git" --exclude="venv" --exclude="index" server/ scripts/ frontend/dist/ requirements.txt .env.prod

# 2. Upload app.tar.gz to your file host to get a download link.

# 3. On the Jetson SSH terminal, download and extract:
wget -O app.tar.gz "<your_download_link>"
mkdir -p /home/username/Edge_minds
tar -xzf app.tar.gz -C /home/username/Edge_minds/
```

#### Option D: Outbound SCP (Pulling files from your laptop)
If your developer laptop is running an SSH server (like OpenSSH) and is reachable from the Jetson board over the local network:
```bash
# On the Jetson SSH terminal (pull files from your laptop)
mkdir -p /home/username/Edge_minds
scp -r laptop_user@<laptop_ip_address>:/path/to/Edge_minds/* /home/username/Edge_minds/
```

### 2. Install Backend Dependencies
Log back into your Jetson SSH session and install the required Python packages into your virtual environment:

```bash
cd /home/username/Edge_minds
source venv/bin/activate

# Install requirements (excluding torch since we manually installed the CUDA version)
grep -v '^torch' requirements.txt | pip install -r /dev/stdin
```
*Note: `tree-sitter-languages` and `tree-sitter` binaries will compile automatically during this step. This may take a minute.*

### 3. Setup Production Configuration
Create a production `.env` file in the root directory `/home/username/Edge_minds/`:

```bash
cp .env.prod .env
```

Open `.env` using `nano` and configure the variables:
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
DB_PATH=./index/codegenome.db
MANIFEST_PATH=./index/manifest.json
ENV=prod

# Bind to 0.0.0.0 to receive external connections from other machines on the network
API_HOST=0.0.0.0
API_PORT=8000

# Set the path to the built frontend assets
FRONTEND_STATIC_DIR=frontend/dist
```

---

## 8. Step 7: Start CodeGenome-Edge

Now that configurations are set, start the server:

```bash
source venv/bin/activate
python -m uvicorn server.api.main:app --host 0.0.0.0 --port 8000
```

Open a web browser on your developer laptop and navigate to:
```text
http://<jetson_ip_address>:8000/
```
The CodeGenome-Edge dashboard should load and status checks should confirm Ollama connectivity.

---

## 9. Step 8: Configure as a Background System Service

To ensure the backend runs continuously in the background and starts automatically when the Jetson board boots up, create a `systemd` service file.

1. Create a new service file:
   ```bash
   sudo nano /etc/systemd/system/codegenome.service
   ```

2. Add the following configuration (replace `username` with your Jetson username):
   ```ini
   [Unit]
   Description=CodeGenome-Edge Server
   After=network.target ollama.service

   [Service]
   Type=simple
   User=username
   WorkingDirectory=/home/username/Edge_minds
   Environment="PATH=/home/username/Edge_minds/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
   ExecStart=/home/username/Edge_minds/venv/bin/python -m uvicorn server.api.main:app --host 0.0.0.0 --port 8000
   Restart=on-failure
   RestartSec=5s

   [Install]
   WantedBy=multi-user.target
   ```

3. Save the file (`Ctrl+O`, `Enter`, `Ctrl+X`).

4. Reload systemd daemon, start the service, and enable it on boot:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start codegenome
   sudo systemctl enable codegenome
   ```

5. Monitor server logs:
   ```bash
   journalctl -u codegenome.service -f -n 100
   ```

---

## 10. Troubleshooting & Optimizations

### Out of Memory (OOM) Errors
Jetson boards (especially 4GB or 8GB versions) can run out of memory when loading both Ollama models and PyTorch models.
- **Enable Swap Space**: Increase your Jetson swap size to at least 6-8 GB to handle spikes during repository parsing or LLM inference.
  ```bash
  # Check current swap
  free -h
  # Set up a 6GB swapfile (if missing or small)
  sudo fallocate -l 6G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
  ```

### CUDA Initialization Errors
If PyTorch reports CUDA is unavailable despite installing the NVIDIA wheel:
- Confirm that your user is a member of the `video` group:
  ```bash
  sudo usermod -aG video $USER
  ```
  *(Log out and log back in for group changes to apply).*
- Preload the Jetson CUDA drivers:
  ```bash
  export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
  ```

### Slow Embedding Generation
If repository scanning is too slow:
- Verify that PyTorch is running the HuggingFace model on CUDA by ensuring logs do not throw CPU fallbacks.
- You can change your Python start script or shell environment to limit thread counts:
  ```env
  OMP_NUM_THREADS=4
  MKL_NUM_THREADS=4
  ```
