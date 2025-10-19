from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from ui.widgets import RoundedButton as Button
import random
import datetime as _dt

class LearnScreen:
    def open_learn_mode(self, *_):
        # Kandidaten prüfen
        if not any(w for w in self.new_words if w.lower() not in self.removed_words):
            self.show_error_popup("No new words available.")
            return

        root = BoxLayout(orientation='vertical', spacing=10, padding=12)

        # Modus: Reihenfolge
        modes = ("Random", "Newest", "Oldest")
        prefs = self._get_prefs()
        saved_mode = "Random"
        try:
            if prefs.exists("learn"): saved_mode = prefs.get("learn").get("order_mode") or "Random"
        except Exception: pass
        self.learn_order_mode = saved_mode if saved_mode in modes else "Random"
        order_bar = BoxLayout(size_hint=(1, 0.10))
        order_lbl = Label(text="Order:", font_size=24, size_hint=(None, 1), width=170, color=(0.9,0.95,1,1))
        order_spin = Spinner(text=self.learn_order_mode, values=modes, size_hint=(None, 1), width=180)
        def _on_order(inst, val):
            try: prefs.put("learn", order_mode=val)
            except Exception: pass
            if hasattr(self, "_on_learn_order_changed"):
                self._on_learn_order_changed(inst, val)
            else:
                self.learn_order_mode = val
        order_spin.bind(text=_on_order)
        order_bar.add_widget(order_lbl)
        order_bar.add_widget(order_spin)
        root.add_widget(order_bar)

        # Klickbares Wort (öffnet den Bedeutungs-/Beispiele-Editor)
        self.learn_word_label = Button(
            text="",
            font_size=64,
            size_hint=(1, 0.34),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0.9, 0.95, 1, 1)
        )
        self.learn_word_label.bind(on_press=lambda *_: self._open_word_meanings_editor(getattr(self, "learn_current_word", None)))
        root.add_widget(self.learn_word_label)

        # Hinweis direkt unter dem Wort
        hint = Label(
            text="[i]Tap the word to add meanings and examples.[/i]",
            markup=True,
            size_hint=(1, 0.08),
            font_size=24,
            color=(0.8, 0.85, 0.9, 1),
            halign='center',
            valign='middle'
        )
        def _sync(*_):
            try:
                hint.text_size = (hint.width - 12, None)
            except Exception:
                pass
        hint.bind(size=lambda *_: _sync())
        _sync()

        root.add_widget(hint)

        # Aktionen: Gelernt / Nächste / Entfernen
        act_bar = BoxLayout(size_hint=(1, 0.14), spacing=8)
        btn_learned = Button(text="Learned", font_size=24, background_color=(0.25,0.6,0.25,1))
        btn_next = Button(text="Next", font_size=24, background_color=(0.4,0.8,0.4,1))
        self.learn_next_btn = btn_next
        self._learn_idx = 0
        self._learn_history = []
        btn_remove = Button(text="Remove", font_size=24, background_color=(0.6,0.2,0.2,1))
        btn_learned.bind(on_release=self._learn_mark_known)
        btn_next.bind(on_release=self._learn_next_word)
        btn_remove.bind(on_release=self._learn_remove_current)
        act_bar.add_widget(btn_learned)
        act_bar.add_widget(btn_next)
        act_bar.add_widget(btn_remove)
        root.add_widget(act_bar)

        # Breite Buttons: Wiederholen / Gelernte Wörter
        actions = BoxLayout(orientation='vertical', size_hint=(1, 0.18), spacing=8)
        btn_review = Button(text="Review", font_size=24, size_hint=(1, 0.5), background_color=(0.55,0.55,0.9,1))
        btn_all = Button(text="Learned words", font_size=24, size_hint=(1, 0.5), background_color=(0.25,0.55,0.7,1))
        btn_review.bind(on_release=self.open_review_popup)
        btn_all.bind(on_release=(self.open_all_learned_popup))
        actions.add_widget(btn_review)
        actions.add_widget(btn_all)
        root.add_widget(actions)

        # Unten: nur „Schließen“
        bottom = BoxLayout(size_hint=(1, 0.14), spacing=8)
        close_btn = Button(text="Close", font_size=24, size_hint=(1, 1), background_color=self.theme["closeButton"])
        close_btn.bind(on_release=lambda *_: self.learn_popup.dismiss())
        bottom.add_widget(close_btn)
        root.add_widget(bottom)

        self.learn_popup = Popup(title="Learn (New words)", content=root, size_hint=(0.95, 0.92), auto_dismiss=True)
        self.learn_popup.bind(on_dismiss=(lambda *_: self.schedule_update_lists() if hasattr(self, "schedule_update_lists") else self.update_lists()))
        self.learn_popup.open()

        # Startwort anzeigen
        self._learn_next_word(None)

    def _on_learn_order_changed(self, spinner, value):
        self.learn_order_mode = value
        self._learn_idx = 0
        self._learn_next_word(None)
        try:
            self._store.save_async()
        except Exception:
            pass

    def _learn_candidates(self) -> list[str]:
        removed_lower = set(self.removed_words)
        base = [w for w in self.new_sequence if (w in self.new_words and w.lower() not in removed_lower)]
        rest = [w for w in self.new_words if (w not in base and w.lower() not in removed_lower)]
        seq = base + rest
        if self.learn_order_mode == "Oldest":
            return seq
        if self.learn_order_mode == "Newest":
            return list(reversed(seq))
        return seq  # Zufällig: Reihenfolge egal, Auswahl erfolgt zufällig

    def _learn_next_word(self, *_):
        prev = getattr(self, "learn_current_word", None)
        if prev:
            if not hasattr(self, "_learn_history"):
                self._learn_history = []
            if not self._learn_history or self._learn_history[-1] != prev:
                self._learn_history.append(prev)

        candidates = self._learn_candidates()
        if not candidates:
            self.learn_current_word = None
            if hasattr(self, "learn_word_label"):
                self.learn_word_label.text = "No new words."
            if hasattr(self, "learn_next_btn"):
                self.learn_next_btn.disabled = True
            return

        mode = getattr(self, "learn_order_mode", "Random")
        if mode == "Zufällig":
            if len(candidates) > 1 and prev in candidates:
                pool = [w for w in candidates if w != prev]
                w = random.choice(pool)
            else:
                w = random.choice(candidates)
        else:
            idx = getattr(self, "_learn_idx", 0)
            w = candidates[idx % len(candidates)]
            self._learn_idx = (idx + 1) % max(1, len(candidates))

        self.learn_current_word = w
        if hasattr(self, "learn_word_label"):
            self.learn_word_label.text = w
        if hasattr(self, "learn_next_btn"):
            self.learn_next_btn.disabled = False

    def _learn_prev_word(self, *_):
        if not hasattr(self, "_learn_history") or not self._learn_history:
            return
        w = self._learn_history.pop()
        self.learn_current_word = w
        if hasattr(self, "learn_word_label"):
            self.learn_word_label.text = w
        if hasattr(self, "learn_next_btn"):
            self.learn_next_btn.disabled = False

    def _mark_known_no_advance(self, w: str):
        if not w:
            return
        self.new_words.discard(w)
        try:
            self.new_sequence.remove(w)
        except ValueError:
            pass
        if w not in self.known_words:
            self.known_words.add(w)
        if w not in self.known_sequence:
            self.known_sequence.append(w)
        lw = w.lower()
        if all(x.lower() != lw for x in self.learned_session):
            self.learned_session.append(w)
        try:
            self.learned_log[lw] = _dt.date.today().isoformat()
        except Exception:
            pass
        (self.schedule_update_lists() if hasattr(self, "schedule_update_lists") else self.update_lists())
        try:
            self._store.save_async()
        except Exception:
            pass

    def _learn_mark_known(self, *_):
        w = getattr(self, "learn_current_word", None)
        if not w:
            return
        self._mark_known_no_advance(w)
        self._learn_next_word(None)

    def _learn_mark_new(self, *_):
        w = getattr(self, "learn_current_word", None)
        if not w:
            return
        if w in self.known_words:
            self.known_words.discard(w)
            try:
                self.known_sequence.remove(w)
            except ValueError:
                pass
        if w not in self.new_words:
            self.new_words.add(w)
        if w not in self.new_sequence:
            self.new_sequence.append(w)
        (self.schedule_update_lists() if hasattr(self, "schedule_update_lists") else self.update_lists())
        try:
            self._store.save_async()
        except Exception:
            pass
        self._learn_next_word(None)

    def _learn_remove_current(self, *_):
        w = getattr(self, "learn_current_word", None)
        if not w:
            return
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
        (self.schedule_update_lists() if hasattr(self, "schedule_update_lists") else self.update_lists())
        self.update_display()
        try:
            self._store.save_async()
        except Exception:
            pass
        self._learn_next_word(None)