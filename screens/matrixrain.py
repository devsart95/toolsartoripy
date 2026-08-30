"""MatrixRain — lluvia digital en la terminal."""
import logging
import random

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from widgets.shared import is_view_active

logger = logging.getLogger(__name__)

FPS = 18
MIN_TAIL, MAX_TAIL = 12, 26

CHARS = (
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモ"
    "ヤユヨラリルレロワヲン0123456789"
    "01$#&@*+=<>[]{}|\\:;\"'.,?!^~"
)

_HEAD  = Style(color="bright_white", bold=True)
_TAIL  = [Style(color=c) for c in (
    "bright_green", "green", "green", "green",
    "dark_green", "dark_green", "dark_green", "dark_green",
)]


class _Drop:
    """Una columna de lluvia."""

    __slots__ = ("chars", "length", "speed", "x", "y")

    def __init__(self, x: int, height: int, stagger: bool = False) -> None:
        self.x = x
        self.reset(height)
        if stagger:
            self.y = random.uniform(-4, height * 0.3)

    def reset(self, height: int) -> None:
        self.y      = random.uniform(-height * 0.6, 0)
        self.speed  = random.uniform(0.6, 1.45)
        self.length = random.randint(MIN_TAIL, MAX_TAIL)
        self.chars  = [random.choice(CHARS) for _ in range(self.length)]

    def update(self, height: int) -> None:
        self.y += self.speed
        if random.random() < 0.12:
            self.chars[random.randrange(self.length)] = random.choice(CHARS)
        if self.y - self.length > height:
            self.reset(height)


def _render(drops: list[_Drop], w: int, h: int) -> Text:
    """Compone el frame agrupando los espacios en runs — un append por
    caracter visible, no uno por celda de la grilla."""
    grid   = [[" "] * w for _ in range(h)]
    styles = [[None] * w for _ in range(h)]

    for d in drops:
        if not 0 <= d.x < w:
            continue
        top = int(d.y)
        for i in range(d.length):
            y = top - i
            if 0 <= y < h:
                grid[y][d.x]   = d.chars[i]
                styles[y][d.x] = _HEAD if i == 0 else _TAIL[min(i, len(_TAIL) - 1)]

    out = Text(no_wrap=True, overflow="crop")
    for y in range(h):
        row, srow, blanks = grid[y], styles[y], []
        for x in range(w):
            st = srow[x]
            if st is None:
                blanks.append(" ")
                continue
            if blanks:
                out.append("".join(blanks))
                blanks.clear()
            out.append(row[x], style=st)
        if blanks:
            out.append("".join(blanks))
        if y < h - 1:
            out.append("\n")
    return out


class MatrixRainView(Container):
    DEFAULT_CSS = """
    MatrixRainView {
        width: 100%;
        height: 100%;
        background: #000000;
    }
    MatrixRainView #mr_view {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._drops: list[_Drop] = []
        self._w = 0
        self._h = 0

    def compose(self) -> ComposeResult:
        yield Static(id="mr_view")

    def on_mount(self) -> None:
        self.set_interval(1 / FPS, self.tick)

    def on_resize(self) -> None:
        self._drops = []

    def refresh_view(self) -> None:
        """Al volver a la vista, la lluvia arranca limpia."""
        self._drops = []

    def _ensure_drops(self, w: int, h: int) -> None:
        if self._drops and (w, h) == (self._w, self._h):
            return
        self._w, self._h = w, h
        self._drops = [_Drop(x, h, stagger=(x % 3 == 0)) for x in range(w)]

    def tick(self) -> None:
        # Sin esta guarda la lluvia seguiria consumiendo CPU en segundo plano
        if not is_view_active(self, "matrixrain"):
            return
        try:
            view = self.query_one("#mr_view", Static)
            w, h = view.content_size.width, view.content_size.height
            if w < 2 or h < 2:
                return
            self._ensure_drops(w, h)
            for d in self._drops:
                d.update(h)
            view.update(_render(self._drops, w, h))
        except Exception:
            logger.exception("No se pudo actualizar MatrixRain")
