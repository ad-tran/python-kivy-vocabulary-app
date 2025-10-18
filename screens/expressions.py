from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from VocaApp.ui.widgets import RoundedButton as Button
from kivy.uix.widget import Widget

class ExpressionsScreen:
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

    def open_expressions_popup(self, *_):
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        search_row = BoxLayout(size_hint=(1, 0.10), spacing=8)
        search_input = TextInput(hint_text="Search...", multiline=False, font_size=30, size_hint=(1, 1))
        search_row.add_widget(search_input)
        root.add_widget(search_row)
        sv = ScrollView(size_hint=(1, 0.74))
        grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(0, 6))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)
        bar = BoxLayout(size_hint=(1, 0.16), spacing=8)
        add_btn = Button(text="Add", font_size=30, background_color=(0.25, 0.55, 0.9, 1))
        close_btn = Button(text="Close", font_size=30, background_color=self.theme["closeButton"])
        bar.add_widget(add_btn)
        bar.add_widget(close_btn)
        root.add_widget(bar)
        self.expressions_popup = Popup(
            title="Expressions & Phrases", content=root, size_hint=(0.95, 0.92), auto_dismiss=True
        )
        def rebuild_list(query: str):
            grid.clear_widgets()
            q = (query or "").strip().lower()
            filtered = [t for t in self.expressions if (not q or q in t.lower())]
            max_items = 400
            show = filtered[:max_items]
            if not show:
                grid.add_widget(Label(text="No entries.", size_hint_y=None, height=40, font_size=20, color=(0.8,0.8,0.8,1)))
                return
            for phrase in show:
                btn = Button(
                    text=phrase,
                    size_hint_y=None,
                    height=56,
                    font_size=32,
                    background_normal='',
                    background_color=(0, 0, 0, 0),
                    color=(0.95,0.98,1,1),
                    halign='left',
                    valign='middle'
                )
                btn.text_size = (grid.width, None)
                grid.bind(width=lambda inst, val, b=btn: setattr(b, 'text_size', (val, None)))
                btn.bind(on_release=lambda *_x, p=phrase: self._open_word_meanings_editor(p))
                grid.add_widget(btn)
                key = (phrase or "").lower()
                _ipa = (self.word_ipa.get(key, "") or "").strip()
                if _ipa:
                    self._add_wrapped_label(grid, f"[IPA] {_ipa}", 24, color=(0.8, 0.95, 0.9, 1), indent_left=12, font_name=self.font_ipa_name or None)
                entries = self.word_details.get(key, [])
                if not entries:
                    self._add_wrapped_label(grid, "– No meanings available –", 20, color=(0.8, 0.8, 0.8, 1), indent_left=12)
                else:
                    for idx, item in enumerate(entries, start=1):
                        meaning = (item.get("meaning", "") or "").strip()
                        examples = item.get("examples")
                        if not isinstance(examples, list):
                            ex = (item.get("example", "") or "").strip()
                            examples = [ex] if ex else []
                        pos = [p for p in (item.get("pos") or []) if isinstance(p, str)]
                        pos_str = f"({', '.join(pos)}) " if pos else ""
                        if meaning:
                            self._add_wrapped_label(grid, f"{idx}. {pos_str}{meaning}", 35, color=(0.9, 0.95, 1, 1), indent_left=12)
                        for ex in examples:
                            self._add_wrapped_label(grid, f"- {ex}", 30, color=(0.8, 0.9, 1, 1), indent_left=36)
            if len(filtered) > max_items:
                grid.add_widget(Label(text=f"… {len(filtered)-max_items} weitere …", size_hint_y=None, height=32, font_size=18, color=(0.8,0.8,0.8,1)))
        self._expr_rebuild = rebuild_list
        self._expr_search_widget = search_input
        _pending_expr = {"ev": None}
        def _debounced_expr(*_):
            if _pending_expr["ev"]:
                try: _pending_expr["ev"].cancel()
                except Exception: pass
            _pending_expr["ev"] = Clock.schedule_once(lambda dt: rebuild_list(search_input.text), 0.12)
        search_input.bind(text=lambda inst, val: _debounced_expr())
        add_btn.bind(on_release=(lambda *_: self._add_expression_dialog()))
        close_btn.bind(on_release=(lambda *_: self.expressions_popup.dismiss()))
        def _cleanup_expr_refs(*_):
            try:
                if _pending_expr["ev"]: _pending_expr["ev"].cancel()
            except Exception:
                pass
            self._expr_rebuild = None
            self._expr_search_widget = None
        self.expressions_popup.bind(on_open=(lambda *_: rebuild_list(search_input.text)))
        self.expressions_popup.bind(on_dismiss=(_cleanup_expr_refs))
        self.expressions_popup.open()

    def _add_expression_dialog(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=12)

        # Eingabe: Redewendung / Ausdruck (Text)
        title_lbl = Label(text="New expression / phrase", font_size=26, size_hint=(1, None), height=34, color=(0.9,0.95,1,1))
        content.add_widget(title_lbl)
        phrase_row = BoxLayout(size_hint=(1, None), height=64, spacing=10)
        # phrase_lbl = Label(text="Text:", size_hint=(None, 1), width=90, font_size=22, color=(0.9,0.95,1,1))
        phrase_inp = TextInput(text="", multiline=False, font_size=30)
        # phrase_row.add_widget(phrase_lbl)
        phrase_row.add_widget(phrase_inp)
        content.add_widget(phrase_row)

        # Eingabe: Bedeutung
        meaning_lbl = Label(text="Meaning:", font_size=22, size_hint=(1, None), height=30, color=(0.9,0.95,1,1))
        content.add_widget(meaning_lbl)
        meaning_inp = TextInput(text="", multiline=True, font_size=28, size_hint=(1, None), height=140)
        content.add_widget(meaning_inp)

        # Eingabe: Beispiele (mehrere, eingerückt)
        examples_lbl = Label(text="Examples:", font_size=22, size_hint=(1, None), height=30, color=(0.9,0.95,1,1))
        content.add_widget(examples_lbl)

        # Beispiel-Box
        ex_box = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(24, 0, 0, 0))
        ex_box.bind(minimum_height=ex_box.setter('height'))
        content.add_widget(ex_box)

        example_inputs = []

        def add_example(text: str = ""):
            row = BoxLayout(size_hint_y=None, height=64, spacing=6)
            ex_inp = TextInput(text=text, hint_text="Examples", multiline=True, font_size=28)
            rm_btn = Button(text="x", size_hint=(None, 1), width=56, font_size=20, background_color=(0.5,0.2,0.2,1))
            def do_rm(*_):
                if row.parent:
                    ex_box.remove_widget(row)
                try:
                    example_inputs.remove(ex_inp)
                except ValueError:
                    pass
            rm_btn.bind(on_release=do_rm)
            row.add_widget(ex_inp)
            row.add_widget(rm_btn)
            ex_box.add_widget(row)
            example_inputs.append(ex_inp)

        # mindestens ein Beispiel-Feld anbieten
        add_example()

        # "+ Beispiel" Button UNTER den Beispiel-Feldern
        ex_ctrl = BoxLayout(size_hint=(1, None), height=52, spacing=6, padding=(24, 0, 0, 0))
        add_ex_btn = Button(text="+ Examples", size_hint=(None, 1), width=240, font_size=20, background_color=(0.25,0.55,0.9,1))
        ex_ctrl.add_widget(add_ex_btn)
        content.add_widget(ex_ctrl)
        add_ex_btn.bind(on_release=(lambda *_: add_example("")))

        # Spacer, damit Felder ganz oben bleiben
        content.add_widget(Widget(size_hint_y=1))

        # Footer
        bar = BoxLayout(size_hint=(1, None), height=64, spacing=8)
        cancel = Button(text="Cancel", font_size=22, background_color=self.theme["closeButton"])
        save = Button(text="Add", font_size=22, background_color=(0.25,0.6,0.25,1))
        bar.add_widget(cancel)
        bar.add_widget(save)
        content.add_widget(bar)

        self.expr_add_popup = Popup(title="Add", content=content, size_hint=(0.9, 0.75), auto_dismiss=True)

        def commit(*_):
            phrase = (phrase_inp.text or "").strip()
            meaning = (meaning_inp.text or "").strip()
            examples = []
            for inp in list(example_inputs):
                t = (inp.text or "").strip()
                if t:
                    examples.append(t)

            if not phrase:
                self.show_error_popup("Please enter the expression text.")
            elif not meaning and not examples:
                self.show_error_popup("Please enter a meaning or example(s).")
            else:
                # In Liste der Redewendungen aufnehmen (unique, Reihenfolge)
                if phrase not in self.expressions:
                    self.expressions.append(phrase)

                # Bedeutung/Beispiele als Eintrag mergen
                key = phrase.lower()
                entry = {"meaning": meaning, "examples": examples, "pos": []}
                items = list(self.word_details.get(key, []))
                items.append(entry)
                self.word_details[key] = items

                # speichern
                if hasattr(self, "_store"):
                    self._store.save_async()
                else:
                    try:
                        self.save_progress()
                    except Exception:
                        pass

                # Liste im Popup auffrischen (sofern geöffnet)
                try:
                    if getattr(self, "expressions_popup", None) and self.expressions_popup.parent:
                        q = ""
                        si = getattr(self, "_expr_search_widget", None)
                        if si:
                            q = si.text or ""
                        reb = getattr(self, "_expr_rebuild", None)
                        if callable(reb):
                            reb(q)
                except Exception:
                    pass

                try:
                    self.expr_add_popup.dismiss()
                except Exception:
                    pass
                self.show_error_popup("Saved.", duration=2)

        cancel.bind(on_release=(lambda *_: self.expr_add_popup.dismiss()))
        save.bind(on_release=(commit))
        self.expr_add_popup.open()