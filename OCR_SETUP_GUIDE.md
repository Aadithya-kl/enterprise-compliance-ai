# Tesseract OCR Installation and Setup Guide

This guide explains how to install and configure Tesseract OCR for use with the Enterprise Compliance AI Platform in development, production (Linux), and Render hosting environments.

---

## 1. Windows Installation (Development Environment)

1. **Download the Installer**:
   Download the latest 64-bit installer for Windows from the [UB Mannheim Tesseract Repository](https://github.com/UB-Mannheim/tesseract/wiki).
2. **Run the Installer**:
   Follow the setup wizard. By default, it installs to:
   ```text
   C:\Program Files\Tesseract-OCR
   ```
3. **Configure the Environment PATH**:
   * Open the Start Menu, search for **Edit the system environment variables**, and open it.
   * Click **Environment Variables...**.
   * Under **System variables**, select the `Path` variable and click **Edit...**.
   * Click **New** and add the path to the installation folder:
     ```text
     C:\Program Files\Tesseract-OCR
     ```
   * Click **OK** to save and close all dialogs.
4. **Verification**:
   Open a new PowerShell or Command Prompt window and run:
   ```powershell
   tesseract --version
   ```
   If successful, it will print the installed version info.

---

## 2. Linux Installation (Ubuntu / Debian)

Run the following commands:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr libtesseract-dev
```

Verify the installation:
```bash
tesseract --version
```

---

## 3. Render Deployment Setup

When deploying to Render, the container or runtime must have access to the Tesseract binary.

### Option A: Deploying via Docker (Recommended)
If your application uses a `Dockerfile` on Render, append the following dependencies to your package installs:

```dockerfile
# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*
```

### Option B: Deploying via Render native Python Environment
Add a custom build script or use the **Render Apt Buildpack** to fetch Tesseract binaries before building:
1. In your Render Dashboard, navigate to **Settings** for the service.
2. In the **Buildpacks** section, add:
   ```text
   https://github.com/render-examples/apt-buildpack.git
   ```
3. Create an `Aptfile` in the root of your repository and list the package dependencies:
   ```text
   tesseract-ocr
   tesseract-ocr-eng
   libtesseract-dev
   ```

---

## 4. Python Integration

The application utilizes `pytesseract` to wrap CLI calls.
If Tesseract is installed but the binary is not in the system's `PATH`, you can set the environment variable:
```env
TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```
Or the app will attempt to locate it automatically using standard binary paths.
If the binary is missing entirely, image OCR will log a warning and return empty content, letting the rest of the ingestion process continue without crashing.
