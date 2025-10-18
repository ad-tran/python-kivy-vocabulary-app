from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.togglebutton import ToggleButton
from VocaApp.ui.widgets import RoundedButton as Button
from kivy.clock import Clock
import random
import datetime as _dt

class ReviewScreen:
    def open_review_popup(self, *_):
        review_pool = []
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        filter_row = BoxLayout(size_hint=(1, 0.12), spacing=8, height=20)
        lbl_from = Label(text="From:", font_size=18, size_hint=(None, 1), width=60, color=(0.9,0.95,1,1))
        date_from_inp = TextInput(hint_text="DD/MM or YYYY-MM-DD", multiline=False, font_size=25, height=20)
        lbl_to = Label(text="To:", font_size=18, size_hint=(None, 1), width=60, color=(0.9,0.95,1,1))
        date_to_inp = TextInput(hint_text="DD/MM or YYYY-MM-DD", multiline=False, font_size=25, height=20)
        tt_filter_btn = ToggleButton(text="Tongue‑twister", size_hint=(None, 1), width=220)
        filter_row.add_widget(lbl_from); filter_row.add_widget(date_from_inp)
        filter_row.add_widget(lbl_to);   filter_row.add_widget(date_to_inp)
        filter_row.add_widget(tt_filter_btn)
        root.add_widget(filter_row)

        word_btn = Button(
            text="", font_size=64, size_hint=(1, 0.28),
            background_normal='', background_color=(0, 0, 0, 0),
            color=(0.95, 0.98, 1, 1)
        )
        word_btn.bind(on_release=lambda *_: self._open_word_meanings_editor(getattr(self, "_review_current_word", None)))
        root.add_widget(word_btn)

        controls = AnchorLayout(size_hint=(1, 0.12), anchor_x='center', anchor_y='center')
        controls_row = BoxLayout(orientation='horizontal', spacing=12, size_hint=(None, 1))
        play_btn = Button(text='Listen', size_hint=(None, 1), width=120, font_size=22,
                          background_normal='', background_color=(0.25,0.55,0.9,1))
        rec_btn = Button(text='Speak', size_hint=(None, 1), width=120, font_size=22,
                         background_normal='', background_color=(0.9,0.4,0.3,1))
        controls_row.add_widget(play_btn)
        controls_row.add_widget(rec_btn)
        controls_row.width = sum(w.width for w in controls_row.children) + (len(controls_row.children)-1)*controls_row.spacing
        controls.add_widget(controls_row)
        root.add_widget(controls)

        stt_label = Label(text="", font_size=18, size_hint=(1, 0.06), color=(0.8,0.9,1,1))
        root.add_widget(stt_label)

        sv = ScrollView(size_hint=(1, 0.48))
        grid = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=(0, 6))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)

        bar = BoxLayout(size_hint=(1, 0.10), spacing=8)
        close_btn = Button(text="Close", font_size=24, background_color=self.theme["closeButton"])
        reveal_btn = Button(text="Show", font_size=24, background_color=(0.25,0.55,0.9,1))
        next_btn = Button(text="Next", font_size=24, background_color=(0.4,0.8,0.4,1))
        bar.add_widget(close_btn); bar.add_widget(reveal_btn); bar.add_widget(next_btn)
        root.add_widget(bar)
        self.review_popup = Popup(title="Review", content=root, size_hint=(0.95, 0.9), auto_dismiss=True)

        # Fix: Toggle für „Anzeigen“ steuern
        reveal_btn.bind(on_release=lambda *_: setattr(reveal_btn, "disabled", True))
        next_btn.bind(on_release=lambda *_: setattr(reveal_btn, "disabled", False))

        # Persist review order
        modes = ("Random", "Newest", "Oldest")
        prefs = self._get_prefs()
        saved_mode = "Random"
        try:
            if prefs.exists("review"): saved_mode = prefs.get("review").get("order_mode") or "Random"
        except Exception: pass
        self.review_order_mode = saved_mode if saved_mode in modes else "Random"

        # If you already have a Spinner for order, set it to saved mode and save on change:
        # order_spin = Spinner(text=self.review_order_mode, values=modes, size_hint=(None, 1), width=180)
        # def _on_order_change(inst, val):
        #     self.review_order_mode = val
        #     try: prefs.put("review", order_mode=val)
        #     except Exception: pass
        # order_spin.bind(text=_on_order_change)

        def _parse_date(s: str):
            s = (s or "").strip()
            if not s: return None
            today_year = _dt.date.today().year
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d/%m", "%d.%m"):
                try:
                    d = _dt.datetime.strptime(s, fmt)
                    if fmt in ("%d/%m", "%d.%m"):
                        return _dt.date(year=today_year, month=d.month, day=d.day)
                    return _dt.date(year=d.year, month=d.month, day=d.day)
                except Exception:
                    continue
            return None

        def _show_random_word(*_):
            if not review_pool:
                self._review_current_word = None
                word_btn.text = ""
                return
            w = random.choice(review_pool)
            self._review_current_word = w
            word_btn.text = w
            grid.clear_widgets()

        def _compute_pool():
            nonlocal review_pool
            f = _parse_date(date_from_inp.text)
            t = _parse_date(date_to_inp.text)
            words = list(self.learned_session) + list(self.expressions)
            if f or t:
                filtered_words = []
                for w in words:
                    lw = (w or "").lower()
                    ds = (self.learned_log.get(lw, "") or "").strip()
                    try:
                        d = _dt.date.fromisoformat(ds) if ds else None
                    except Exception:
                        d = None
                    if f and (not d or d < f): 
                        continue
                    if t and (not d or d > t):
                        continue
                    filtered_words.append(w)
                review_pool = filtered_words
            else:
                review_pool = words

            if tt_filter_btn.state == 'down':
                review_pool = [w for w in review_pool if (w or "").lower() in self.tongue_twisters]

            next_btn.disabled = (len(review_pool) == 0)
            play_btn.disabled = (len(review_pool) == 0)
            reveal_btn.disabled = (len(review_pool) == 0)
            stt_label.text = ""
            grid.clear_widgets()
            Clock.schedule_once(_show_random_word, 0)

        def render_details(*_):
            w = getattr(self, "_review_current_word", None)
            if not w:
                return
            self._show_word_details_in_grid(w, word_btn, grid)
            reveal_btn.disabled = True

        next_btn.bind(on_release=_show_random_word)
        reveal_btn.bind(on_release=render_details)
        close_btn.bind(on_release=(lambda *_: self.review_popup.dismiss()))
        tt_filter_btn.bind(state=lambda *_: _compute_pool())
        date_from_inp.bind(text=lambda *_: _compute_pool())
        date_to_inp.bind(text=lambda *_: _compute_pool())
        self.review_popup.open()
        Clock.schedule_once(lambda dt: _compute_pool(), 0)

        play_btn.bind(on_release=lambda *_: self._speak(getattr(self, "_review_current_word", "")))

        def _on_rec(*_):
            rec_btn.disabled = True

            def _start_recording():
                stt_label.text = "Speak …"
                self.stt.record_and_transcribe(3.0, lambda text, err: (
                    setattr(stt_label, "text", err or (text or "")),
                    setattr(rec_btn, "disabled", False)
                ))

            if getattr(self, "stt", None):
                _start_recording()
            else:
                stt_label.text = "Loading STT …"
                # Autostart vormerken – wird von _init_stt_async ausgelöst
                self._stt_on_ready = lambda: Clock.schedule_once(lambda dt: _start_recording(), 0)
                try:
                    self._init_stt_async()
                except Exception:
                    pass

        rec_btn.bind(on_release=_on_rec)

    def _notify_stt_ready(self):
        cb = getattr(self, "_stt_on_ready", None)
        if cb:
            try:
                cb()
            finally:
                self._stt_on_ready = None