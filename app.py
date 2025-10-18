import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from kivy.app import App
from VocaApp.screens.main import VocabularyApp
from kivy.core.window import Window
Window.size = (800, 1000)

class VocaMainApp(App):
    def build(self):
        root = VocabularyApp()
        # ProgressStore am App-Objekt referenzieren (für Backups im on_stop)
        self.store = getattr(root, "_store", None)
        return root

    def on_stop(self):
        # final synchron speichern + Backup nur bei Änderungen
        try:
            if self.store:
                self.store.save_sync()
                self.store.backup_if_changed()
        except Exception:
            pass

if __name__ == "__main__":
    VocaMainApp().run()