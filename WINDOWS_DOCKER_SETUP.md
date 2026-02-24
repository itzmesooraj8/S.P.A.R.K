# S.P.A.R.K. Windows Docker & Sandbox Setup Guide

Welcome to the **S.P.A.R.K. Sandbox Setup Guide** tailored specifically for Windows.

Your SPARK system is structurally sound, but the heavy analysis components (Flake8, Mypy, Bandit, Radon) are currently failing silently because Docker is not running correctly on your machine. This guide will walk you through exactly how to get Docker Desktop running properly on your Windows machine, so that the Heavy Scan engine can produce real metrics and drive the Risk Score.

## Step 1: Install & Configure Docker Desktop (Windows)

The error you received (`The system cannot find the file specified` when calling Docker via named pipes) usually means Docker is not installed, or the Docker Daemon is currently stopped.

1. **Download Docker Desktop for Windows**:
   - Go to [Docker Desktop Download](https://docs.docker.com/desktop/install/windows-install/) and download the installer.
2. **Install with WSL 2 Backend (Recommended)**:
   - Run the installer. When prompted, ensure that **"Use WSL 2 instead of Hyper-V"** is checked. WSL 2 provides much better performance and integration on modern Windows systems.
3. **Finish Installation & Restart**:
   - Complete the installation, which may require you to log out and log back in, or restart your computer.
4. **Start Docker Desktop**:
   - Search for **Docker Desktop** in your Windows Start menu and launch it.
   - Accept the terms if prompted. The Docker icon in your system tray (bottom right corner) should animate and eventually show that the Docker engine is running (a green status).

## Step 2: Verify Docker is Running

Once the Docker engine is fully started, verify that it responds correctly from your PowerShell or Command Prompt.

Open a terminal and run:
```powershell
docker info
```
*(You should see an output with details about your containers, images, and the Server endpoint rather than an error about a missing file / pipe.)*

Next, test it with:
```powershell
docker run -it --rm hello-world
```
*(If Docker is correctly installed and running, this will pull a tiny image and print a "Hello from Docker!" message.)*

## Step 3: Build the S.P.A.R.K. Sandbox Image

Now that Docker provides the environment, we must build the isolated sandbox where S.P.A.R.K. performs its analysis on codebases.

1. **Navigate to the sandbox directory**:
   Keep an eye on the directory paths, you want to be inside `spark_core/sandbox`.
   ```powershell
   cd c:\Users\itzme\Downloads\S.P.A.R.K\spark_core\sandbox
   ```

2. **Build the `spark-sandbox` image**:
   Run the following command exactly as written. This packages up the heavy analysis tools (flake8, mypy, bandit, radon) into a portable, secure container.
   ```powershell
   docker build -t spark-sandbox .
   ```
   *(Wait for this process to finish. It will pull a Python base image and install all the necessary static analysis packages.)*

## Step 4: Run S.P.A.R.K. & Verify Audits

With the heavy scanning container built and Docker running seamlessly on your host, the SPARK engine can now orchestrate real metric generation.

1. **Go back to your project root**:
   ```powershell
   cd c:\Users\itzme\Downloads\S.P.A.R.K
   ```

2. **Start the SPARK engine**:
   ```powershell
   python spark_core/main.py
   ```

### What to Expect Now
With the sandbox operational:
- When a codebase (like your `requests` clone) is scanned, S.P.A.R.K. will pass the files to `spark-sandbox` via Docker.
- S.P.A.R.K. will parse real `lint_errors`, `type_errors`, `known_vulnerabilities` and code `complexity` metrics.
- As actual metrics populate, you will see your **Risk Score update accurately** in the HUD, providing true structural awareness, replacing the silent `0` values.

---

**Troubleshooting Note**: If Docker complains about VT-X/AMD-v being disabled, you'll need to enable Hardware Virtualization in your computer's BIOS. If it complains about WSL 2 requiring an update, open PowerShell as Administrator and run `wsl --install` or `wsl --update`.
