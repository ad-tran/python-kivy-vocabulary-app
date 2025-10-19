from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.uix.togglebutton import ToggleButton
from ui.widgets import RoundedButton as Button
import re

class DictionaryScreen:
    # Normalize a single word input (used when renaming/adding)
    def _sanitize_single_word(self, text: str) -> str:
        s = (text or "").strip()
        if s.startswith("- "):
            s = s[2:]
        s = s.replace("’", "'").replace("–", "-").replace("—", "-")
        s = re.sub(r"\s+", " ", s)
        # take the first token before space/comma/slash
        s = re.split(r"[,\s/]+", s)[0]
        # strip surrounding punctuation
        s = s.strip(" .,:;!?\"'()[]{}")
        return s

    def _adjust_label_height(self, label):
        label.text_size = (label.width, None)
        label.height = label.texture_size[1]
        if not hasattr(label, "_auto_height_bound"):
            label.bind(width=lambda inst, val: self._adjust_label_height(inst))
            label._auto_height_bound = True

    def _add_wrapped_label(self, parent_grid: GridLayout, text: str, font_size: int,
                           color=(0.95, 0.98, 1, 1), extra_pad: int = 6, indent_left: int = 0, font_name: str | None = None):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=0, spacing=0, padding=(0, 0))
        if (indent_left > 0):
            from kivy.uix.widget import Widget
            row.add_widget(Widget(size_hint=(None, None), width=indent_left, height=1))
        lbl = Label(text=text, font_size=font_size, size_hint_y=None, color=color, halign='left', valign='top')
        if font_name:
            lbl.font_name = font_name
        def _recalc(*_):
            try:
                lbl.text_size = (max(0, parent_grid.width - indent_left), None)
                lbl.texture_update()
                lbl.height = lbl.texture_size[1] + extra_pad
                row.height = lbl.height
            except Exception:
                pass
        parent_grid.bind(width=lambda inst, val: Clock.schedule_once(lambda dt: _recalc(), 0))
        lbl.bind(texture_size=lambda inst, val: setattr(lbl, 'height', val[1] + extra_pad))
        lbl.bind(height=lambda inst, val: setattr(row, 'height', val))
        row.add_widget(lbl)
        parent_grid.add_widget(row)
        Clock.schedule_once(lambda dt: _recalc(), 0)
        return lbl

    def _show_word_details_in_grid(self, word: str, word_label: Label, grid: GridLayout):
        word_label.text = word
        grid.clear_widgets()
        ipa = self.word_ipa.get((word or "").lower(), "").strip()
        if ipa:
            self._add_wrapped_label(
                grid, f"[IPA] {ipa}", 28, color=(0.8, 0.95, 0.9, 1), indent_left=12, font_name=self.font_ipa_name or None
            )
        entries = self.word_details.get((word or "").lower(), [])
        if not entries:
            if not ipa:
                self._add_wrapped_label(grid, "No meanings available.", 20, color=(0.8, 0.8, 0.8, 1), indent_left=12)
            return
        for idx, item in enumerate(entries, start=1):
            meaning = (item.get("meaning", "") or "").strip()
            examples = item.get("examples")
            if not isinstance(examples, list):
                ex = (item.get("example", "") or "").strip()
                examples = [ex] if ex else []
            pos = [p for p in (item.get("pos") or []) if isinstance(p, str)]
            pos_str = f"({', '.join(pos)}) " if pos else ""
            if meaning:
                self._add_wrapped_label(grid, f"{idx}. {pos_str}{meaning}", 40, color=(0.95, 0.98, 1, 1), indent_left=12)
            for ex in examples:
                self._add_wrapped_label(grid, f"- {ex}", 30, color=(0.8, 0.9, 1, 1), indent_left=36)

    def open_dictionary_popup(self, word: str | None, *_):
        if not word:
            self.show_error_popup("No word selected.")
            return
        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        word_btn = Button(
            text="",
            font_size=64,
            size_hint=(1, 0.22),
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0.95, 0.98, 1, 1)
        )
        root.add_widget(word_btn)
        play_row = BoxLayout(size_hint=(1, 0.08), spacing=8)
        play_btn = Button(
            text="Listen",
            size_hint=(None, 1),
            width=96,
            font_size=28,
            background_normal='',
            background_color=(0.25, 0.55, 0.9, 1)
        )
        play_btn.bind(on_release=lambda *_: self._speak(word))
        play_row.add_widget(play_btn)
        from kivy.uix.widget import Widget
        play_row.add_widget(Widget())
        root.add_widget(play_row)
        sv = ScrollView(size_hint=(1, 0.56))
        grid = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=(0, 6))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)
        bar = BoxLayout(size_hint=(1, 0.14), spacing=8)
        edit_btn = Button(text="Edit", font_size=24, size_hint=(1, 1), background_color=(0.25,0.55,0.9,1))
        close_btn = Button(text="Close", font_size=24, size_hint=(1, 1), background_color=self.theme["closeButton"])
        bar.add_widget(edit_btn)
        bar.add_widget(close_btn)
        root.add_widget(bar)
        self.dictionary_popup = Popup(
            title=f"Dictionary – {word}", content=root, size_hint=(0.95, 0.9), auto_dismiss=True
        )
        def refresh_view():
            self._show_word_details_in_grid(word, word_btn, grid)
        word_btn.bind(on_release=lambda *_: self._open_word_meanings_editor(word))
        edit_btn.bind(on_release=lambda *_: self._open_word_meanings_editor(word))
        close_btn.bind(on_release=lambda *_: self.dictionary_popup.dismiss())
        self.dictionary_popup.bind(on_open=(lambda *_: refresh_view()))
        self.dictionary_popup.open()

    # Editor (Bedeutungen/Beispiele) – aus deinem Code übernommen
    def _open_word_meanings_editor(self, word: str | None):
        if not word:
            self.show_error_popup("No word.")
            return
        key = word.lower()

        existing_raw = list(self.word_details.get(key, []))
        existing = []
        for it in existing_raw:
            if not isinstance(it, dict):
                continue
            m = (it.get("meaning") or "").strip()
            if isinstance(it.get("examples"), list):
                exs = [str(e).strip() for e in it["examples"] if str(e).strip()]
            else:
                ex = (it.get("example") or "").strip()
                exs = [ex] if ex else []
            existing.append({"meaning": m, "examples": exs, "pos": list(it.get("pos") or [])})

        root = BoxLayout(orientation='vertical', spacing=10, padding=12)
        header = Label(text=f"{word} – Meanings & Examples", font_size=self.font_meanings_header, size_hint=(1, 0.1), color=(0.95,0.98,1,1))
        root.add_widget(header)

        rename_row = BoxLayout(size_hint=(1, None), height=56, spacing=8)
        rename_lbl = Label(text="Word:", font_size=self.font_meanings_buttons, size_hint=(None, 1), width=70, color=(0.9,0.95,1,1))
        rename_inp = TextInput(text=word, multiline=False, font_size=self.font_meaning_input)
        rename_btn = Button(text="Rename word", size_hint=(None, 1), width=220, font_size=self.font_meanings_buttons, background_color=(0.25,0.55,0.9,1))
        rename_row.add_widget(rename_lbl)
        rename_row.add_widget(rename_inp)
        rename_row.add_widget(rename_btn)
        root.add_widget(rename_row)

        def _do_rename(*_):
            nonlocal word, key
            old = word
            new_raw = (rename_inp.text or "")
            new = self._sanitize_single_word(new_raw)
            if not new:
                self.show_error_popup("Invalid word.")
                return
            old_l, new_l = old.lower(), new.lower()
            if new_l in self.removed_words:
                self.show_error_popup("This word is marked as removed.")
                return
            existing_lower_map = {}
            for w0 in self.vocabulary:
                wl = w0.lower()
                if wl not in existing_lower_map:
                    existing_lower_map[wl] = w0

            if new_l == old_l:
                self._replace_word_everywhere(old, new)
                target = new
            elif new_l in existing_lower_map:
                canonical = existing_lower_map[new_l]
                self._merge_word_into_canonical(old, canonical)
                target = canonical
            else:
                self._replace_word_everywhere(old, new)
                target = new

            word = target
            key = target.lower()
            header.text = f"{word} – Meanings & Examples"
            try:
                self.meanings_popup.title = f"{word} – Notes"
            except Exception:
                pass
            rename_inp.text = target

            ipa_val = (self.word_ipa.get(key, "") or "").strip()
            ipa_inp.text = ipa_val
            try:
                tt_toggle.state = 'down' if key in self.tongue_twisters else 'normal'
            except Exception:
                pass
            if getattr(self, "learn_current_word", None) == old:
                self.learn_current_word = word
                if hasattr(self, "learn_word_label"):
                    self.learn_word_label.text = word

            (self.schedule_update_lists() if hasattr(self, "schedule_update_lists") else self.update_lists())
            self.update_display()
            self._store.save_async() if hasattr(self, "_store") else self.save_progress()
            self.show_error_popup(f"Renamed to: {word}")

        rename_btn.bind(on_release=_do_rename)
        rename_inp.bind(on_text_validate=_do_rename)

        ipa_row = BoxLayout(size_hint=(1, None), height=56, spacing=8)
        ipa_lbl = Label(text="IPA:", font_size=self.font_meanings_buttons, size_hint=(None, 1), width=70, color=(0.9,0.95,1,1))
        ipa_inp = TextInput(
            text=self.word_ipa.get(key, ""),
            hint_text="",
            multiline=False,
            font_size=self.font_meaning_input,
        )
        if self.font_ipa_name:
            ipa_inp.font_name = self.font_ipa_name
        ipa_row.add_widget(ipa_lbl)
        ipa_row.add_widget(ipa_inp)
        # Hören-Button direkt hinter dem IPA-Feld
        play_ipa_btn = Button(
            text="Listen", size_hint=(None, 1), width=100,
            font_size=self.font_meanings_buttons, background_normal='',
            background_color=(0.25,0.55,0.9,1)
        )
        def _on_play_ipa(*_):
            try:
                self._init_tts_async()
            except Exception:
                pass
            self._speak(word)
        play_ipa_btn.bind(on_release=_on_play_ipa)
        ipa_row.add_widget(play_ipa_btn)
        root.add_widget(ipa_row)

        flags_row = BoxLayout(size_hint=(1, None), height=50, spacing=8)
        tt_toggle = ToggleButton(
            text="Tongue‑twister",
            size_hint=(None, 1),
            width=220,
            state='down' if key in self.tongue_twisters else 'normal'
        )
        flags_row.add_widget(tt_toggle)
        root.add_widget(flags_row)

        sv = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=1, spacing=8, size_hint_y=None, padding=(0, 4))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)

        self._meaning_rows_data = []

        def update_row_height(row_dict, *_):
            try:
                total = (
                    row_dict["pos_row"].height +
                    row_dict["inp_mean"].height +
                    row_dict["ex_box"].height +
                    row_dict["bar"].height +
                    12
                )
                row_dict["row"].height = total
            except Exception:
                pass

        def add_example(row_dict, text: str = ""):
            ex_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=56, spacing=6)
            ex_inp = TextInput(text=text, hint_text="Example", multiline=True, size_hint=(1, 1), font_size=self.font_example_input)
            rm = Button(text="x", size_hint=(None, 1), width=42, font_size=16, background_color=(0.5,0.2,0.2,1))
            def do_rm(*_):
                if ex_row.parent:
                    row_dict["ex_box"].remove_widget(ex_row)
                try:
                    row_dict["ex_inputs"].remove(ex_inp)
                except ValueError:
                    pass
                update_row_height(row_dict)
            rm.bind(on_release=do_rm)
            ex_row.add_widget(ex_inp)
            ex_row.add_widget(rm)
            row_dict["ex_box"].add_widget(ex_row)
            row_dict["ex_inputs"].append(ex_inp)
            update_row_height(row_dict)

        def add_row(meaning: str = "", examples: list[str] | None = None, pos: list[str] | None = None):
            row = BoxLayout(orientation='vertical', size_hint_y=None, height=150, spacing=6, padding=(12, 0, 0, 0))
            pos_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=6)
            pos_lbl = Label(text="POS:", size_hint=(None, 1), width=50, font_size=self.font_meanings_buttons, color=(0.9,0.95,1,1))
            pos_row.add_widget(pos_lbl)
            selected = set((pos or []))
            pos_buttons = []
            for tag in self.pos_tags:
                tb = ToggleButton(
                    text=tag,
                    size_hint=(None, 1),
                    width=70,
                    font_size=self.font_meanings_buttons,
                    background_normal='',
                    background_color=(0.25,0.25,0.25,1),
                    state='down' if tag in selected else 'normal'
                )
                pos_row.add_widget(tb)
                pos_buttons.append(tb)
            row.add_widget(pos_row)

            mean_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=6)
            inp_mean = TextInput(text=meaning, hint_text="Meaning", multiline=True, size_hint=(1, 1), font_size=self.font_meaning_input)
            rm_mean_btn = Button(text="x", size_hint=(None, 1), width=42, font_size=16, background_color=(0.5,0.2,0.2,1))
            mean_row.add_widget(inp_mean)
            mean_row.add_widget(rm_mean_btn)
            row.add_widget(mean_row)

            ex_box = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=(24, 0, 0, 0))
            ex_box.bind(minimum_height=ex_box.setter('height'))

            bar = BoxLayout(size_hint_y=None, height=36, spacing=6)
            add_ex_btn = Button(text="+ Example", font_size=self.font_meanings_buttons, size_hint=(None, 1), width=200, background_color=(0.25,0.55,0.9,1))
            bar.add_widget(add_ex_btn)
            bar.add_widget(BoxLayout(size_hint=(1, 1)))
            row.add_widget(ex_box)
            row.add_widget(bar)
            grid.add_widget(row)

            row_dict = {"row": row, "pos_row": pos_row, "inp_mean": inp_mean, "ex_box": ex_box, "bar": bar, "ex_inputs": [], "pos_buttons": pos_buttons}
            self._meaning_rows_data.append(row_dict)

            add_ex_btn.bind(on_release=(lambda *_: add_example(row_dict)))

            # Bedeutung entfernen: bei letzter verbleibender Zeile nur leeren
            def _remove_meaning(*_):
                try:
                    if len(self._meaning_rows_data) <= 1:
                        # letzte Zeile: Felder leeren + genau ein Beispiel-Feld behalten
                        row_dict["inp_mean"].text = ""
                        for ex_inp in list(row_dict["ex_inputs"]):
                            try:
                                ex_row = ex_inp.parent
                                if ex_row and ex_row.parent:
                                    row_dict["ex_box"].remove_widget(ex_row)
                            except Exception:
                                pass
                        row_dict["ex_inputs"].clear()
                        add_example(row_dict, "")
                        update_row_height(row_dict)
                        return
                    # sonst: Zeile komplett entfernen
                    try:
                        self._meaning_rows_data.remove(row_dict)
                    except ValueError:
                        pass
                    if row_dict["row"].parent:
                        grid.remove_widget(row_dict["row"])
                except Exception:
                    pass

            rm_mean_btn.bind(on_release=_remove_meaning)

            ex_box.bind(height=lambda inst, val: update_row_height(row_dict))
            # Direkt ein Beispiel-Feld anzeigen (falls keine Beispiele vorhanden)
            if examples and len(examples) > 0:
                for ex in examples:
                    add_example(row_dict, ex)
            else:
                add_example(row_dict, "")
            update_row_height(row_dict)

        if existing:
            for item in existing:
                add_row(item["meaning"], item["examples"], item.get("pos"))
        else:
            add_row()

        footer = BoxLayout(size_hint=(1, None), height=70, spacing=8, padding=(0, 0))
        add_meaning_btn = Button(text="+ Meaning", font_size=self.font_meanings_buttons, background_color=(0.25,0.55,0.9,1))
        save_btn = Button(text="Save", font_size=self.font_meanings_buttons, background_color=(0.2,0.6,0.2,1))
        prev_btn = Button(text="Back", font_size=self.font_meanings_buttons, background_color=(0.55,0.55,0.7,1))
        next_btn = Button(text="Next", font_size=self.font_meanings_buttons, background_color=(0.4,0.8,0.4,1))
        close_btn = Button(text="Close", font_size=self.font_meanings_buttons, background_color=self.theme["closeButton"])
        footer.add_widget(add_meaning_btn)
        footer.add_widget(save_btn)
        footer.add_widget(prev_btn)
        footer.add_widget(next_btn)
        footer.add_widget(close_btn)
        root.add_widget(footer)

        self.meanings_popup = Popup(title=f"{word} – Notizen", content=root, size_hint=(0.95, 0.92), auto_dismiss=True)
        add_meaning_btn.bind(on_release=(lambda *_: add_row()))

        is_from_learn = (getattr(self, "learn_current_word", None) == word)
        next_btn.disabled = not is_from_learn
        prev_btn.disabled = not is_from_learn
        _advanced_via_next = {"flag": False}

        def collect_and_save(silent: bool = False, only_if_filled: bool = False) -> bool:
            items = []
            for rd in list(self._meaning_rows_data):
                m = (rd["inp_mean"].text or "").strip()
                exs = []
                for ex_inp in list(rd["ex_inputs"]):
                    t = (ex_inp.text or "").strip()
                    if t:
                        exs.append(t)
                pos_sel = [btn.text for btn in rd.get("pos_buttons", []) if getattr(btn, "state", "") == "down"]
                if m or exs or pos_sel:
                    items.append({"meaning": m, "examples": exs, "pos": pos_sel})

            ipa_text = (ipa_inp.text or "").strip()
            has_content = bool(items) or bool(ipa_text) or (tt_toggle.state == 'down')

            if only_if_filled and not has_content:
                return False

            if items:
                self.word_details[key] = items
            else:
                if not only_if_filled:
                    self.word_details.pop(key, None)

            if ipa_text:
                self.word_ipa[key] = ipa_text
            else:
                if not only_if_filled:
                    self.word_ipa.pop(key, None)

            if tt_toggle.state == 'down':
                self.tongue_twisters.add(key)
            else:
                if not only_if_filled:
                    self.tongue_twisters.discard(key)

            if is_from_learn:
                self._mark_known_no_advance(word)

            if hasattr(self, "_store"):
                self._store.save_async()
            else:
                self.save_progress()
            self._refresh_learned_list_ui()
            self._refresh_expressions_list_ui()
            if not silent:
                self.show_error_popup("Gespeichert.", duration=2)
            return True

        def do_next(*_):
            if not is_from_learn:
                return
            saved = False
            try:
                saved = collect_and_save(silent=True, only_if_filled=True)
            except Exception:
                saved = False
            if saved and getattr(self, "learn_order_mode", "Random") in ("Newest", "Oldest"):
                try:
                    self._learn_idx = max(0, int(getattr(self, "_learn_idx", 0)) - 1)
                except Exception:
                    pass
            _advanced_via_next["flag"] = True
            try:
                self._learn_next_word(None)
            except Exception:
                pass
            try:
                self.meanings_popup.dismiss()
            except Exception:
                pass
            Clock.schedule_once(lambda dt: self._open_word_meanings_editor(getattr(self, "learn_current_word", None)), 0)

        def do_prev(*_):
            if not is_from_learn:
                return
            _advanced_via_next["flag"] = True
            try:
                self._learn_prev_word(None)
            except Exception:
                pass
            try:
                self.meanings_popup.dismiss()
            except Exception:
                pass
            Clock.schedule_once(lambda dt: self._open_word_meanings_editor(getattr(self, "learn_current_word", None)), 0)

        next_btn.bind(on_release=do_next)
        prev_btn.bind(on_release=do_prev)
        save_btn.bind(on_release=lambda *_: collect_and_save(silent=False, only_if_filled=False))

        def on_close(*_):
            try:
                self.meanings_popup.dismiss()
            except Exception:
                pass
            if is_from_learn and not _advanced_via_next["flag"]:
                self._learn_next_word(None)
            self._refresh_learned_list_ui()

        close_btn.bind(on_release=on_close)
        self.meanings_popup.open()