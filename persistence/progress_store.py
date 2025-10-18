from __future__ import annotations
from pathlib import Path
import json
import datetime as _dt
import shutil

class ProgressStore:
    def __init__(self, app, path: Path):
        self.app = app
        self.path = path
        self._save_scheduled = False

    # ---- Snapshot build/apply ----
    def _sorted_ci_list(self, items):
        return sorted(list(items), key=lambda s: s.lower() if isinstance(s, str) else str(s))

    def _sorted_ci_keys(self, dct):
        return sorted((dct or {}).keys(), key=lambda s: s.lower() if isinstance(s, str) else str(s))

    def build_snapshot(self) -> dict:
        a = self.app
        return {
            "displayed_words": self._sorted_ci_list(a.displayed_words),
            "word_history": list(a.word_history),
            "current_word": a.current_word,
            "known_words": self._sorted_ci_list(a.known_words),
            "new_words": self._sorted_ci_list(a.new_words),
            "known_sequence": list(a.known_sequence),
            "new_sequence": list(a.new_sequence),
            "user_words": self._sorted_ci_list(a.user_words),
            "removed_words": self._sorted_ci_list(a.removed_words),
            "learned_words": list(a.learned_session),
            "learned_log": {k: a.learned_log[k] for k in self._sorted_ci_keys(a.learned_log)},
            "word_details": {k: a.word_details[k] for k in self._sorted_ci_keys(a.word_details)},
            "word_ipa": {k: a.word_ipa[k] for k in self._sorted_ci_keys(a.word_ipa)},
            "learn_order_mode": a.learn_order_mode,
            "tongue_twisters": self._sorted_ci_list(a.tongue_twisters),
            "expressions": list(a.expressions),
        }

    def apply_snapshot(self, data: dict):
        a = self.app
        # user_words sammeln (lower)
        raw_user_words = data.get("user_words", []) or []
        user_words_lower = {str(w).strip().lower() for w in raw_user_words if isinstance(w, str) and str(w).strip()}
        a.user_words = set(user_words_lower)

        # Vokabular: (wie in Voca.py) auf lowercase setzen
        vocab_lower = {(w or "").lower() for w in a.vocabulary}
        final_vocab = sorted(vocab_lower | user_words_lower)
        a.vocabulary = final_vocab
        vocab_lower_set = set(a.vocabulary)

        a.removed_words = set((w or "").lower() for w in data.get("removed_words", []) if isinstance(w, str))
        loaded_learned = data.get("learned_words", [])
        a.learned_session = self._unique_preserve_order(
            [w for w in loaded_learned if (isinstance(w, str) and w and w.lower() not in a.removed_words)]
        )
        # details
        raw_details = data.get("word_details", {}) or {}
        cleaned = {}
        if isinstance(raw_details, dict):
            for k, v in raw_details.items():
                if not isinstance(k, str) or not isinstance(v, list):
                    continue
                kl = k.lower()
                entries = []
                for item in v:
                    if not isinstance(item, dict):
                        continue
                    meaning = str(item.get("meaning", "")).strip()
                    if isinstance(item.get("examples"), list):
                        ex_list = [str(e).strip() for e in item.get("examples") if str(e).strip()]
                    else:
                        ex = str(item.get("example", "")).strip()
                        ex_list = [ex] if ex else []
                    pos_list = []
                    if isinstance(item.get("pos"), list):
                        for t in item["pos"]:
                            t = str(t).strip().lower()
                            if t in ("n", "v", "adj", "adv", "prep", "conj") and t not in pos_list:
                                pos_list.append(t)
                    if meaning or ex_list or pos_list:
                        entries.append({"meaning": meaning, "examples": ex_list, "pos": pos_list})
                if entries:
                    cleaned[kl] = entries
        a.word_details = cleaned

        # IPA
        raw_ipa = data.get("word_ipa", {}) or {}
        ipa_cleaned = {}
        if isinstance(raw_ipa, dict):
            for k, v in raw_ipa.items():
                if isinstance(k, str) and isinstance(v, str):
                    val = v.strip()
                    if val:
                        ipa_cleaned[k.lower()] = val
        a.word_ipa = ipa_cleaned

        a.displayed_words = {w for w in data.get("displayed_words", []) if (isinstance(w, str) and w.lower() in vocab_lower_set and w.lower() not in a.removed_words)}
        a.word_history = [w for w in data.get("word_history", []) if (isinstance(w, str) and w.lower() in vocab_lower_set and w.lower() not in a.removed_words)]
        a.known_words = {w for w in data.get("known_words", []) if (isinstance(w, str) and w.lower() in vocab_lower_set and w.lower() not in a.removed_words)}
        a.new_words = {w for w in data.get("new_words", []) if (isinstance(w, str) and w.lower() in vocab_lower_set and w.lower() not in a.removed_words)}

        a.known_sequence = self._unique_preserve_order(
            [w for w in data.get("known_sequence", []) if (w in a.known_words and w.lower() not in a.removed_words)]
        )
        loaded_new_seq = data.get("new_sequence", []) or []
        a.new_sequence = self._unique_preserve_order(
            [w for w in loaded_new_seq if (w in a.new_words and w not in a.known_words and w.lower() not in a.removed_words)]
        )
        for w in a.known_words:
            if w not in a.known_sequence:
                a.known_sequence.append(w)
        for w in a.new_words:
            if w not in a.new_sequence and w not in a.known_words:
                a.new_sequence.append(w)

        if a.word_history:
            cw = data.get("current_word")
            a.current_word = cw if (isinstance(cw, str) and cw.lower() in vocab_lower_set) else a.word_history[-1]
            a.history_index = len(a.word_history) - 1

        a._recompute_remaining()

        modes = ("Zufällig", "Neueste", "Älteste")
        lom = data.get("learn_order_mode", "Zufällig")
        a.learn_order_mode = lom if lom in modes else "Zufällig"

        a.tongue_twisters = set(
            w.lower() for w in (data.get("tongue_twisters", []) or []) if isinstance(w, str)
        )
        raw_expr = data.get("expressions", []) or []
        expr_clean, seen = [], set()
        for s in raw_expr:
            if isinstance(s, str):
                t = s.strip()
                if t and t not in seen:
                    seen.add(t)
                    expr_clean.append(t)
        a.expressions = expr_clean

        raw_log = data.get("learned_log", {}) or {}
        log_cleaned = {}
        if isinstance(raw_log, dict):
            for k, v in raw_log.items():
                if isinstance(k, str) and isinstance(v, str):
                    ks = k.strip().lower()
                    vs = v.strip()
                    if ks and vs:
                        log_cleaned[ks] = vs
        a.learned_log = log_cleaned

    def _unique_preserve_order(self, items):
        seen, out = set(), []
        for w in items:
            if w not in seen:
                seen.add(w)
                out.append(w)
        return out

    # ---- IO ----
    def save_async(self):
        from kivy.clock import Clock
        if self._save_scheduled:
            return
        self._save_scheduled = True
        Clock.schedule_once(lambda dt: self._do_save_async(), 0.2)

    def _do_save_async(self):
        from kivy.clock import Clock
        data = self.build_snapshot()
        path = self.path
        tmp_path = path.with_suffix(".tmp")

        def worker():
            import os
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                os.replace(tmp_path, path)
            except Exception:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink(missing_ok=True)  # type: ignore
                except Exception:
                    pass
            finally:
                Clock.schedule_once(lambda *_: setattr(self, "_save_scheduled", False), 0)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def save_sync(self):
        data = self.build_snapshot()
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        import os
        os.replace(tmp_path, self.path)
        self._save_scheduled = False

    def load(self):
        if not self.path.exists():
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.apply_snapshot(data)
            return True
        except Exception:
            return False

    # ---- Backups ----
    def _subset(self, obj: dict) -> dict:
        # nur relevante Keys für Backup-Vergleich
        relevant_keys = (
            "user_words", "removed_words",
            "known_words", "new_words",
            "known_sequence", "new_sequence",
            "learned_words", "learned_log",
            "word_details", "word_ipa",
            "learn_order_mode", "tongue_twisters",
            "expressions",
        )
        return {k: obj.get(k) for k in relevant_keys}

    def _canonical_str(self, o: dict) -> str:
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    def backup_if_changed(self):
        path = self.path
        if not path.exists():
            return
        backup_dir = Path(path).with_name("back_ups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        # letztes Backup
        pattern = f"{path.stem}_*{path.suffix}"
        candidates = sorted(backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime)
        last_backup = candidates[-1] if candidates else None

        current_str = self._canonical_str(self._subset(self.build_snapshot()))
        prev_str = None
        if last_backup and last_backup.exists():
            try:
                with open(last_backup, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                prev_str = self._canonical_str(self._subset(obj))
            except Exception:
                prev_str = None

        if prev_str == current_str:
            return
        ts = _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup = backup_dir / f"{path.stem}_{ts}{path.suffix}"
        shutil.copy2(path, backup)