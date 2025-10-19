# VocaApp — Kivy Vocabulary Learning App

A cross‑platform vocabulary learning app built with Python and Kivy. Add new words and expressions, edit meanings and examples, practice with Learn and Review modes, get pronunciation via AI Text-to-Speech, practice pronunciation via AI Speech-to-Text, and track your progress with a dashboard.

## About me
I developed this app as a beginner without formal software development experience. 
My Python knowledge comes from a computer vision course at my university. 
As a beginner, I welcome feedback and suggestions for improvement.


## Features

- Check your English level with B1 words from Cambridge
<p>
  <img src="images/start.png" alt="Start" width="360">
  <img src="images/mainscreen.png" alt="Main screen" width="360">
</p>

- Add and manage words  
![Manage meaning](images/meaningEditor.png)

- Review mode
  - Text‑to‑speech (TTS) playback
  - Speech‑to‑text (STT) to practice pronunciation
  - Flashcard
<p>
  <img src="images/reviewMode1.png" alt="Flashcard" width="360">
  <img src="images/reviewMode2.png" alt="Main screen" width="360">
</p>

- Dashboard
  - Bar charts for “Last 10 Days” and “Months”
  - Color‑coded bars (green = same/more than previous; red = less)
  - Navigation arrows for days/months  
![Dashboard](images/dashboard.png)

- Works on macOS and Windows (Python)

## Requirements

- Python 3.10 or newer
- Python packages (see requirements.txt):
  - kivy
  - sounddevice
  - TTS (Coqui TTS, requires torch)
  - torch
  - openai-whisper
- System dependencies
  - FFmpeg (required by Whisper)
  - PortAudio (used by sounddevice)
  - On Windows, Visual C++ Redistributable / Build Tools may be needed

## Installation

### 1) Clone the repository

```bash
git clone https://github.com/ad-tran/python-kivy-vocabulary-app.git
cd python-kivy-vocabulary-app
```

### 2) Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
```

Windows (PowerShell):

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip setuptools wheel
```

### 3) Install system dependencies

macOS (Homebrew):

```bash
brew install ffmpeg portaudio
```

Windows (Open PowerShell as Administrator for this step):

```PowerShell as Administrator
# choco
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
# FFmpeg
choco install ffmpeg
```

If sounddevice complains about PortAudio or build tools, install:
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

### 4) Install Python dependencies

(Windows: go back to normal cmd)

This might take a while because of the AI Models for Text-to-Speech and Speech-to-Text
From the repository root (where requirements.txt lives):

```bash
python -m pip install -r requirements.txt
```

GPU optional (Windows/NVIDIA): install a CUDA build of PyTorch instead of CPU wheels. Example:
```powershell
# Remove/skip torch from requirements first, then:
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

## Running the app

Option A — run the module:
```bash
python app.py
```

Option B — run the script app.py in python-kivy-vocabulary-app:
```bash
app.py
```

Notes:
- On first run, models for TTS (Coqui) and STT (Whisper) may download automatically.
- Grant microphone permissions to the terminal/IDE for STT on macOS and Windows.

## Troubleshooting

- “ffmpeg not found”
  - Ensure FFmpeg is installed and in PATH (see installation above).
- “No default output/input device” or sounddevice errors
  - Check audio devices and permissions. On macOS, grant microphone access in System Settings.
- PyTorch installation issues
  - Upgrade pip/setuptools/wheel, then reinstall. For GPU, install the matching CUDA wheel for your system.


## Contributing

Issues and pull requests are welcome. Please open an issue for bugs or feature requests.

## License

Choose an open‑source license (e.g., MIT) and add a LICENSE file to the repository.
