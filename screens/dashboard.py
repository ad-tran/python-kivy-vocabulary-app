from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from ui.widgets import RoundedButton as Button, BarChart
import datetime as _dt
from kivy.graphics import Color, Rectangle
from kivy.uix.anchorlayout import AnchorLayout

class DashboardScreen:
    def open_dashboard_popup(self, *_):
        today = _dt.date.today()
        iso = lambda d: d.isoformat()
        counts_by_day: dict[str, int] = {}
        for lw, ds in (self.learned_log or {}).items():
            try:
                d = _dt.date.fromisoformat((ds or "").strip())
            except Exception:
                continue
            key = iso(d)
            counts_by_day[key] = counts_by_day.get(key, 0) + 1

        week_start = today - _dt.timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        def sum_range(start: _dt.date, end: _dt.date) -> int:
            total = 0
            cur = start
            while (cur <= end):
                total += counts_by_day.get(iso(cur), 0)
                cur += _dt.timedelta(days=1)
            return total

        learned_today = counts_by_day.get(iso(today), 0)
        learned_week = sum_range(week_start, today)
        learned_month = sum_range(month_start, today)
        learned_year = sum_range(year_start, today)

        root = BoxLayout(orientation='vertical', spacing=10, padding=(12, 12, 12, 12))

        summary = GridLayout(cols=2, spacing=3, size_hint=(1, 0.18))
        def _add_row(lbl, val, suffix=""):
            summary.add_widget(Label(text=lbl, font_size=28, color=(0.9,0.95,1,1)))
            summary.add_widget(Label(text=f"{val} {suffix}".strip(), font_size=28, color=(0.9,0.95,1,1)))
        _add_row("Today:", learned_today, "words")
        _add_row("This week:", learned_week, "words")
        _add_row("This month:", learned_month, "words")
        _add_row("This year:", learned_year, "words")
        root.add_widget(summary)

        sv = ScrollView(size_hint=(1, 0.62))
        grid = GridLayout(cols=1, spacing=66, size_hint_y=None, padding=(0, 64, 0, 6))
        grid.bind(minimum_height=grid.setter('height'))
        sv.add_widget(grid)
        root.add_widget(sv)

        def add_section(title: str, chart_widget, height: int = 280):
            box = BoxLayout(orientation='vertical', size_hint_y=None, height=height + 36, spacing=6)
            lbl = Label(text=title, font_size=28, size_hint_y=None, height=36, color=(0.95,0.98,1,1))
            box.add_widget(lbl)
            chart_widget.size_hint = (1, None)
            chart_widget.height = height
            box.add_widget(chart_widget)
            grid.add_widget(box)
            return box, lbl

        # Letzte 10 Tage – navigierbar
        good = list(self.theme.get("good", (0.35, 0.75, 0.35, 1)))
        bad  = list(self.theme.get("bad",  (0.85, 0.25, 0.25, 1)))

        # Legende für beide Diagramme
        def _legend_item(col, text):
            box = BoxLayout(size_hint=(None, 1), width=200, spacing=8)
            sw = Widget(size_hint=(None, 1), width=22)
            with sw.canvas:
                Color(*col)
                rect = Rectangle(pos=sw.pos, size=sw.size)
            sw.bind(pos=lambda w, *_: setattr(rect, "pos", w.pos))
            sw.bind(size=lambda w, *_: setattr(rect, "size", w.size))
            lbl = Label(text=text, font_size=18, color=(0.95,0.98,1,1))
            box.add_widget(sw); box.add_widget(lbl)
            return box

        legend = BoxLayout(size_hint=(None, None), height=32, spacing=24, padding=(6, 0, 6, 0))
        # Breite automatisch an Inhalt anpassen (zentrierbar)
        legend.bind(minimum_width=legend.setter('width'))
        legend.add_widget(_legend_item(good, "same/more learned"))
        legend.add_widget(_legend_item(bad,  "less learned"))
        # unten mittig platzieren
        footer_legend = AnchorLayout(size_hint=(1, None), height=40, anchor_x='center', anchor_y='center')
        footer_legend.add_widget(legend)

        day_state = {"offset": 0}  # 0 = bis heute; +10 = vorige 10 Tage

        chart_10 = BarChart(
            labels=[], values=[], max_value=0,
            bar_color=list(self.theme["primary"]),
            label_color=list(self.theme["text"]), bg_color=[0,0,0,0], axis_color=[0.7,0.7,0.8,0.6],
            label_sp=24, x_label_angle=0,
            padding=[48, 44, 24, 36],
            show_values=True, value_sp=20, value_color=list(self.theme["text"])
        )
        days_box, _ = add_section("Last 10 Days", chart_10, height=300)

        # Pfeile unter dem 10‑Tage‑Diagramm
        nav10 = BoxLayout(size_hint=(1, None), height=54, spacing=12, padding=(0, 6, 0, 0))
        prev10_btn = Button(text="<", font_size=24, size_hint=(None, 1), width=80, background_color=self.theme["closeButton"])
        next10_btn = Button(text=">", font_size=24, size_hint=(None, 1), width=80, background_color=self.theme["closeButton"])
        nav10.add_widget(prev10_btn); nav10.add_widget(Widget()); nav10.add_widget(next10_btn)
        days_box.add_widget(nav10); days_box.height += nav10.height + 6

        def _update_days_chart():
            off = int(day_state["offset"])
            end = today - _dt.timedelta(days=off)
            days = [end - _dt.timedelta(days=i) for i in range(9, -1, -1)]  # 10 Tage
            labels = [d.strftime("%d.%m") for d in days]
            vals = [counts_by_day.get(iso(d), 0) for d in days]
            # Farben: rot, wenn weniger als Vortag; sonst grün
            cols = []
            prev = None
            for v in vals:
                cols.append(good if (prev is None or v >= prev) else bad)
                prev = v
            chart_10.labels = labels
            chart_10.values = vals
            chart_10.bar_colors = cols
            chart_10.max_value = max(vals) if any(vals) else 0
            # ">" nur aktiv, wenn wir nicht im Zukunftsfenster wären
            next10_btn.disabled = (off == 0)

        def _go_prev10(*_):
            day_state["offset"] += 10
            _update_days_chart()
        def _go_next10(*_):
            if day_state["offset"] >= 10:
                day_state["offset"] -= 10
                _update_days_chart()

        prev10_btn.bind(on_release=_go_prev10)
        next10_btn.bind(on_release=_go_next10)
        _update_days_chart()

        # Monate – navigierbar per Jahr
        def month_range(y: int, m: int):
            start = _dt.date(y, m, 1)
            end = (_dt.date(y + 1, 1, 1) - _dt.timedelta(days=1)) if m == 12 else (_dt.date(y, m + 1, 1) - _dt.timedelta(days=1))
            return start, end

        labels_m = [_dt.date(today.year, m, 1).strftime("%b") for m in range(1, 13)]
        # Startjahr ist das aktuelle; vor/zurück per Buttons
        year_state = {"year": today.year}

        chart_m = BarChart(
            labels=labels_m, values=[0]*12, max_value=0,
            bar_color=list(self.theme["accent"]), label_color=list(self.theme["text"]),
            bg_color=[0,0,0,0], axis_color=[0.7,0.7,0.8,0.6],
            label_sp=24, x_label_angle=0,
            padding=[48, 44, 24, 36],   # mehr Top-Padding für Zahlen
            show_values=True, value_sp=20, value_color=list(self.theme["text"])
        )
        months_box, months_title = add_section(f"{today.year}", chart_m, height=280)

        # Navigationsleiste unter dem Monatsdiagramm
        nav = BoxLayout(size_hint=(1, None), height=54, spacing=12, padding=(0, 6, 0, 0))
        prev_btn = Button(text="<", font_size=24, size_hint=(None, 1), width=80, background_color=self.theme["closeButton"])
        next_btn = Button(text=">", font_size=24, size_hint=(None, 1), width=80, background_color=self.theme["closeButton"])
        nav.add_widget(prev_btn)
        nav.add_widget(Widget())  # Spacer mittig
        nav.add_widget(next_btn)
        months_box.add_widget(nav)
        months_box.height += nav.height + 6  # Platz für die Nav einplanen

        # Monatsdaten für ein Jahr berechnen und UI aktualisieren
        def _update_month_chart():
            y = year_state["year"]
            months = [month_range(y, m) for m in range(1, 13)]
            vals = [sum_range(s, e) for (s, e) in months]
            # Farben pro Monat
            colors = []
            prev = None
            for v in vals:
                colors.append(good if (prev is None or v >= prev) else bad)
                prev = v
            chart_m.labels = [_dt.date(y, m, 1).strftime("%b") for m in range(1, 13)]
            chart_m.values = vals
            chart_m.bar_colors = colors
            chart_m.max_value = max(vals) if any(vals) else 0
            months_title.text = f"Months {y}"
            # „>“ nur erlauben, wenn wir in der Vergangenheit sind (kein zukünftiges Jahr)
            next_btn.disabled = (y >= today.year)

        # Button-Handler
        def _go_prev(*_):
            year_state["year"] -= 1
            _update_month_chart()
        def _go_next(*_):
            if year_state["year"] < today.year:
                year_state["year"] += 1
                _update_month_chart()
        prev_btn.bind(on_release=_go_prev)
        next_btn.bind(on_release=_go_next)
        # initiale Füllung
        _update_month_chart()

        # Legende unten mittig anzeigen
        root.add_widget(footer_legend)

        bar = BoxLayout(size_hint=(1, 0.10), spacing=8)
        close_btn = Button(text="Close", font_size=30, background_color=self.theme["closeButton"])
        bar.add_widget(close_btn)
        root.add_widget(bar)
        popup = Popup(title="Dashboard", content=root, size_hint=(0.95, 0.92), auto_dismiss=True)
        close_btn.bind(on_release=lambda *_: popup.dismiss())
        popup.open()