import re
import json
import random
from pathlib import Path
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import sp
from VocaApp.ui.widgets import RoundedButton as Button
from VocaApp.services.tts import TTSService
from VocaApp.services.stt import STTService
from VocaApp.persistence.progress_store import ProgressStore
from .dictionary import DictionaryScreen
from .expressions import ExpressionsScreen
from .learn import LearnScreen
from .review import ReviewScreen
from .dashboard import DashboardScreen

class VocabularyApp(DictionaryScreen, ExpressionsScreen, LearnScreen, ReviewScreen, DashboardScreen, BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 20
        self.spacing = 20

        self.theme = {
            "bg": (0.07, 0.08, 0.10, 1),
            "surface": (0.12, 0.14, 0.18, 1),
            "text": (0.95, 0.98, 1, 1),
            "muted": (0.78, 0.82, 0.88, 1),
            "primary": (0.20, 0.52, 0.90, 1),
            "success": (0.25, 0.65, 0.38, 1),
            "warning": (0.93, 0.65, 0.25, 1),
            "danger": (0.85, 0.32, 0.35, 1),
            "accent": (0.55, 0.32, 0.75, 1),
            "closeButton": (0.5, 0.5, 0.5, 1),
        }
        self.tongue_twisters: set[str] = set()
        self.font_meanings_header = 35
        self.font_meaning_input = 30
        self.font_example_input = 30
        self.font_meanings_buttons = 30
        self.font_text_check_input = 26
        self.font_expr_phrase_input = 26
        self.font_ipa_name = None
        try:
            # Kandidatenpfade durchprobieren (erstes existierendes File wird genommen)
            candidates = [
                Path(__file__).with_name("fonts") / "DoulosSIL-Regular.ttf",                    # screens/fonts
                Path(__file__).resolve().parents[1] / "res" / "fonts" / "DoulosSIL-Regular.ttf" # res/fonts
            ]
            for p in candidates:
                if p.exists():
                    LabelBase.register(name="IPAFont", fn_regular=str(p))
                    self.font_ipa_name = "IPAFont"
                    print(f"[IPA] Font geladen: {p}")
                    break
            if not self.font_ipa_name:
                print("[IPA] Kein IPA-Font gefunden. Lege DoulosSIL-Regular.ttf in screens/fonts/ ab.")
        except Exception as e:
            print(f"[IPA] Registrierung fehlgeschlagen: {e}")

        with self.canvas.before:
            Color(*self.theme["bg"])
            self.rect = Rectangle(size=Window.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # Daten laden
        vocab_json = Path(__file__).resolve().parent.parent / "res" / "b1_word_from_cambridge.json"
        self.vocabulary = self.load_vocabulary_from_json(vocab_json)
        if not self.vocabulary:
            self.show_error_popup("Keine Vokabeln gefunden. Bitte B1.py ausführen.")
            return

        self.displayed_words = set()
        self.current_word = None
        self.known_words = set()
        self.new_words = set()
        self.known_sequence = []
        self.new_sequence = []
        self.user_words = set()
        self.removed_words = set()
        self.learned_session = []
        self.learn_order_mode = "Zufällig"
        self.learned_log: dict[str, str] = {}
        self.word_details: dict[str, list[dict]] = {}
        self.word_ipa: dict[str, str] = {}
        self.pos_tags = ("n", "v", "adj", "adv", "prep", "conj")
        self.expressions: list[str] = []
        self.word_history = []
        self.history_index = -1
        self.max_history = 300
        self._eligible_pool: list[str] = []
        self._eligible_dirty = True
        self._lists_update_scheduled = False
        self.remaining_count = 0
        self.auto_mark_known_on_next = True

        # Services
        self.tts = TTSService()
        self.stt = STTService(model_size="base")
        Clock.schedule_once(lambda dt: self.tts.init_async(), 0)

        # Persistenz
        self.progress_file = Path(__file__).resolve().parent.parent / "res" / "voca_progress.json"
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        self._store = ProgressStore(self, self.progress_file)
        self._store.load()

        # UI
        self._build_ui()
        self._recompute_remaining()
        self.update_display()
        self.update_lists()

    # ---- UI building (Header, Labels, Lists, Buttons) ----
    def _build_ui(self):
        header = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.2),
            padding=(6, 6, 6, 4),
            spacing=6
        )
        self.add_words_button = Button(text="Neue Wörter", font_size=22, size_hint=(None, 1), width=220, background_color=self.theme["success"])
        self.add_words_button.bind(on_press=self.open_add_words_popup)
        self.words_button = Button(text="Neue Wörter von Text überprüfen", font_size=22, size_hint=(1, 1), background_color=self.theme["primary"])
        self.words_button.bind(on_press=self.open_text_check_popup)
        self.expressions_button = Button(text="Redewendungen", font_size=22, size_hint=(None, 1), width=220, background_color=self.theme["accent"])
        self.expressions_button.bind(on_press=self.open_expressions_popup)
        self.learn_button = Button(text="Lernen", font_size=22, size_hint=(None, 1), width=160, background_color=self.theme["warning"])
        self.learn_button.bind(on_press=self.open_learn_mode)
        self.learned_main_btn = Button(text="Gelernte Wörter", font_size=22, size_hint=(None, 1), width=220, background_color=self.theme["surface"], color=self.theme["text"])
        self.learned_main_btn.bind(on_release=lambda *_: self.open_all_learned_popup(initial_only_tw=False))
        self.review_main_btn = Button(text="Wiederholen", font_size=22, size_hint=(None, 1), width=180, background_color=self.theme["surface"], color=self.theme["text"])
        self.review_main_btn.bind(on_release=self.open_review_popup)
        self.dashboard_btn = Button(text="Dashboard", font_size=22, size_hint=(None, 1), width=200, background_color=self.theme["surface"], color=self.theme["text"])
        self.dashboard_btn.bind(on_release=self.open_dashboard_popup)
        header.add_widget(self.add_words_button)
        header.add_widget(self.words_button)
        header.add_widget(self.expressions_button)
        header.add_widget(self.learn_button)
        header.add_widget(self.learned_main_btn)
        header.add_widget(self.review_main_btn)
        header.add_widget(self.dashboard_btn)
        self.add_widget(header)

        self.word_label = Label(text="Klicke auf 'Nächstes Wort' um zu beginnen", font_size=sp(64), size_hint=(1, 0.4), color=self.theme["text"])
        self.add_widget(self.word_label)
        self.progress_label = Label(text="0 Wörter verbleibend", font_size=sp(22), size_hint=(1, 0.1), color=(0.8, 0.8, 0.8, 1))
        self.add_widget(self.progress_label)

        button_layout = BoxLayout(size_hint=(1, 0.15), spacing=10)
        self.remove_button = Button(text="Entfernen", font_size=30, background_color=(0.8, 0.3, 0.3, 1))
        self.remove_button.bind(on_press=self.remove_current_word)
        button_layout.add_widget(self.remove_button)
        self.next_button = Button(text="Nächstes Wort", font_size=30, background_color=(0.4, 0.8, 0.4, 1))
        self.next_button.bind(on_press=self.next_word)
        button_layout.add_widget(self.next_button)
        self.add_widget(button_layout)

        classify_layout = BoxLayout(size_hint=(1, 0.12), spacing=10)
        self.known_button = Button(text="Korrigiere", font_size=30, background_color=(0.2, 0.6, 0.9, 1))
        self.known_button.bind(on_press=self.open_correct_word_popup)
        classify_layout.add_widget(self.known_button)
        self.unknown_button = Button(text="Neu / Unsicher", font_size=30, background_color=(0.9, 0.6, 0.2, 1))
        self.unknown_button.bind(on_press=self.mark_new)
        classify_layout.add_widget(self.unknown_button)
        self.add_widget(classify_layout)

        lists_layout = BoxLayout(size_hint=(1, 0.40), spacing=10)
        left_box = BoxLayout(orientation='vertical')
        self.known_header_btn = Button(text="Bekannte Wörter (0/0)", size_hint=(1, 0.12), font_size=24, background_normal='', background_color=(0.0, 0.35, 0.0, 1), color=(0.95, 0.98, 1, 1))
        self.known_header_btn.bind(on_release=self.open_known_list_popup)
        left_box.add_widget(self.known_header_btn)
        self.known_container = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=(0,4))
        self.known_container.bind(minimum_height=self.known_container.setter('height'))
        known_scroll = ScrollView(size_hint=(1, 0.88)); known_scroll.add_widget(self.known_container)
        left_box.add_widget(known_scroll)
        lists_layout.add_widget(left_box)

        mid_box = BoxLayout(orientation='vertical', size_hint=(0.18, 1), spacing=8, padding=4)
        self.to_new_btn = Button(text=">>", halign='center', valign='middle', disabled=True, color=(0.1,0.1,0.1,1))
        self.to_new_btn.bind(on_press=lambda *_: self.move_to_new())
        self.to_known_btn = Button(text="<<", halign='center', valign='middle', disabled=True, color=(0.1,0.1,0.1,1))
        self.to_known_btn.bind(on_press=lambda *_: self.move_to_known())
        self.to_remove_btn = Button(text="x", halign='center', valign='middle', background_color=(0.6, 0.2, 0.2, 1), disabled=True)
        self.to_remove_btn.bind(on_press=lambda *_: self.remove_selected_word())
        mid_box.add_widget(self.to_new_btn); mid_box.add_widget(self.to_known_btn); mid_box.add_widget(self.to_remove_btn)
        lists_layout.add_widget(mid_box)

        right_box = BoxLayout(orientation='vertical')
        self.new_header_btn = Button(text="Neue Wörter (0/0)", size_hint=(1, 0.12), font_size=24, background_normal='', background_color=(0.45, 0.28, 0.0, 1), color=(0.95, 0.98, 1, 1))
        self.new_header_btn.bind(on_release=self.open_new_list_popup)
        right_box.add_widget(self.new_header_btn)
        self.new_container = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=(0,4))
        self.new_container.bind(minimum_height=self.new_container.setter('height'))
        new_scroll = ScrollView(size_hint=(1, 0.88)); new_scroll.add_widget(self.new_container)
        right_box.add_widget(new_scroll)
        lists_layout.add_widget(right_box)

        removed_box = BoxLayout(orientation='vertical')
        self.removed_header_btn = Button(text="Entfernte Wörter (0)", size_hint=(1, 0.12), font_size=20, background_normal='', background_color=(0.25, 0.0, 0.0, 1), color=(0.95, 0.98, 1, 1))
        removed_box.add_widget(self.removed_header_btn)
        self.removed_container = GridLayout(cols=1, spacing=4, size_hint_y=None, padding=(0,4))
        self.removed_container.bind(minimum_height=self.removed_container.setter('height'))
        removed_scroll = ScrollView(size_hint=(1, 0.88)); removed_scroll.add_widget(self.removed_container)
        removed_box.add_widget(removed_scroll)
        lists_layout.add_widget(removed_box)
        self.add_widget(lists_layout)

        self.selected_word = None
        self.selected_origin = None
        self.selected_button = None

        # Einheitliches Layout/Umbruch für alle Top-Buttons
        def _style_top(btn):
            if not btn:
                return
            try:
                # gleiche Breite (gleichmäßig verteilen)
                btn.size_hint_x = 1
                # Text umbrechen und mittig ausrichten
                btn.halign = 'center'
                btn.valign = 'middle'
                btn.padding = (8, 4)
                # beim Größenwechsel den Textbereich anpassen (aktiviert Umbruch)
                btn.bind(size=lambda inst, _v: setattr(inst, 'text_size', (inst.width - 12, inst.height - 8)))
            except Exception:
                pass

        for name in (
            "add_words_button",
            "text_check_button",
            "learn_button",
            "learned_button",
            "correct_button",
            "review_button",
            "dashboard_button",
        ):
            _style_top(getattr(self, name, None))

    # ---- Helpers, IO ----
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def load_vocabulary_from_json(self, json_path) -> list[str]:
        p = Path(json_path)
        if not p.exists():
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            items = obj.get("words", []) if isinstance(obj, dict) else obj
            out, seen = [], set()
            for w in items or []:
                if not isinstance(w, str):
                    continue
                s = w.strip()
                if len(s) < 2:
                    continue
                lw = s.lower()
                if lw not in seen:
                    seen.add(lw)
                    out.append(s)
            return sorted(out, key=str.lower)
        except Exception:
            return []

    def _rebuild_eligible_pool(self):
        removed_lower = set(self.removed_words)
        known_lower = {w.lower() for w in self.known_words}
        new_lower = {w.lower() for w in self.new_words}
        shown_lower = {w.lower() for w in self.displayed_words}
        self._eligible_pool = [
            w for w in self.vocabulary
            if (w.lower() not in shown_lower)
            and (w.lower() not in known_lower)
            and (w.lower() not in new_lower)
            and (w.lower() not in removed_lower)
        ]
        self._eligible_dirty = False

    def _recompute_remaining(self):
        removed_lower = set(self.removed_words)
        known_lower = {w.lower() for w in self.known_words}
        new_lower = {w.lower() for w in self.new_words}
        shown_lower = {w.lower() for w in self.displayed_words}
        self.remaining_count = sum(
            1 for w in self.vocabulary
            if (w.lower() not in shown_lower)
            and (w.lower() not in known_lower)
            and (w.lower() not in new_lower)
            and (w.lower() not in removed_lower)
        )

    def schedule_update_lists(self):
        if getattr(self, "_lists_update_scheduled", False):
            return
        self._lists_update_scheduled = True
        self._eligible_dirty = True
        Clock.schedule_once(self._run_update_lists, 0)

    def _run_update_lists(self, dt):
        self._lists_update_scheduled = False
        self.update_lists()

    def get_random_word(self):
        if self._eligible_dirty:
            self._rebuild_eligible_pool()
        if not self._eligible_pool:
            return None
        i = random.randrange(len(self._eligible_pool))
        self._eligible_pool[i], self._eligible_pool[-1] = self._eligible_pool[-1], self._eligible_pool[i]
        return self._eligible_pool.pop()

    def remove_current_word(self, *_):
        if not self.current_word:
            return
        lw = self.current_word.lower()
        self.removed_words.add(lw)
        self.known_words.discard(self.current_word)
        self.new_words.discard(self.current_word)
        try:
            self.known_sequence.remove(self.current_word)
        except ValueError:
            pass
        try:
            self.new_sequence.remove(self.current_word)
        except ValueError:
            pass
        self.learned_session = [x for x in self.learned_session if x.lower() != lw]
        self.next_word(None)

    def next_word(self, instance):
        if getattr(self, "auto_mark_known_on_next", False):
            prev = self.current_word
            if prev and prev not in self.new_words and prev not in self.known_words and prev.lower() not in self.removed_words:
                self.known_words.add(prev)
                if prev not in self.known_sequence:
                    self.known_sequence.append(prev)
                self.schedule_update_lists()
                self._store.save_async()
        new_word = self.get_random_word()
        if new_word is None:
            self.current_word = None
            self.next_button.disabled = True
            # nichts anzeigen
            if getattr(self, "word_label", None):
                self.word_label.text = ""
            self.progress_label.text = f"{self.remaining_count} Wörter verbleibend"
            return
        self.displayed_words.add(new_word)
        self.word_history.append(new_word)
        if len(self.word_history) > self.max_history:
            self.word_history = self.word_history[-self.max_history:]
        self.history_index = len(self.word_history) - 1
        self.current_word = new_word
        if self.remaining_count > 0:
            self.remaining_count -= 1
        self.update_display()
        self.schedule_update_lists()
        self._store.save_async()

    def previous_word(self, instance):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_word = self.word_history[self.history_index]
            self.update_display()
            self._store.save_async()

    def update_display(self):
        # Fortschritt immer aktualisieren
        self.progress_label.text = f"{self.remaining_count} Wörter verbleibend"
        if self.remaining_count <= 0:
            # nichts anzeigen, Button sperren
            if getattr(self, "word_label", None) and self.word_label.text:
                self.word_label.text = ""
            self.next_button.disabled = True
            return
        # es gibt noch Wörter → aktuelles Wort anzeigen
        if self.current_word and getattr(self, "word_label", None) and self.word_label.text != self.current_word:
            self._animate_word_change(self.current_word)
        self.next_button.disabled = False

    def _animate_word_change(self, new_text: str):
        lbl = getattr(self, "word_label", None)
        if not lbl:
            return
        Animation.cancel_all(lbl)
        fade_out = Animation(opacity=0.0, duration=0.10)
        def _set_and_fade_in(*_):
            lbl.text = new_text
            Animation(opacity=1.0, duration=0.12).start(lbl)
        fade_out.bind(on_complete=lambda *_: _set_and_fade_in())
        fade_out.start(lbl)

    def show_error_popup(self, message, duration: float | None = None):
        popup = Popup(title='Hinzugefügt', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()
        if duration:
            Clock.schedule_once(lambda *_: popup.dismiss(), duration)

    def _unique_preserve_order(self, items):
        seen, out = set(), []
        for w in items:
            if w not in seen:
                seen.add(w)
                out.append(w)
        return out

    def update_lists(self):
        removed_lower = set(self.removed_words)
        total = sum(1 for w in self.vocabulary if w.lower() not in removed_lower)
        ordered_known = self._unique_preserve_order([w for w in self.known_sequence if w.lower() not in removed_lower])
        for w in self.known_words:
            if w not in ordered_known and w.lower() not in removed_lower:
                ordered_known.append(w)
        ordered_new = self._unique_preserve_order([w for w in self.new_sequence
            if (w in self.new_words and w not in self.known_words and w.lower() not in removed_lower)])
        for w in self.new_words:
            if w not in ordered_new and w not in self.known_words and w.lower() not in removed_lower:
                ordered_new.append(w)
        ordered_known = list(reversed(ordered_known))
        ordered_new = list(reversed(ordered_new))
        self.known_container.clear_widgets()
        for w in ordered_known:
            self.known_container.add_widget(self._make_word_button(w, 'known'))
        self.new_container.clear_widgets()
        for w in ordered_new:
            self.new_container.add_widget(self._make_word_button(w, 'new'))
        removed_display = sorted([w for w in self.vocabulary if w.lower() in removed_lower], key=lambda x: x.lower())
        self.removed_container.clear_widgets()
        for w in removed_display:
            self.removed_container.add_widget(self._make_removed_button(w))
        self.removed_header_btn.text = f"Entfernte Wörter ({len(removed_display)})"
        known_count = sum(1 for w in self.known_words if w.lower() not in removed_lower)
        new_count = sum(1 for w in (self.new_words - self.known_words) if w.lower() not in removed_lower)
        self.known_header_btn.text = f"Bekannte Wörter ({known_count}/{total})"
        self.new_header_btn.text = f"Neue Wörter ({new_count}/{total})"
        self.clear_selection()

    def _make_word_button(self, word, origin):
        btn = Button(
            text=word, size_hint_y=None, height=44, font_size=20,
            background_normal='', background_color=(0.18, 0.18, 0.18, 1) if origin == 'known' else (0.20, 0.18, 0.12, 1),
            color=self.theme["text"]
        )
        btn.bind(on_release=lambda inst: self.select_word(word, origin, inst))
        return btn

    def _make_removed_button(self, word):
        btn = Button(
            text=word, size_hint_y=None, height=44, font_size=20,
            background_normal='', background_color=(0.16, 0.05, 0.07, 1), color=(0.95, 0.9, 0.9, 1)
        )
        def on_touch(inst, touch):
            if inst.collide_point(*touch.pos) and getattr(touch, "is_double_tap", False):
                self.restore_removed_word(word)
                return True
            return False
        btn.bind(on_touch_down=on_touch)
        return btn

    def select_word(self, word, origin, button):
        if getattr(self, "selected_button", None):
            if self.selected_origin == 'known':
                self.selected_button.background_color = (0.18, 0.18, 0.18, 1)
            else:
                self.selected_button.background_color = (0.20, 0.18, 0.12, 1)
        self.selected_word = word
        self.selected_origin = origin
        self.selected_button = button
        button.background_color = (0.1, 0.4, 0.7, 1)
        self.to_new_btn.disabled = (origin != 'known')
        self.to_known_btn.disabled = (origin != 'new')
        self.to_remove_btn.disabled = False

    def move_to_known(self):
        if not self.selected_word or self.selected_origin != 'new':
            return
        w = self.selected_word
        self.new_words.discard(w)
        try:
            self.new_sequence.remove(w)
        except ValueError:
            pass
        if w not in self.known_words:
            self.known_words.add(w)
        if w not in self.known_sequence:
            self.known_sequence.append(w)
        self.clear_selection()
        self.schedule_update_lists()
        self._store.save_async()

    def move_to_new(self):
        if not self.selected_word or self.selected_origin != 'known':
            return
        w = self.selected_word
        self.known_words.discard(w)
        try:
            self.known_sequence.remove(w)
        except ValueError:
            pass
        if w not in self.new_words:
            self.new_words.add(w)
        if w not in self.new_sequence:
            self.new_sequence.append(w)
        self.clear_selection()
        self.schedule_update_lists()
        self._store.save_async()

    def clear_selection(self):
        self.selected_word = None
        self.selected_origin = None
        self.selected_button = None
        self.to_new_btn.disabled = True
        self.to_known_btn.disabled = True
        self.to_remove_btn.disabled = True

    def remove_selected_word(self):
        if not self.selected_word:
            return
        w = self.selected_word
        lw = w.lower()
        self.removed_words.add(lw)
        self.known_words.discard(w)
        self.new_words.discard(w)
        try:
            self.known_sequence.remove(w)
        except ValueError:
            pass
        try:
            self.new_sequence.remove(w)
        except ValueError:
            pass
        self.learned_session = [x for x in self.learned_session if x.lower() != lw]
        self.learned_log.pop(lw, None)
        self.clear_selection()
        self.schedule_update_lists()
        self.update_display()
        self._store.save_async()

    def restore_removed_word(self, word: str):
        lw = (word or "").lower()
        if lw in self.removed_words:
            self.removed_words.discard(lw)
            self.known_words.discard(word)
            if word not in self.new_words:
                self.new_words.add(word)
            if word not in self.new_sequence:
                self.new_sequence.append(word)
            self.current_word = word
            self.displayed_words.add(word)
            if not self.word_history or self.word_history[-1] != word:
                self.word_history.append(word)
                if len(self.word_history) > self.max_history:
                    self.word_history = self.word_history[-self.max_history:]
                self.history_index = len(self.word_history) - 1
            self.schedule_update_lists()
            self.update_display()
            self._store.save_async()

    def open_known_list_popup(self, *_):
        words = list(self.known_sequence)
        for w in self.known_words:
            if w not in words:
                words.append(w)
        words = list(reversed(words))
        words = [w for w in words if w.lower() not in self.removed_words]
        self._open_list_popup("Bekannte Wörter", words, show_tt_filter=True, initial_only_tw=False)

    def open_new_list_popup(self, *_):
        words = [w for w in self.new_sequence if w in self.new_words and w not in self.known_words]
        for w in self.new_words:
            if w not in words and w not in self.known_words:
                words.append(w)
        words = list(reversed(words))
        words = [w for w in words if w.lower() not in self.removed_words]
        self._open_list_popup("Neue Wörter", words)

    def _open_list_popup(self, title, words, *, show_tt_filter: bool = False, initial_only_tw: bool = False):
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        header_lbl = Label(text=f"{title} — {len(words)}", font_size=28, size_hint=(1, 0.08), color=(0.95,0.98,1,1))
        root.add_widget(header_lbl)
        search_row = BoxLayout(size_hint=(1, 0.1), spacing=8)
        search_input = TextInput(hint_text="Suchen...", multiline=False, font_size=20, size_hint=(1, 1))
        search_row.add_widget(search_input)
        tt_filter_btn = None
        if show_tt_filter:
            tt_filter_btn = ToggleButton(text="Tongue‑twister", size_hint=(None, 1), width=220, state='down' if initial_only_tw else 'normal')
            search_row.add_widget(tt_filter_btn)
        root.add_widget(search_row)
        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(0, 4))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)
        def rebuild_list(query_text: str):
            grid.clear_widgets()
            q = (query_text or "").strip().lower()
            only_tw = (tt_filter_btn is not None and tt_filter_btn.state == 'down')
            filtered = [w for w in words if (not q or q in w.lower()) and (not only_tw or (w.lower() in self.tongue_twisters))]
            header_lbl.text = f"{title} — {len(filtered)}" + (" • TT" if only_tw else "")
            max_items = 400
            for w in filtered[:max_items]:
                btn = Button(
                    text=w, size_hint_y=None, height=56, font_size=32,
                    background_normal='', background_color=(0, 0, 0, 0),
                    color=(0.95,0.98,1,1), halign='left', valign='middle'
                )
                btn.text_size = (grid.width, None)
                grid.bind(width=lambda inst, val, b=btn: setattr(b, 'text_size', (val, None)))
                btn.bind(on_release=lambda *_x, word=w: self.open_dictionary_popup(word))
                grid.add_widget(btn)
            if len(filtered) > max_items:
                grid.add_widget(Label(text=f"… {len(filtered)-max_items} weitere …", size_hint_y=None, height=32, font_size=18, color=(0.8,0.8,0.8,1)))
        rebuild_list("")
        _pending = {"ev": None}
        def _debounced(*_):
            if _pending["ev"]:
                try: _pending["ev"].cancel()
                except Exception: pass
            _pending["ev"] = Clock.schedule_once(lambda dt: rebuild_list(search_input.text), 0.12)
        search_input.bind(text=lambda inst, val: _debounced())
        if tt_filter_btn is not None:
            tt_filter_btn.bind(state=lambda inst, val: _debounced())
        bar = BoxLayout(size_hint=(1, None), height=56, spacing=8)
        close_btn = Button(text="Schließen", font_size=18, size_hint=(1, 1), background_color=self.theme["closeButton"])
        bar.add_widget(close_btn)
        root.add_widget(bar)
        popup = Popup(title=title, content=root, size_hint=(0.95, 0.92), auto_dismiss=True)
        close_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.bind(on_dismiss=lambda *_: (_pending["ev"].cancel() if _pending["ev"] else None))
        popup.open()

    # --- Manuelle Wörter hinzufügen ---
    def open_add_words_popup(self, *_):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        info = Label(
            text="Füge neue Wörter ein, je Zeile (mit oder ohne '- ' am Anfang). Diese werden als 'Neu' gespeichert.",
            font_size=18, size_hint=(1, 0.12), color=(0.9, 0.95, 1, 1)
        )
        content.add_widget(info)
        self.add_words_input = TextInput(text="", multiline=True, font_size=30, size_hint=(1, 0.7))
        content.add_widget(self.add_words_input)
        bar = BoxLayout(size_hint=(1, 0.18), spacing=10)
        cancel_btn = Button(text="Abbrechen", font_size=20, background_color=self.theme["closeButton"])
        add_btn = Button(text="Hinzufügen (Neu)", font_size=20, background_color=(0.2, 0.6, 0.2, 1))
        bar.add_widget(cancel_btn); bar.add_widget(add_btn)
        content.add_widget(bar)
        self.add_popup = Popup(title="Neue Wörter hinzufügen", content=content, size_hint=(0.9, 0.9), auto_dismiss=True)
        cancel_btn.bind(on_release=lambda *_: self.add_popup.dismiss())
        add_btn.bind(on_release=self._commit_added_words)
        self.add_popup.open()

    def _commit_added_words(self, *_):
        txt = self.add_words_input.text or ""
        added = self._add_words_from_text(txt)
        try: self.add_popup.dismiss()
        except Exception: pass
        self.update_lists(); self.update_display()
        self._store.save_async()
        if added:
            self.show_error_popup(f"{added} neue Wörter hinzugefügt.", duration=2)

    def _add_words_from_text(self, text: str) -> int:
        lines = text.splitlines()
        existing_lower = set(w.lower() for w in self.vocabulary) | set(self.removed_words)
        to_add = []
        for raw in lines:
            s = (raw or "").strip()
            if not s:
                continue
            s = re.sub(r'^[\-\*\u2022]+\s*', '', s)
            s = s.replace("’", "'").replace("‘", "'")
            s = re.sub(r"[^A-Za-z'\-\s]", "", s)
            s = re.sub(r"\s*-\s*", "-", s)
            s = re.sub(r"-{2,}", "-", s)
            s = re.sub(r"^-+|-+$", "", s)
            s = re.sub(r"\s+", " ", s).strip()
            if len(s) < 2:
                continue
            w = s.lower()
            if w not in existing_lower:
                to_add.append(w)
                existing_lower.add(w)
        if not to_add:
            return 0
        self.user_words.update(to_add)
        self.vocabulary = sorted(set(self.vocabulary).union(to_add), key=lambda x: x.lower())
        for w in to_add:
            self.known_words.discard(w)
            if w not in self.new_words:
                self.new_words.add(w)
            if w not in self.new_sequence:
                self.new_sequence.append(w)
        return len(to_add)

    # --- Freitext prüfen ---
    def open_text_check_popup(self, *_):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)
        info = Label(
            text="Füge normalen Text ein. Es werden darin vorkommende Wörter\ngegen dein Vokabular geprüft (case-insensitive, Länge > 2).",
            font_size=30, size_hint=(1, 0.14), color=(0.9, 0.95, 1, 1)
        )
        content.add_widget(info)
        self.text_check_input = TextInput(text="", multiline=True, font_size=self.font_text_check_input, size_hint=(1, 0.68))
        content.add_widget(self.text_check_input)
        bar = BoxLayout(size_hint=(1, 0.18), spacing=10)
        cancel_btn = Button(text="Abbrechen", font_size=20, background_color=self.theme["closeButton"])
        check_btn = Button(text="Prüfen", font_size=20, background_color=(0.2, 0.6, 0.2, 1))
        bar.add_widget(cancel_btn); bar.add_widget(check_btn)
        content.add_widget(bar)
        self.text_check_popup = Popup(title="Wörter prüfen", content=content, size_hint=(0.95, 0.92), auto_dismiss=True)
        cancel_btn.bind(on_release=(lambda *_: self.text_check_popup.dismiss()))
        check_btn.bind(on_release=self._analyze_text_and_show_results)
        self.text_check_popup.open()

    def _analyze_text_and_show_results(self, *_):
        txt = self.text_check_input.text or ""
        uniques = self._extract_words_from_free_text(txt)
        existing_lower = set(w.lower() for w in self.vocabulary)
        unknown = [w for w in uniques if (w not in existing_lower and w not in self.removed_words)]
        known_in = [w for w in uniques if w in existing_lower]
        self.text_unknown_words = unknown

        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        header = Label(
            text=f"Im Text: {len(uniques)} unique • {len(unknown)} • Vorhanden: {len(known_in)}",
            font_size=20, size_hint=(1, 0.12), color=(0.95, 0.98, 1, 1)
        )
        root.add_widget(header)
        sv = ScrollView(size_hint=(1, 0.72))
        gl = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=(0, 6))
        gl.bind(minimum_height=gl.setter('height'))
        if unknown:
            for w in unknown:
                gl.add_widget(Label(text=w, size_hint_y=None, height=48, font_size=28, color=(0.95,0.98,1,1)))
        else:
            gl.add_widget(Label(text="Keine neuen Wörter gefunden.", size_hint_y=None, height=48, font_size=24, color=(0.6,0.9,0.7,1)))
        sv.add_widget(gl)
        root.add_widget(sv)
        bar = BoxLayout(size_hint=(1, 0.16), spacing=10)
        close_btn = Button(text="Schließen", font_size=20)
        add_btn = Button(text=f"Hinzufügen ({len(unknown)})", font_size=20, background_color=self.theme["closeButton"])
        add_btn.disabled = (len(unknown) == 0)
        bar.add_widget(close_btn); bar.add_widget(add_btn)
        root.add_widget(bar)
        self.text_check_popup.content = root
        close_btn.bind(on_release=lambda *_: self.text_check_popup.dismiss())
        add_btn.bind(on_release=self._commit_add_from_text_check)

    def _commit_add_from_text_check(self, *_):
        to_add = list(dict.fromkeys(getattr(self, "text_unknown_words", []) or []))
        if not to_add:
            try: self.text_check_popup.dismiss()
            except Exception: pass
            return
        to_add = [w for w in to_add if w.lower() not in self.removed_words]
        if to_add:
            self.user_words.update(to_add)
            self.vocabulary = sorted(set(self.vocabulary).union(to_add), key=lambda x: x.lower())
            self.remaining_count += len(to_add)
        self.schedule_update_lists()
        self.update_display()
        self._store.save_async()
        try: self.text_check_popup.dismiss()
        except Exception: pass
        self.show_error_popup(f"{len(to_add)} Wörter zum Vokabular hinzugefügt. Mit 'Nächstes Wort' kannst du sie einordnen.", duration=3)

    # --- Alle gelernten Wörter ---
    def open_all_learned_popup(self, *_, initial_only_tw: bool = False):
        if not self.learned_session and not self.expressions:
            self.show_error_popup("Keine gelernten Wörter oder Redewendungen vorhanden.")
            return
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        header = Label(text="", font_size=40, size_hint=(1, 0.08), color=(0.95,0.98,1,1))
        root.add_widget(header)
        search_row = BoxLayout(size_hint=(1, 0.08), spacing=8)
        search_input = TextInput(hint_text="Suchen...", multiline=False, font_size=20, size_hint=(1, 1))
        tt_filter_btn = ToggleButton(text="Tongue‑twister", size_hint=(None, 1), width=220, state='down' if initial_only_tw else 'normal')
        search_row.add_widget(search_input); search_row.add_widget(tt_filter_btn)
        root.add_widget(search_row)
        sv = ScrollView(size_hint=(1, 0.76))
        gl = GridLayout(cols=1, spacing=10, size_hint_y=None, padding=(0, 6))
        gl.bind(minimum_height=gl.setter('height'))
        sv.add_widget(gl)
        root.add_widget(sv)
        bar = BoxLayout(size_hint=(1, 0.08))
        close_btn = Button(text="Schließen", font_size=24, size_hint=(1, 1), background_color=self.theme["closeButton"])
        bar.add_widget(close_btn)
        root.add_widget(bar)
        self.learned_popup = Popup(title="Gelernte Wörter", content=root, size_hint=(0.95, 0.92), auto_dismiss=True)
        close_btn.bind(on_release=lambda *_: self.learned_popup.dismiss())

        def rebuild_list(query_text: str):
            gl.clear_widgets()
            q = (query_text or "").strip().lower()
            only_tw = (tt_filter_btn.state == 'down')
            words = list(reversed(self.learned_session))
            for expr in self.expressions:
                if expr not in words:
                    words.append(expr)
            filtered = [w for w in words if (not q or q in w.lower()) and (not only_tw or (w.lower() in self.tongue_twisters))]
            total = len(self.learned_session) + len(self.expressions)
            header.text = f"{total} Gelernte Wörter & Redewendungen" + (" • TT" if only_tw else "")

            if not filtered:
                gl.add_widget(Label(text="Keine Treffer.", size_hint_y=None, height=40, font_size=20, color=(0.8,0.8,0.8,1)))
                return

            # Performance: begrenzen + in Chunks zeichnen
            max_items = 300
            items = filtered[:max_items]
            overflow = len(filtered) - max_items

            # Optional: Lade-Hinweis
            gl.add_widget(Label(text="Lade …", size_hint_y=None, height=32, font_size=18, color=(0.8,0.8,0.8,1)))

            chunk = 40
            state = {"i": 0, "added_header": False}

            def add_chunk(dt=None):
                start = state["i"]
                end = min(start + chunk, len(items))
                if start == 0 and gl.children:
                    # Ersten Lade-Hinweis entfernen
                    try:
                        gl.remove_widget(gl.children[0])
                    except Exception:
                        pass
                for w in items[start:end]:
                    row = BoxLayout(orientation='horizontal', size_hint_y=None, height=56, spacing=6)
                    play_btn = Button(text='Hören', size_hint=(None, 1), width=80, font_size=24,
                                      background_normal='', background_color=(0.25,0.55,0.9,1))
                    play_btn.bind(on_release=lambda *_w, word=w: self._speak(word))
                    w_btn = Button(
                        text=w, font_size=35, size_hint=(1, None), height=56,
                        background_normal='', background_color=(0, 0, 0, 0), color=(0.95, 0.98, 1, 1),
                        halign='left', valign='middle'
                    )
                    w_btn.padding = (8, 0)
                    w_btn.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width, inst.height)))
                    w_btn.bind(on_release=lambda *_w, word=w: self.open_dictionary_popup(word))

                    row.add_widget(play_btn)
                    row.add_widget(w_btn)
                    gl.add_widget(row)

                    # IPA anzeigen (falls vorhanden)
                    _ipa = (self.word_ipa.get((w or "").lower(), "") or "").strip()
                    if _ipa:
                        self._add_wrapped_label(
                            gl, f"[IPA] {_ipa}", 24,
                            color=(0.8, 0.95, 0.9, 1),
                            indent_left=12,
                            font_name=self.font_ipa_name or None
                        )

                    # Bedeutungen/Beispiele anzeigen
                    entries = list(self.word_details.get((w or "").lower(), []) or [])
                    if not entries:
                        self._add_wrapped_label(gl, "– Keine Bedeutungen hinterlegt –", 20, color=(0.8, 0.8, 0.8, 1), indent_left=12)
                    else:
                        for idx, item in enumerate(entries, start=1):
                            meaning = (item.get("meaning", "") or "").strip()
                            ex_list = item.get("examples")
                            if not isinstance(ex_list, list):
                                ex_single = (item.get("example", "") or "").strip()
                                ex_list = [ex_single] if ex_single else []
                            pos = [p for p in (item.get("pos") or []) if isinstance(p, str)]
                            pos_str = f"({', '.join(pos)}) " if pos else ""
                            if meaning:
                                self._add_wrapped_label(gl, f"{idx}. {pos_str}{meaning}", 35, color=(0.9, 0.95, 1, 1), indent_left=12)
                            for ex in ex_list:
                                self._add_wrapped_label(gl, f"- {ex}", 30, color=(0.8, 0.9, 1, 1), indent_left=36)

                state["i"] = end
                if end < len(items):
                    Clock.schedule_once(add_chunk, 0)
                else:
                    if overflow > 0:
                        gl.add_widget(Label(text=f"… {overflow} weitere …", size_hint_y=None, height=32, font_size=18, color=(0.8,0.8,0.8,1)))

            add_chunk()

        self._learned_list_refresh = rebuild_list
        self._learned_list_search_widget = search_input
        rebuild_list(search_input.text)
        search_input.bind(text=lambda inst, val: rebuild_list(val))
        tt_filter_btn.bind(state=lambda inst, val: rebuild_list(search_input.text))

        def _cleanup_refs(*_):
            try:
                self._learned_list_refresh = None
                self._learned_list_search_widget = None
            except Exception:
                pass
        self.learned_popup.bind(on_dismiss=_cleanup_refs)
        self.learned_popup.open()

    def _refresh_learned_list_ui(self):
        fn = getattr(self, "_learned_list_refresh", None)
        popup = getattr(self, "learned_popup", None)
        if callable(fn) and popup is not None and popup.parent:
            try:
                query = ""
                si = getattr(self, "_learned_list_search_widget", None)
                if si: query = si.text or ""
                fn(query)
            except Exception:
                pass

    # Redewendungen-Popup live auffrischen (wie bei „Gelernte Wörter“)
    def _refresh_expressions_list_ui(self):
        reb = getattr(self, "_expr_rebuild", None)
        popup = getattr(self, "expressions_popup", None)
        if callable(reb) and popup is not None and popup.parent:
            try:
                q = ""
                si = getattr(self, "_expr_search_widget", None)
                if si:
                    q = si.text or ""
                reb(q)
            except Exception:
                pass

    def open_correct_word_popup(self, *_):
        if not self.current_word:
            self.show_error_popup("Kein Wort ausgewählt.")
            return
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        info = Label(text="Wort korrigieren und speichern:", font_size=18, size_hint=(1, 0.12), color=(0.9, 0.95, 1, 1))
        root.add_widget(info)
        self.correct_input = TextInput(text=self.current_word, multiline=False, font_size=22, size_hint=(1, 0.6))
        root.add_widget(self.correct_input)
        bar = BoxLayout(size_hint=(1, 0.18), spacing=10)
        cancel_btn = Button(text="Abbrechen", font_size=20, background_color=self.theme["closeButton"])
        save_btn = Button(text="Speichern", font_size=20, background_color=(0.2, 0.6, 0.2, 1))
        bar.add_widget(cancel_btn); bar.add_widget(save_btn)
        root.add_widget(bar)
        self.correct_popup = Popup(title="Wort korrigieren", content=root, size_hint=(0.9, 0.5), auto_dismiss=True)
        cancel_btn.bind(on_release=lambda *_: self.correct_popup.dismiss())
        save_btn.bind(on_release=self._commit_correction)
        self.correct_popup.open()

    def _commit_correction(self, *_):
        old = self.current_word
        new_raw = getattr(self, "correct_input", None).text if getattr(self, "correct_input", None) else ""
        new = self._sanitize_single_word(new_raw)
        if not new:
            self.show_error_popup("Ungültiges Wort.")
            return
        old_l, new_l = old.lower(), new.lower()
        if new_l in self.removed_words:
            self.show_error_popup("Dieses Wort ist als entfernt markiert.")
            return
        existing_lower_map = {}
        for w in self.vocabulary:
            wl = w.lower()
            if wl not in existing_lower_map:
                existing_lower_map[wl] = w
        if new_l == old_l:
            self._replace_word_everywhere(old, new)
        else:
            if new_l in existing_lower_map:
                canonical = existing_lower_map[new_l]
                self._merge_word_into_canonical(old, canonical)
                self.current_word = canonical
            else:
                self._replace_word_everywhere(old, new)
        try:
            if getattr(self, "correct_popup", None):
                self.correct_popup.dismiss()
        except Exception:
            pass
        self.update_lists(); self.update_display()
        self._store.save_async()
        self.show_error_popup("Gespeichert.", duration=2)

    def _replace_word_everywhere(self, old: str, new: str):
        if old != new:
            pass
        vocab_set = set(self.vocabulary)
        if old in vocab_set:
            vocab_set.discard(old)
        vocab_set.add(new)
        self.vocabulary = sorted(vocab_set, key=lambda x: x.lower())
        if old in self.known_words:
            self.known_words.discard(old); self.known_words.add(new)
        if old in self.new_words:
            self.new_words.discard(old)
            if new not in self.known_words:
                self.new_words.add(new)
        self.known_sequence = self._unique_preserve_order([new if w == old else w for w in self.known_sequence])
        self.new_sequence = self._unique_preserve_order([w for w in [new if w == old else w for w in self.new_sequence] if w not in self.known_words])
        if old in self.displayed_words:
            self.displayed_words.discard(old); self.displayed_words.add(new)
        self.word_history = [new if w == old else w for w in self.word_history]
        if hasattr(self, "user_words") and old in self.user_words:
            self.user_words.discard(old); self.user_words.add(new)
        try:
            ol, nl = (old or "").lower(), (new or "").lower()
            if ol in self.learned_log:
                if nl not in self.learned_log:
                    self.learned_log[nl] = self.learned_log[ol]
                self.learned_log.pop(ol, None)
        except Exception:
            pass
        self.learned_session = self._unique_preserve_order([new if w == old else w for w in self.learned_session])
        self._move_word_details(old, new)
        try:
            ol, nl = (old or "").lower(), (new or "").lower()
            if ol in self.tongue_twisters:
                self.tongue_twisters.discard(ol); self.tongue_twisters.add(nl)
        except Exception:
            pass
        self.current_word = new

    def _merge_word_into_canonical(self, old: str, canonical: str):
        if old in self.known_words:
            self.known_words.discard(old); self.known_words.add(canonical)
        if old in self.new_words:
            self.new_words.discard(old)
            if canonical not in self.known_words:
                self.new_words.add(canonical)
        self.known_sequence = [w for w in self.known_sequence if w != old]
        if canonical in self.known_words and canonical not in self.known_sequence:
            self.known_sequence.append(canonical)
        self.new_sequence = [w for w in self.new_sequence if w != old and w not in self.known_words]
        if canonical in self.new_words and canonical not in self.known_sequence and canonical not in self.new_sequence:
            self.new_sequence.append(canonical)
        if old in self.displayed_words:
            self.displayed_words.discard(old); self.displayed_words.add(canonical)
        self.word_history = [canonical if w == old else w for w in self.word_history]
        self.vocabulary = sorted({w for w in self.vocabulary if w != old}, key=lambda x: x.lower())
        if hasattr(self, "user_words") and old in self.user_words:
            self.user_words.discard(old)
        try:
            ol, cl = (old or "").lower(), (canonical or "").lower()
            if ol in self.learned_log and cl not in self.learned_log:
                self.learned_log[cl] = self.learned_log[ol]
            self.learned_log.pop(ol, None)
        except Exception:
            pass
        self.learned_session = self._unique_preserve_order([canonical if w == old else w for w in self.learned_session])
        self._move_word_details(old, canonical)
        try:
            ol, cl = (old or "").lower(), (canonical or "").lower()
            if ol in self.tongue_twisters:
                self.tongue_twisters.discard(ol); self.tongue_twisters.add(cl)
        except Exception:
            pass

    def _move_word_details(self, old: str, new: str):
        try:
            ol = (old or "").lower(); nl = (new or "").lower()
            if ol == nl:
                return
            src = self.word_details.get(ol)
            if src:
                dst = list(self.word_details.get(nl, []))
                dst.extend(src)
                self.word_details[nl] = dst
                try: del self.word_details[ol]
                except Exception: pass
            ipa = self.word_ipa.get(ol)
            if ipa:
                if nl not in self.word_ipa or not (self.word_ipa.get(nl) or "").strip():
                    self.word_ipa[nl] = ipa
                try: del self.word_ipa[ol]
                except Exception: pass
        except Exception:
            pass

    # ---- Services delegations ----
    def _init_tts_async(self):
        try:
            self.tts.init_async()
        except Exception:
            pass

    def _speak(self, text: str | None):
        try:
            self.tts.speak(text)
        except Exception:
            pass

    def _init_stt_async(self):
        try:
            self.stt.init_async()
        except Exception:
            pass
        
    def mark_new(self, *_):
        if not self.current_word:
            return
        w = self.current_word
        # Aus bekannt entfernen (falls vorhanden)
        if w in self.known_words:
            self.known_words.discard(w)
            try:
                self.known_sequence.remove(w)
            except ValueError:
                pass
        # In neu aufnehmen
        if w not in self.new_words:
            self.new_words.add(w)
        if w not in self.new_sequence:
            self.new_sequence.append(w)
        # UI und Persistenz
        self.schedule_update_lists()
        try:
            self._store.save_async()
        except Exception:
            pass

    def _add_wrapped_label(self, parent, text, font_size, color=(1,1,1,1), indent_left=0, font_name=None):
        # Label + Einrückung in eine eigene Zeile (BoxLayout)
        lbl = Label(
            text=text, font_size=font_size, color=color,
            halign='left', valign='top', size_hint_y=None
        )
        if font_name:
            lbl.font_name = font_name

        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=font_size + 8, spacing=4)
        spacer = Widget(size_hint=(None, 1), width=indent_left)
        row.add_widget(spacer)
        row.add_widget(lbl)
        parent.add_widget(row)

        def _recalc(*_):
            try:
                avail_w = max(10, parent.width - indent_left - 4)
                lbl.text_size = (avail_w, None)   # Wrap aktivieren
                lbl.texture_update()
                new_h = max(font_size + 6, lbl.texture_size[1] + 6)
                lbl.height = new_h                 # Label-Höhe setzen
                row.height = new_h                 # Zeilenhöhe MIT aktualisieren!
            except Exception:
                pass

        # Bei Breiten- und Texture-Änderung neu berechnen
        parent.bind(width=lambda *_: _recalc())
        lbl.bind(texture_size=lambda *_: _recalc())
        Clock.schedule_once(lambda dt: _recalc(), 0)