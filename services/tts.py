import threading
import numpy as np
import sounddevice as sd
from TTS.api import TTS

class TTSService:
    def __init__(self):
        self._ready = False
        self._loading = False
        self._engine = None
        self._speaker = None
        self._sr = 22050

    def init_async(self):
        if self._ready or self._loading:
            return
        self._loading = True
        def worker():
            try:
                eng = TTS(model_name="tts_models/en/vctk/vits", gpu=False)
                speakers = getattr(eng, "speakers", []) or []
                self._engine = eng
                self._speaker = speakers[5] if len(speakers) > 5 else (speakers[0] if speakers else None)
                synth = getattr(eng, "synthesizer", None)
                self._sr = getattr(synth, "output_sample_rate", 22050)
                self._ready = True
            except Exception:
                self._ready = False
            finally:
                self._loading = False
        threading.Thread(target=worker, daemon=True).start()

    def speak(self, text: str | None):
        if not text:
            return
        if not self._ready:
            self.init_async()
            return
        def worker():
            try:
                wav = self._engine.tts(text, speaker=self._speaker)
                wav = np.asarray(wav, dtype=np.float32)
                wav *= 2.0
                wav = np.clip(wav, -1.0, 1.0)
                wav = wav[: int(len(wav) * 0.95)]
                try:
                    sd.stop()
                except Exception:
                    pass
                sd.play(wav, self._sr, blocking=False)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def stop(self):
        try:
            sd.stop()
        except Exception:
            pass