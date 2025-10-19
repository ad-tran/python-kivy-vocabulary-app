from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ListProperty, StringProperty, BooleanProperty
from kivy.graphics import Color, Rectangle, RoundedRectangle, StencilPush, StencilUse, StencilUnUse, StencilPop, BorderImage, Line, PushMatrix, PopMatrix, Rotate, Translate
from kivy.core.text import Label as CoreLabel
from kivy.metrics import sp

class RoundedButton(Button):
    corner_radius = NumericProperty(12)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._orig_background_normal = getattr(self, "background_normal", "") or ""
        self._orig_background_down = getattr(self, "background_down", "") or ""
        try:
            self.background_normal = ""
            self.background_down = ""
        except Exception:
            pass
        try:
            alpha = float(self.background_color[3])
        except Exception:
            alpha = 1.0
        self._use_heavy_canvas = bool(alpha > 0.01 or self._orig_background_normal or self._orig_background_down)
        if self._use_heavy_canvas:
            self._build_canvas()
            self.bind(
                pos=self._update_canvas,
                size=self._update_canvas,
                state=self._update_canvas,
                background_color=self._update_canvas,
                border=self._update_canvas,
            )
        else:
            self.bind(background_color=self._maybe_enable_heavy)

    def _maybe_enable_heavy(self, *_):
        if self._use_heavy_canvas:
            return
        try:
            alpha = float(self.background_color[3])
        except Exception:
            alpha = 0.0
        if alpha <= 0.01 and not (self._orig_background_normal or self._orig_background_down):
            return
        self._use_heavy_canvas = True
        try:
            self.unbind(background_color=self._maybe_enable_heavy)
        except Exception:
            pass
        self._build_canvas()
        self.bind(
            pos=self._update_canvas,
            size=self._update_canvas,
            state=self._update_canvas,
            background_color=self._update_canvas,
            border=self._update_canvas,
        )
        self._update_canvas()

    def _current_source(self):
        if self.state == "down" and self._orig_background_down:
            return self._orig_background_down
        return self._orig_background_normal

    def _build_canvas(self):
        if not getattr(self, "_use_heavy_canvas", False):
            return
        self.canvas.before.clear()
        self.canvas.after.clear()
        r = float(self.corner_radius)
        with self.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            self._mask = RoundedRectangle(pos=self.pos, size=self.size, radius=[(r, r)] * 4)
            StencilUse()
            self._bg_color_instr = Color(*self.background_color)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            src = self._current_source()
            if (src):
                self._bg_img = BorderImage(pos=self.pos, size=self.size, source=src, border=self.border)
            else:
                self._bg_img = None
        with self.canvas.after:
            StencilUnUse()
            Color(1, 1, 1, 1)
            self._mask_after = RoundedRectangle(pos=self.pos, size=self.size, radius=[(r, r)] * 4)
            StencilPop()

    def on_corner_radius(self, *_):
        self._update_canvas()

    def _update_canvas(self, *args):
        if not getattr(self, "_use_heavy_canvas", False):
            return
        r = float(self.corner_radius)
        radius = [(r, r)] * 4
        pos = self.pos
        size = self.size
        if hasattr(self, "_mask"):
            self._mask.pos = pos
            self._mask.size = size
            self._mask.radius = radius
        if hasattr(self, "_bg_color_instr"):
            self._bg_color_instr.rgba = self.background_color
        if hasattr(self, "_bg_rect"):
            self._bg_rect.pos = pos
            self._bg_rect.size = size
        if getattr(self, "_bg_img", None) is not None:
            self._bg_img.pos = pos
            self._bg_img.size = size
            try:
                self._bg_img.border = self.border
            except Exception:
                pass
            self._bg_img.source = self._current_source() or ""
        if hasattr(self, "_mask_after"):
            self._mask_after.pos = pos
            self._mask_after.size = size
            self._mask_after.radius = radius

class BarChart(Widget):
    labels = ListProperty([])
    values = ListProperty([])
    max_value = NumericProperty(0)
    bar_color = ListProperty([0.30, 0.60, 1.00, 1.0])     
    bar_colors = ListProperty([])                           
    label_color = ListProperty([0.95, 0.98, 1.00, 1.0])
    axis_color  = ListProperty([0.70, 0.70, 0.80, 0.6])
    bg_color    = ListProperty([0, 0, 0, 0])

    label_sp = NumericProperty(16)
    x_label_angle = NumericProperty(0)
    padding = ListProperty([48, 56, 24, 16])

    show_values  = BooleanProperty(False)
    value_sp     = NumericProperty(14)
    value_color  = ListProperty([0.95, 0.98, 1.00, 1.0])
    value_format = StringProperty("{:.0f}")
    value_offset = NumericProperty(4)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cb = self._redraw
        self.bind(pos=cb, size=cb, labels=cb, values=cb, max_value=cb,
                  label_sp=cb, x_label_angle=cb, padding=cb,
                  show_values=cb, value_sp=cb, value_color=cb, value_format=cb, value_offset=cb,
                  bar_colors=cb)  

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            PushMatrix(); Translate(self.x, self.y)
            Color(*self.bg_color); Rectangle(pos=(0, 0), size=(self.width, self.height))

            l, b, r, t = self.padding
            x0, y0 = l, b
            x1, y1 = self.width - r, self.height - t
            w = max(1, x1 - x0); h = max(1, y1 - y0)

            Color(*self.axis_color)
            Line(points=[x0, y0, x1, y0], width=1)
            Line(points=[x0, y0, x0, y1], width=1)

            n = len(self.values)
            slot = w / n if n else w
            bar_w = slot * 0.6 if n else 0

            tops = []
            if n > 0:
                mv = float(self.max_value or 0) or float(max(self.values) or 1.0)
                for i, v in enumerate(self.values):
                    cx = x0 + i * slot + slot / 2.0
                    left = cx - bar_w / 2.0
                    bh = (v / mv) * (h - 2)
                    # Farbe pro Balken (falls vorhanden), sonst fallback
                    col = (self.bar_colors[i] if i < len(self.bar_colors) and self.bar_colors else self.bar_color)
                    Color(*col)
                    Rectangle(pos=(left, y0), size=(bar_w, bh))
                    tops.append((cx, y0 + bh, v))

            if self.show_values and tops:
                Color(*self.value_color)
                for cx, ty, v in tops:
                    lbl = CoreLabel(text=self.value_format.format(v), font_size=self.value_sp); lbl.refresh()
                    tw, th = lbl.texture.size
                    Rectangle(texture=lbl.texture, pos=(cx - tw / 2.0, ty + self.value_offset), size=(tw, th))

            if self.labels:
                Color(*self.label_color)
                ang = float(self.x_label_angle or 0)
                slot = w / max(1, len(self.labels))
                for i, txt in enumerate(self.labels):
                    lbl = CoreLabel(text=str(txt), font_size=self.label_sp); lbl.refresh()
                    tw, th = lbl.texture.size
                    cx = x0 + i * slot + slot / 2.0
                    if abs(ang) > 0.1:
                        PushMatrix(); Translate(cx, y0 - 6); Rotate(angle=-ang, origin=(0, 0))
                        Rectangle(texture=lbl.texture, pos=(-tw / 2.0, -th), size=(tw, th)); PopMatrix()
                    else:
                        Rectangle(texture=lbl.texture, pos=(cx - tw / 2.0, y0 - th - 6), size=(tw, th))
            PopMatrix()

class GroupedBarChart(Widget):
    labels = ListProperty([])
    series_a = ListProperty([])
    series_b = ListProperty([])
    color_a = ListProperty([0.25, 0.6, 0.25, 1])
    color_b = ListProperty([0.25, 0.55, 0.9, 1])
    bg_color = ListProperty([0, 0, 0, 0])
    axis_color = ListProperty([0.6, 0.6, 0.7, 0.6])
    label_color = ListProperty([0.9, 0.95, 1, 1])
    title_a = StringProperty("A")
    title_b = StringProperty("B")
    max_value = NumericProperty(0)
    label_sp = NumericProperty(16)
    legend_sp = NumericProperty(14)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            size=lambda *_: self._redraw(),
            pos=lambda *_: self._redraw(),
            labels=lambda *_: self._redraw(),
            series_a=lambda *_: self._redraw(),
            series_b=lambda *_: self._redraw(),
            color_a=lambda *_: self._redraw(),
            color_b=lambda *_: self._redraw(),
            max_value=lambda *_: self._redraw(),
        )
    def _draw_text(self, text, x, y, font_size=12, color=(1,1,1,1)):
        if not text: return
        lbl = CoreLabel(text=str(text), font_size=font_size, color=color)
        lbl.refresh()
        tex = lbl.texture
        Rectangle(texture=tex, pos=(x, y), size=tex.size)
    def _redraw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.bg_color)
            Rectangle(pos=self.pos, size=self.size)
            n = len(self.labels)
            if n == 0:
                self._draw_text("Keine Daten", self.x + 10, self.y + self.height/2 - 10, sp(self.label_sp), self.label_color)
                return
            pad_l, pad_r, pad_b, pad_t = 28, 12, 28, 24
            w, h = self.width, self.height
            plot_w = max(1, w - pad_l - pad_r)
            plot_h = max(1, h - pad_b - pad_t)
            vals = []
            if self.series_a: vals += self.series_a
            if self.series_b: vals += self.series_b
            max_v = float(self.max_value or 0) or max(1.0, float(max(vals) if vals else 1))
            Color(*self.axis_color)
            Rectangle(pos=(self.x + pad_l, self.y + pad_b - 1), size=(plot_w, 1))
            Rectangle(pos=(self.x + pad_l, self.y + pad_b), size=(1, plot_h))
            slot = plot_w / n
            gap = min(10, slot * 0.1)
            bw = max(3, (slot - gap) / 2 - gap * 0.5)
            Color(*self.color_a)
            for i in range(n):
                v = float(self.series_a[i]) if i < len(self.series_a) else 0.0
                bh = 0 if v <= 0 else (plot_h * (v / max_v))
                x = self.x + pad_l + i * slot + gap
                Rectangle(pos=(x, self.y + pad_b), size=(bw, bh))
            Color(*self.color_b)
            for i in range(n):
                v = float(self.series_b[i]) if i < len(self.series_b) else 0.0
                bh = 0 if v <= 0 else (plot_h * (v / max_v))
                x = self.x + pad_l + i * slot + gap + bw + gap
                Rectangle(pos=(x, self.y + pad_b), size=(bw, bh))
            for i, lab in enumerate(self.labels):
                x_center = self.x + pad_l + i * slot + slot / 2
                lbl = CoreLabel(text=str(lab), font_size=sp(self.label_sp), color=self.label_color)
                lbl.refresh()
                Rectangle(texture=lbl.texture, pos=(x_center - lbl.texture.width/2, self.y + 6), size=lbl.texture.size)
            leg_x = self.x + pad_l + 6
            leg_y = self.y + self.height - 18
            Color(*self.color_a)
            Rectangle(pos=(leg_x, leg_y), size=(10, 10))
            self._draw_text(self.title_a, leg_x + 14, leg_y - 2, sp(self.legend_sp), self.label_color)
            Color(*self.color_b)
            Rectangle(pos=(leg_x + 100, leg_y), size=(10, 10))
            self._draw_text(self.title_b, leg_x + 114, leg_y - 2, sp(self.legend_sp), self.label_color)