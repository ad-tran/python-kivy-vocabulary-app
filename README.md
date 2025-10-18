# VocaApp — Kivy Vocabulary Learning App

A cross‑platform vocabulary learning app built with Python and Kivy. Add new words and expressions, edit meanings and examples, practice with Learn and Review modes, get pronunciation via TTS, and track your progress with a dashboard.

## Features

- Add and manage words
  - Meanings, parts of speech, examples
  - IPA display (optional)
- Expressions & phrases
  - Quick add dialog with multiple examples
- Learn mode
  - Order: Random, Newest, Oldest
  - Mark as learned, next, remove
- Review mode
  - Text‑to‑speech (TTS) playback
  - Speech‑to‑text (STT) to practice pronunciation
- Dictionary view
  - Word details, meanings, examples, IPA, TTS
- Dashboard
  - Bar charts for “Last 10 Days” and “Months”
  - Color‑coded bars (green = same/more than previous; red = less)
  - Navigation arrows for days/months
- Works on macOS and Windows (Python)

## Requirements

- Python 3.10 or newer
- Python packages (see requirements.txt):
  - kivy
  - numpy
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
git clone https://github.com/https://github.com/ad-tran/python-kivy-vocabulary-app.git
cd <your-repo>/VocaApp
```

Replace <your-user>/<your-repo> with your GitHub path.

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

Windows (choose one package manager):

```powershell
# FFmpeg
choco install ffmpeg -y
# or
winget install Gyan.FFmpeg
```

If sounddevice complains about PortAudio or build tools, install:
```powershell
winget install Microsoft.VisualStudio.2022.BuildTools
```

### 4) Install Python dependencies

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
python -m VocaApp.app
```

Option B — run the script:
```bash
python VocaApp/app.py
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
- Coqui TTS model download slow/fails
  - Try a stable network or pre‑download the model; ensure torch is installed correctly.

## Project structure (overview)

- VocaApp/app.py — Kivy App entrypoint
- VocaApp/screens/ — UI screens and logic
  - main.py, dashboard.py, review.py, learn.py, expressions.py, dictionary.py
- VocaApp/services/ — services (e.g., tts.py, stt.py)
- VocaApp/ui/ — custom widgets (e.g., charts, buttons)

## Contributing

Issues and pull requests are welcome. Please open an issue for bugs or feature requests.

## License

Choose an open‑source license (e.g., MIT) and add a LICENSE file to the repository.
