from kivy.clock import Clock
import threading
import numpy as np
import sounddevice as sd
import whisper

class STTService:
    def __init__(self, model_size: str = "small", sr: int = 16000):
        self._ready = False
        self._loading = False
        self._model = None
        self._sr = sr
        self._model_size = model_size

    def init_async(self):
        if self._ready or self._loading:
            return
        self._loading = True
        def worker():
            try:
                self._model = whisper.load_model(self._model_size)
                self._ready = True
            except Exception:
                self._ready = False
            finally:
                self._loading = False
        threading.Thread(target=worker, daemon=True).start()

    def record_and_transcribe(self, seconds: float, on_result):
        def worker():
            text, err = "", None
            try:
                if not self._ready:
                    self.init_async()
                    err = "Model is loading. Please tap ‘Speak’ again."
                    Clock.schedule_once(lambda dt: on_result(text, err), 0)
                    return
                try:
                    sd.stop()
                except Exception:
                    pass
                audio = sd.rec(int(seconds * self._sr), samplerate=self._sr, channels=1)
                sd.wait()
                audio = audio.flatten().astype(np.float32)
                m = float(np.max(np.abs(audio)) + 1e-9)
                audio = audio / m
                res = self._model.transcribe(audio, language="en")
                text = (res.get("text") or "").strip()
            except Exception as e:
                err = f"STT loading failed: {e}"
            Clock.schedule_once(lambda dt: on_result(text, err), 0)
        threading.Thread(target=worker, daemon=True).start()