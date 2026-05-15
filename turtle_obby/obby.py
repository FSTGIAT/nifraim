"""
Turtle Obby - 50 levels across 8 obstacle themes.

THEMES (every 6 levels switches theme; final stretch is GAUNTLET):
   1-6   DODGER       red blocks slide up and down between you and the goal
   7-12  SWEEPER      long bars sweep horizontally across the field
  13-18  SPINNER      rotating blades pinwheel around fixed centers
  19-24  MAZE         shrinking gaps in vertical walls
  25-30  BULLET HELL  projectiles fired from the goal line
  31-36  CHASER       enemies that hunt you down across the screen
  37-42  ORBITER      rings of enemies circle fixed points
  43-50  GAUNTLET     every theme combined, escalating to a brutal level 50

CONTROLS
  Arrow keys     move
  Esc            abandon the current run, return to home

REWARDS
  +10 coins per cleared level
  Spend coins on 15 unlockable skins (some with animated rainbow effects)

Progress saves to `save.json` in the same folder as this file.
"""

import json
import math
import random
import turtle
from pathlib import Path


# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------
WIDTH = 900
HEIGHT = 650
PLAYER_RADIUS = 13
GOAL_X = WIDTH // 2 - 35
PLAYER_START_X = -WIDTH // 2 + 50
MOVE_SPEED = 5
TICK_MS = 28
MAX_LEVEL = 50
COINS_PER_LEVEL = 10
SAVE_FILE = Path(__file__).parent / "save.json"


# -----------------------------------------------------------------------------
# SKINS (15 total, prices escalate)
# -----------------------------------------------------------------------------
SKINS = [
    {"id": "green",   "name": "Classic Green",   "color": "#2ecc71", "shape": "turtle",   "price": 0},
    {"id": "blue",    "name": "Ocean Blue",      "color": "#3498db", "shape": "turtle",   "price": 50},
    {"id": "yellow",  "name": "Sunny Yellow",    "color": "#f1c40f", "shape": "turtle",   "price": 120},
    {"id": "purple",  "name": "Royal Purple",    "color": "#9b59b6", "shape": "turtle",   "price": 220},
    {"id": "red",     "name": "Crimson Red",     "color": "#e74c3c", "shape": "turtle",   "price": 350},
    {"id": "bubble",  "name": "Pink Bubble",     "color": "#ff69b4", "shape": "circle",   "price": 500},
    {"id": "ninja",   "name": "Shadow Ninja",    "color": "#1a1a1a", "shape": "triangle", "price": 700},
    {"id": "cyan",    "name": "Cyan Glow",       "color": "#1abc9c", "shape": "turtle",   "price": 950},
    {"id": "gold",    "name": "Gold Champion",   "color": "#d4af37", "shape": "turtle",   "price": 1300},
    {"id": "diamond", "name": "Diamond Edge",    "color": "#b9f2ff", "shape": "diamond",  "price": 1700},
    {"id": "fire",    "name": "Inferno",         "color": "#ff4500", "shape": "flame",    "price": 2200},
    {"id": "ice",     "name": "Frost Wraith",    "color": "#00d4ff", "shape": "star5",    "price": 2800},
    {"id": "void",    "name": "Void Walker",     "color": "#4b0082", "shape": "square",   "price": 3500},
    {"id": "ghost",   "name": "Phantom Glide",   "color": "#dcdcdc", "shape": "circle",   "price": 4500},
    {"id": "rainbow", "name": "Rainbow Master",  "color": "rainbow", "shape": "turtle",   "price": 6000},
]


# -----------------------------------------------------------------------------
# THEMES (each level slot maps to a theme; gauntlet covers 43-50)
# -----------------------------------------------------------------------------
THEMES = [
    {"id": "dodger",   "name": "DODGER",       "bg": "#0f1626", "pattern": "grid",      "accent": "#e74c3c"},
    {"id": "sweeper",  "name": "SWEEPER",      "bg": "#0c2a2a", "pattern": "stripes",   "accent": "#1abc9c"},
    {"id": "spinner",  "name": "SPINNER",      "bg": "#1d0d2e", "pattern": "radial",    "accent": "#9b59b6"},
    {"id": "maze",     "name": "MAZE",         "bg": "#0f1a0f", "pattern": "stones",    "accent": "#27ae60"},
    {"id": "bullets",  "name": "BULLET HELL",  "bg": "#1a0606", "pattern": "crosshair", "accent": "#e74c3c"},
    {"id": "chaser",   "name": "CHASER",       "bg": "#2a1f10", "pattern": "vignette",  "accent": "#e67e22"},
    {"id": "orbiter",  "name": "ORBITER",      "bg": "#0a0f24", "pattern": "stars",     "accent": "#3498db"},
    {"id": "gauntlet", "name": "GAUNTLET",     "bg": "#000000", "pattern": "neon",      "accent": "#ff00ff"},
]


def theme_for_level(level):
    if level <= 6:  return THEMES[0]
    if level <= 12: return THEMES[1]
    if level <= 18: return THEMES[2]
    if level <= 24: return THEMES[3]
    if level <= 30: return THEMES[4]
    if level <= 36: return THEMES[5]
    if level <= 42: return THEMES[6]
    return THEMES[7]


# -----------------------------------------------------------------------------
# SAVE FILE HELPERS
# -----------------------------------------------------------------------------
def fresh_save():
    return {"coins": 0, "owned": ["green"], "current": "green", "highest_level": 1}


def load_save():
    if SAVE_FILE.exists():
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
            default = fresh_save()
            for k, v in default.items():
                if k not in data:
                    data[k] = list(v) if isinstance(v, list) else v
            if "green" not in data["owned"]:
                data["owned"].append("green")
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return fresh_save()


def save_data(data):
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)
    except OSError:
        pass


def find_skin(skin_id):
    for s in SKINS:
        if s["id"] == skin_id:
            return s
    return SKINS[0]


# -----------------------------------------------------------------------------
# CUSTOM SHAPE REGISTRATION
# -----------------------------------------------------------------------------
def star_polygon(points, outer_r, inner_r):
    coords = []
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        a = i * math.pi / points - math.pi / 2
        coords.append((r * math.cos(a), r * math.sin(a)))
    return tuple(coords)


def register_shapes(screen):
    screen.register_shape("diamond", ((0, 14), (12, 0), (0, -14), (-12, 0)))
    screen.register_shape("star5", star_polygon(5, 14, 6))
    screen.register_shape(
        "flame",
        ((0, 16), (5, 6), (11, 9), (8, -3), (10, -13), (3, -8), (0, -13),
         (-3, -8), (-10, -13), (-8, -3), (-11, 9), (-5, 6)),
    )
    screen.register_shape("blade", ((40, 0), (8, 6), (0, 0), (8, -6)))
    screen.register_shape("bullet", ((10, 0), (-6, 5), (-3, 0), (-6, -5)))


# -----------------------------------------------------------------------------
# RAINBOW PALETTE (precomputed for the Rainbow Master skin)
# -----------------------------------------------------------------------------
RAINBOW = [
    "#ff0000", "#ff7f00", "#ffff00", "#7fff00",
    "#00ff00", "#00ff7f", "#00ffff", "#007fff",
    "#0000ff", "#7f00ff", "#ff00ff", "#ff007f",
]


# -----------------------------------------------------------------------------
# OBSTACLE - lightweight wrapper around a turtle plus its per-frame logic.
# -----------------------------------------------------------------------------
class Obstacle:
    def __init__(self, t, update, radius=18, deadly=True):
        self.t = t
        self.update = update
        self.radius = radius
        self.deadly = deadly
        self.dead = False


# -----------------------------------------------------------------------------
# GAME
# -----------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.screen = turtle.Screen()
        self.screen.setup(WIDTH, HEIGHT)
        self.screen.title("Turtle Obby - 50 Levels")
        self.screen.bgcolor("#0f1626")
        self.screen.tracer(0)
        register_shapes(self.screen)

        self.save = load_save()
        self.state = "HOME"
        self.level = max(1, min(MAX_LEVEL, self.save["highest_level"]))
        self.frame = 0

        self.keys = {"Up": False, "Down": False, "Left": False, "Right": False}

        self.bg = turtle.Turtle(visible=False); self.bg.penup(); self.bg.speed(0)
        self.ui = turtle.Turtle(visible=False); self.ui.penup(); self.ui.speed(0)
        self.fx = turtle.Turtle(visible=False); self.fx.penup(); self.fx.speed(0)

        self.player = turtle.Turtle()
        self.player.hideturtle()
        self.player.penup()
        self.player.speed(0)
        self.apply_skin()

        self.goal_t = turtle.Turtle()
        self.goal_t.hideturtle()
        self.goal_t.penup()
        self.goal_t.speed(0)
        self.goal_t.shape("square")
        self.goal_t.shapesize(stretch_wid=22, stretch_len=0.4)
        self.goal_t.color("#2ecc71")
        self.goal_t.goto(GOAL_X, 0)

        self.obstacles = []
        self.walls = []        # list of AABBs (x, y, w, h)
        self.tickers = []      # list of callables(self) run each frame
        self.click_areas = []
        self.shop_scroll = 0

        self.screen.onclick(self.on_click)
        for k in self.keys:
            self.screen.onkeypress(self._make_press(k), k)
            self.screen.onkeyrelease(self._make_release(k), k)
        self.screen.onkey(self.escape_to_home, "Escape")
        self.screen.listen()

        self.show_home()
        self.screen.ontimer(self.tick, TICK_MS)

    # =========================================================================
    # INPUT
    # =========================================================================
    def _make_press(self, k):
        def f():
            self.keys[k] = True
        return f

    def _make_release(self, k):
        def f():
            self.keys[k] = False
        return f

    def escape_to_home(self):
        if self.state == "GAME":
            self.show_home()

    def on_click(self, x, y):
        for x1, y1, x2, y2, cb in list(self.click_areas):
            if x1 <= x <= x2 and y1 <= y <= y2:
                cb()
                return

    # =========================================================================
    # UI PRIMITIVES
    # =========================================================================
    def clear_ui(self):
        self.ui.clear()
        self.bg.clear()
        self.fx.clear()
        self.click_areas = []
        self.goal_t.hideturtle()

    def clear_obstacles(self):
        for o in self.obstacles:
            try:
                o.t.hideturtle()
                o.t.clear()
            except (turtle.TurtleGraphicsError, AttributeError):
                pass
        self.obstacles = []
        self.walls = []
        self.tickers = []

    def draw_rect(self, x, y, w, h, color, outline=None):
        self.bg.penup()
        self.bg.goto(x - w / 2, y - h / 2)
        self.bg.setheading(0)
        self.bg.pencolor(outline if outline else color)
        self.bg.fillcolor(color)
        self.bg.begin_fill()
        self.bg.pendown()
        for _ in range(2):
            self.bg.forward(w); self.bg.left(90)
            self.bg.forward(h); self.bg.left(90)
        self.bg.end_fill()
        self.bg.penup()
        self.bg.pencolor("white")

    def draw_line(self, x1, y1, x2, y2, color, width=1):
        self.bg.penup()
        self.bg.goto(x1, y1)
        self.bg.pencolor(color)
        self.bg.pensize(width)
        self.bg.pendown()
        self.bg.goto(x2, y2)
        self.bg.penup()
        self.bg.pensize(1)

    def draw_filled_circle(self, x, y, r, color):
        self.bg.penup()
        self.bg.goto(x, y - r)
        self.bg.setheading(0)
        self.bg.pencolor(color)
        self.bg.fillcolor(color)
        self.bg.begin_fill()
        self.bg.circle(r)
        self.bg.end_fill()
        self.bg.penup()

    def write_text(self, x, y, text, size=14, color="white", bold=False, anchor="center"):
        self.ui.penup()
        self.ui.goto(x, y)
        self.ui.pencolor(color)
        style = "bold" if bold else "normal"
        self.ui.write(text, align=anchor, font=("Arial", size, style))

    def write_fx(self, x, y, text, size=14, color="white", bold=False):
        self.fx.penup()
        self.fx.goto(x, y)
        self.fx.pencolor(color)
        style = "bold" if bold else "normal"
        self.fx.write(text, align="center", font=("Arial", size, style))

    def draw_button(self, x, y, w, h, label, callback, bg="#3498db", fg="white", size=14):
        self.draw_rect(x, y, w, h, bg, outline="#ffffff")
        self.write_text(x, y - size + 2, label, size=size, color=fg, bold=True)
        self.click_areas.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2, callback))

    # =========================================================================
    # BACKGROUND PATTERNS (each theme paints its own arena)
    # =========================================================================
    def draw_background(self, theme):
        self.screen.bgcolor(theme["bg"])
        pat = theme["pattern"]
        if   pat == "grid":      self._pat_grid("#1a2440")
        elif pat == "stripes":   self._pat_stripes("#11383a")
        elif pat == "radial":    self._pat_radial("#2b1640")
        elif pat == "stones":    self._pat_stones("#172218")
        elif pat == "crosshair": self._pat_crosshair("#3a1414")
        elif pat == "vignette":  self._pat_vignette("#3a2a18")
        elif pat == "stars":     self._pat_stars("#202a4a")
        elif pat == "neon":      self._pat_neon("#1a1a1a")

    def _pat_grid(self, c):
        step = 50
        for x in range(-WIDTH // 2, WIDTH // 2 + 1, step):
            self.draw_line(x, -HEIGHT // 2, x, HEIGHT // 2, c)
        for y in range(-HEIGHT // 2, HEIGHT // 2 + 1, step):
            self.draw_line(-WIDTH // 2, y, WIDTH // 2, y, c)

    def _pat_stripes(self, c):
        for y in range(-HEIGHT // 2, HEIGHT // 2, 40):
            self.draw_rect(0, y + 10, WIDTH, 16, c)

    def _pat_radial(self, c):
        for a in range(0, 360, 12):
            rad = math.radians(a)
            x = math.cos(rad) * 700
            y = math.sin(rad) * 700
            self.draw_line(0, 0, x, y, c)

    def _pat_stones(self, c):
        rng = random.Random(42)
        for _ in range(70):
            x = rng.uniform(-WIDTH / 2, WIDTH / 2)
            y = rng.uniform(-HEIGHT / 2, HEIGHT / 2)
            r = rng.uniform(6, 20)
            self.draw_filled_circle(x, y, r, c)

    def _pat_crosshair(self, c):
        for i in range(-5, 6):
            x = i * 100
            self.draw_line(x, -HEIGHT // 2, x, HEIGHT // 2, c, width=2 if i == 0 else 1)
        for i in range(-3, 4):
            y = i * 100
            self.draw_line(-WIDTH // 2, y, WIDTH // 2, y, c, width=2 if i == 0 else 1)

    def _pat_vignette(self, c):
        for r in range(500, 80, -60):
            self.draw_filled_circle(0, 0, r, c)
        self.draw_filled_circle(0, 0, 60, "#1a1208")

    def _pat_stars(self, c):
        rng = random.Random(13)
        for _ in range(140):
            x = rng.uniform(-WIDTH / 2, WIDTH / 2)
            y = rng.uniform(-HEIGHT / 2, HEIGHT / 2)
            r = rng.uniform(1, 3)
            self.draw_filled_circle(x, y, r, c)

    def _pat_neon(self, c):
        for i in range(20):
            x = -WIDTH / 2 + i * (WIDTH / 20)
            self.draw_line(x, -HEIGHT / 2, x + 60, HEIGHT / 2, c)
        for i in range(15):
            y = -HEIGHT / 2 + i * (HEIGHT / 15)
            self.draw_line(-WIDTH / 2, y, WIDTH / 2, y + 30, c)

    # =========================================================================
    # SKINS
    # =========================================================================
    def apply_skin(self):
        skin = find_skin(self.save["current"])
        self.player.shape(skin["shape"])
        if skin["color"] != "rainbow":
            self.player.color(skin["color"])
        self.player.shapesize(1.4, 1.4)

    def update_rainbow_skin(self):
        skin = find_skin(self.save["current"])
        if skin["color"] == "rainbow":
            self.player.color(RAINBOW[(self.frame // 3) % len(RAINBOW)])

    # =========================================================================
    # SCREENS
    # =========================================================================
    def show_home(self):
        self.state = "HOME"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()
        self.screen.bgcolor("#0f1626")

        self._pat_stars("#1a2244")
        self.draw_rect(0, 220, 560, 100, "#1f2a44", outline="#2c3e50")
        self.write_text(0, 232, "TURTLE  OBBY", size=42, color="#f1c40f", bold=True)
        self.write_text(0, 188, "50 levels - 8 obby themes - 15 skins", size=12, color="#bdc3c7")

        self.draw_rect(0, 88, 360, 70, "#1a2438", outline="#ffffff")
        self.write_text(0, 102, f"Coins: {self.save['coins']}", size=20, color="#f1c40f", bold=True)
        self.write_text(0, 68, f"Highest level reached: {self.save['highest_level']} / {MAX_LEVEL}",
                        size=12, color="#95a5a6")

        self.draw_button(0, -5, 260, 60, "START GAME", self.start_game, bg="#27ae60")
        self.draw_button(0, -85, 260, 60, "SHOP", self.show_shop, bg="#9b59b6")
        self.draw_button(0, -165, 260, 50, "RESET PROGRESS", self.confirm_reset, bg="#7f1010", size=12)

        self.write_text(0, -230, "Arrow keys move. Esc abandons a level.", size=11, color="#7f8c8d")
        self.write_text(0, -255, "Reach the green portal on the right side.", size=11, color="#7f8c8d")

    def confirm_reset(self):
        self.state = "CONFIRM_RESET"
        self.clear_ui()
        self.write_text(0, 60, "Reset all progress?", size=22, color="#e74c3c", bold=True)
        self.write_text(0, 25, "Coins, owned skins and level progress will be lost.",
                        size=12, color="#bdc3c7")
        self.draw_button(-110, -40, 180, 55, "YES, RESET", self.do_reset, bg="#e74c3c")
        self.draw_button(110, -40, 180, 55, "CANCEL", self.show_home, bg="#34495e")

    def do_reset(self):
        self.save = fresh_save()
        save_data(self.save)
        self.level = 1
        self.apply_skin()
        self.show_home()

    def show_shop(self):
        self.state = "SHOP"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()
        self.screen.bgcolor("#0f1626")
        self._pat_grid("#1a2440")

        self.draw_rect(0, 270, WIDTH, 70, "#1f2a44")
        self.write_text(0, 270, "SHOP", size=28, color="#f1c40f", bold=True)
        self.write_text(0, 244, f"Coins: {self.save['coins']}", size=14, color="#f1c40f")

        for i, skin in enumerate(SKINS):
            col = i % 2
            row = i // 2
            x = -200 + col * 400
            y = 195 - row * 58

            owned = skin["id"] in self.save["owned"]
            selected = skin["id"] == self.save["current"]
            affordable = self.save["coins"] >= skin["price"]

            if selected:
                label = f"{skin['name']}  [EQUIPPED]"
                cb = lambda s=skin: None
                bg = skin["color"] if skin["color"] != "rainbow" else "#ff00ff"
            elif owned:
                label = f"{skin['name']}  [TAP TO EQUIP]"
                cb = lambda s=skin: self.equip(s)
                bg = skin["color"] if skin["color"] != "rainbow" else "#ff00ff"
            elif affordable:
                label = f"{skin['name']}  -  BUY {skin['price']}"
                cb = lambda s=skin: self.buy(s)
                bg = skin["color"] if skin["color"] != "rainbow" else "#ff00ff"
            else:
                label = f"{skin['name']}  -  LOCKED ({skin['price']})"
                cb = lambda s=skin: None
                bg = "#555555"

            self.draw_button(x, y, 360, 50, label, cb, bg=bg, fg="white", size=11)

        self.draw_button(0, -270, 200, 50, "BACK", self.show_home, bg="#34495e")

    def start_game(self):
        if self.level > MAX_LEVEL:
            self.level = MAX_LEVEL
        self.state = "GAME"
        self.clear_obstacles()
        self.clear_ui()

        theme = theme_for_level(self.level)
        self.draw_background(theme)

        self.build_level(self.level, theme)

        self.write_text(-WIDTH // 2 + 110, HEIGHT // 2 - 32,
                        f"Level {self.level} / {MAX_LEVEL}", size=14, color="white", bold=True)
        self.write_text(0, HEIGHT // 2 - 32,
                        f"{theme['name']}", size=14, color=theme["accent"], bold=True)
        self.write_text(WIDTH // 2 - 110, HEIGHT // 2 - 32,
                        f"Coins: {self.save['coins']}", size=14, color="#f1c40f", bold=True)

        self.goal_t.color("#2ecc71")
        self.goal_t.goto(GOAL_X, 0)
        self.goal_t.showturtle()

        self.player.goto(PLAYER_START_X, 0)
        self.apply_skin()
        self.player.showturtle()

    def show_level_complete(self):
        self.state = "WIN"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()
        self.screen.bgcolor("#0f1626")
        self._pat_stars("#1a2244")

        # confetti effect
        rng = random.Random(self.level)
        for _ in range(30):
            x = rng.uniform(-WIDTH / 2 + 40, WIDTH / 2 - 40)
            y = rng.uniform(-50, 220)
            color = rng.choice(["#f1c40f", "#e74c3c", "#2ecc71", "#3498db", "#9b59b6"])
            self.draw_filled_circle(x, y, rng.uniform(4, 10), color)

        self.draw_rect(0, 140, 520, 90, "#1f2a44", outline="#ffffff")
        self.write_text(0, 150, f"LEVEL {self.level} CLEAR!", size=28, color="#2ecc71", bold=True)
        self.write_text(0, 110, f"+{COINS_PER_LEVEL} coins", size=18, color="#f1c40f", bold=True)
        self.write_text(0, 80, f"Total: {self.save['coins']} coins", size=13, color="white")

        next_level = min(self.level + 1, MAX_LEVEL)
        self.level = next_level
        next_theme = theme_for_level(next_level)
        self.write_text(0, 30, f"Next: {next_theme['name']}", size=14,
                        color=next_theme["accent"], bold=True)

        self.draw_button(0, -30, 280, 55, f"NEXT LEVEL ({next_level})", self.start_game, bg="#27ae60")
        self.draw_button(0, -100, 280, 50, "HOME", self.show_home, bg="#34495e")
        self.draw_button(0, -160, 280, 45, "SHOP", self.show_shop, bg="#9b59b6")

    def show_game_over(self):
        self.state = "LOSE"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()
        self.screen.bgcolor("#1a0606")
        self._pat_crosshair("#3a1414")

        self.draw_rect(0, 100, 460, 90, "#3a1414", outline="#e74c3c")
        self.write_text(0, 110, "OOPS!", size=42, color="#e74c3c", bold=True)
        self.write_text(0, 70, "You hit an obstacle.", size=15, color="white")
        self.write_text(0, 30, "Tip: keep moving - hesitation kills.", size=12, color="#bdc3c7")

        self.draw_button(0, -30, 260, 55, "TRY AGAIN", self.start_game, bg="#e74c3c")
        self.draw_button(0, -100, 260, 50, "HOME", self.show_home, bg="#34495e")

    def show_final_victory(self):
        self.state = "FINAL"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()
        self.screen.bgcolor("#000000")
        self._pat_neon("#222244")

        rng = random.Random(99)
        for _ in range(80):
            x = rng.uniform(-WIDTH / 2 + 40, WIDTH / 2 - 40)
            y = rng.uniform(-HEIGHT / 2 + 40, HEIGHT / 2 - 60)
            color = rng.choice(RAINBOW)
            self.draw_filled_circle(x, y, rng.uniform(2, 8), color)

        self.write_text(0, 140, "CHAMPION!", size=50, color="#f1c40f", bold=True)
        self.write_text(0, 90, "You conquered all 50 levels.", size=18, color="white")
        self.write_text(0, 60, f"Total coins: {self.save['coins']}", size=15, color="#f1c40f")
        self.write_text(0, 30, "Now go spend them on the silliest skin.", size=12, color="#bdc3c7")

        self.draw_button(0, -30, 280, 55, "HOME", self.show_home, bg="#27ae60")
        self.draw_button(0, -100, 280, 50, "SHOP", self.show_shop, bg="#9b59b6")

    # =========================================================================
    # SHOP ACTIONS
    # =========================================================================
    def equip(self, skin):
        if skin["id"] not in self.save["owned"]:
            return
        self.save["current"] = skin["id"]
        save_data(self.save)
        self.apply_skin()
        self.show_shop()

    def buy(self, skin):
        if skin["id"] in self.save["owned"]:
            return
        if self.save["coins"] < skin["price"]:
            return
        self.save["coins"] -= skin["price"]
        self.save["owned"].append(skin["id"])
        self.save["current"] = skin["id"]
        save_data(self.save)
        self.apply_skin()
        self.show_shop()

    # =========================================================================
    # OBSTACLE FACTORIES
    # =========================================================================
    def _new_turtle(self, shape, color, stretch=(1.4, 1.4)):
        t = turtle.Turtle()
        t.shape(shape)
        t.color(color)
        t.shapesize(stretch[0], stretch[1])
        t.penup()
        t.speed(0)
        return t

    def make_vertical_block(self, x, top, bottom, speed, color):
        t = self._new_turtle("square", color, stretch=(1.6, 1.6))
        y0 = random.uniform(bottom, top)
        t.goto(x, y0)
        dy = speed * random.choice([-1, 1])

        def update(o, _self=self, _state={"dy": dy}):
            ox, oy = o.t.position()
            oy += _state["dy"]
            if oy > top:
                oy = top
                _state["dy"] = -abs(_state["dy"])
            elif oy < bottom:
                oy = bottom
                _state["dy"] = abs(_state["dy"])
            o.t.goto(ox, oy)

        return Obstacle(t, update, radius=18)

    def make_horizontal_bar(self, y, length, speed, color):
        t = self._new_turtle("square", color, stretch=(0.6, length / 20))
        x0 = random.uniform(-WIDTH // 2 + 100, WIDTH // 2 - 100)
        t.goto(x0, y)
        dx = speed * random.choice([-1, 1])

        def update(o, _state={"dx": dx}):
            ox, oy = o.t.position()
            ox += _state["dx"]
            left_lim = -WIDTH // 2 + length // 2 + 20
            right_lim = WIDTH // 2 - length // 2 - 20
            if ox > right_lim:
                ox = right_lim
                _state["dx"] = -abs(_state["dx"])
            elif ox < left_lim:
                ox = left_lim
                _state["dx"] = abs(_state["dx"])
            o.t.goto(ox, oy)

        return Obstacle(t, update, radius=length // 2)

    def make_blade(self, cx, cy, arm_length, n_blades, omega, color):
        sentinels = []
        for arm in range(n_blades):
            for i in range(1, 4):
                r = arm_length * i / 3
                t = self._new_turtle("circle", color, stretch=(0.7, 0.7))
                phase = (arm * 2 * math.pi / n_blades)

                def update(o, _r=r, _phase=phase, _cx=cx, _cy=cy, _omega=omega, _self=self):
                    angle = _self.frame * _omega + _phase
                    x = _cx + _r * math.cos(angle)
                    y = _cy + _r * math.sin(angle)
                    o.t.goto(x, y)

                sentinels.append(Obstacle(t, update, radius=11))
        return sentinels

    def make_bullet(self, x, y, speed, color):
        t = self._new_turtle("circle", color, stretch=(0.5, 0.5))
        t.goto(x, y)

        def update(o, _self=self, _speed=speed):
            ox, oy = o.t.position()
            ox -= _speed
            if ox < -WIDTH / 2 - 30:
                ox = WIDTH / 2 + random.uniform(20, 200)
                oy = random.uniform(-HEIGHT / 2 + 60, HEIGHT / 2 - 80)
            o.t.goto(ox, oy)

        return Obstacle(t, update, radius=8)

    def make_chaser(self, x, y, speed, color):
        t = self._new_turtle("triangle", color, stretch=(1.2, 1.2))
        t.goto(x, y)

        def update(o, _self=self, _speed=speed):
            px, py = _self.player.position()
            ox, oy = o.t.position()
            dx, dy = px - ox, py - oy
            d = math.hypot(dx, dy) + 0.001
            o.t.setheading(math.degrees(math.atan2(dy, dx)))
            o.t.goto(ox + dx / d * _speed, oy + dy / d * _speed)

        return Obstacle(t, update, radius=14)

    def make_orbiter(self, cx, cy, r, phase, omega, color):
        t = self._new_turtle("circle", color, stretch=(0.9, 0.9))

        def update(o, _self=self, _cx=cx, _cy=cy, _r=r, _phase=phase, _omega=omega):
            angle = _self.frame * _omega + _phase
            x = _cx + _r * math.cos(angle)
            y = _cy + _r * math.sin(angle)
            o.t.goto(x, y)

        return Obstacle(t, update, radius=13)

    # =========================================================================
    # LEVEL BUILDERS (per theme; difficulty scales with the level number)
    # =========================================================================
    def build_level(self, level, theme):
        random.seed(level * 1237 + 11)
        builder = {
            "dodger":   self.build_dodger,
            "sweeper":  self.build_sweeper,
            "spinner":  self.build_spinner,
            "maze":     self.build_maze,
            "bullets":  self.build_bullets,
            "chaser":   self.build_chaser,
            "orbiter":  self.build_orbiter,
            "gauntlet": self.build_gauntlet,
        }[theme["id"]]
        builder(level)

    # --- 1-6: DODGER -------------------------------------------------------
    def build_dodger(self, level):
        n = 3 + (level - 1) // 2          # 3..5
        speed = 1.8 + (level - 1) * 0.45  # 1.8..4.1
        accent = "#e74c3c"
        lane_min = -WIDTH // 2 + 130
        lane_max = GOAL_X - 50
        for i in range(n):
            x = lane_min + (lane_max - lane_min) * (i + 1) / (n + 1)
            top = random.uniform(60, HEIGHT // 2 - 80)
            bottom = -random.uniform(60, HEIGHT // 2 - 80)
            self.obstacles.append(self.make_vertical_block(x, top, bottom, speed, accent))

    # --- 7-12: SWEEPER -----------------------------------------------------
    def build_sweeper(self, level):
        idx = level - 7
        n = 4 + idx // 2          # 4..6
        speed = 2.2 + idx * 0.5
        accent = "#1abc9c"
        for i in range(n):
            y = -HEIGHT // 2 + 80 + i * (HEIGHT - 180) / max(1, n - 1)
            length = random.randint(140, 220)
            self.obstacles.append(self.make_horizontal_bar(y, length, speed, accent))
        # plus a couple of vertical hazards near the goal so it isn't all linear
        for i in range(2):
            x = GOAL_X - 70 - i * 60
            self.obstacles.append(self.make_vertical_block(x, 180, -180, 3.0 + idx * 0.2, "#16a085"))

    # --- 13-18: SPINNER ---------------------------------------------------
    def build_spinner(self, level):
        idx = level - 13
        n_centers = 2 + idx // 2          # 2..4
        n_blades = 3 if idx < 3 else 4
        omega = 0.05 + idx * 0.012
        arm_len = 80 + idx * 6
        accent = "#9b59b6"
        for i in range(n_centers):
            cx = -WIDTH // 2 + 180 + i * (WIDTH - 360) / max(1, n_centers - 1)
            cy = random.choice([-90, 90, 0])
            self.obstacles.extend(self.make_blade(cx, cy, arm_len, n_blades, omega, accent))

    # --- 19-24: MAZE ------------------------------------------------------
    def build_maze(self, level):
        idx = level - 19
        n_walls = 4 + idx              # 4..9
        gap_h = 130 - idx * 10         # 130..80
        wall_color = "#7f8c8d"
        for i in range(n_walls):
            x = -WIDTH // 2 + 140 + i * (WIDTH - 260) / max(1, n_walls)
            gap_y = random.uniform(-150, 150)
            gap_top = gap_y + gap_h / 2
            gap_bot = gap_y - gap_h / 2
            # top half wall
            top_y = (HEIGHT // 2 + gap_top) / 2
            top_h = HEIGHT // 2 - gap_top
            self.walls.append((x, top_y, 22, top_h))
            # bottom half wall
            bot_y = (-HEIGHT // 2 + gap_bot) / 2
            bot_h = gap_bot + HEIGHT // 2
            self.walls.append((x, bot_y, 22, bot_h))
        for wx, wy, ww, wh in self.walls:
            self.draw_rect(wx, wy, ww, wh, wall_color, outline="#bdc3c7")
        # add a moving block roaming vertically in front of the goal for spice
        if idx >= 2:
            self.obstacles.append(
                self.make_vertical_block(GOAL_X - 60, 200, -200, 2.5 + idx * 0.3, "#27ae60")
            )

    # --- 25-30: BULLET HELL -----------------------------------------------
    def build_bullets(self, level):
        idx = level - 25
        n_bullets = 8 + idx * 2         # 8..18
        speed = 3.5 + idx * 0.5
        accent = "#e74c3c"
        for i in range(n_bullets):
            x = WIDTH / 2 + random.uniform(0, 600)
            y = random.uniform(-HEIGHT / 2 + 60, HEIGHT / 2 - 80)
            self.obstacles.append(self.make_bullet(x, y, speed, accent))
        # plus a couple of stationary blocks as cover/obstruction
        for i in range(2):
            x = -WIDTH // 2 + 220 + i * 200
            y = random.choice([-150, 150])
            self.obstacles.append(self.make_vertical_block(x, y + 80, y - 80, 1.5, "#7f1010"))

    # --- 31-36: CHASER ----------------------------------------------------
    def build_chaser(self, level):
        idx = level - 31
        n = 2 + idx // 2                  # 2..4
        speed = 1.9 + idx * 0.25
        accent = "#e67e22"
        for i in range(n):
            angle = i * 2 * math.pi / n
            x = math.cos(angle) * 250
            y = math.sin(angle) * 200
            self.obstacles.append(self.make_chaser(x, y, speed, accent))
        # a couple of vertical blockers force route choices
        for i in range(2):
            x = -100 + i * 200
            self.obstacles.append(self.make_vertical_block(x, 180, -180, 2.2 + idx * 0.2, "#a04015"))

    # --- 37-42: ORBITER ---------------------------------------------------
    def build_orbiter(self, level):
        idx = level - 37
        n_centers = 2 + idx // 2          # 2..4
        ring_size = 5 + idx               # 5..10
        omega = 0.04 + idx * 0.01
        accent = "#3498db"
        for i in range(n_centers):
            cx = -WIDTH // 2 + 220 + i * (WIDTH - 440) / max(1, n_centers - 1)
            cy = random.choice([-80, 0, 80])
            r = 90 + idx * 4
            for k in range(ring_size):
                phase = k * 2 * math.pi / ring_size
                self.obstacles.append(self.make_orbiter(cx, cy, r, phase, omega, accent))

    # --- 43-50: GAUNTLET --------------------------------------------------
    def build_gauntlet(self, level):
        idx = level - 43                  # 0..7
        difficulty = 1.0 + idx * 0.15

        # vertical dodgers
        for i in range(3):
            x = -WIDTH // 2 + 180 + i * 100
            self.obstacles.append(self.make_vertical_block(
                x, 200, -200, 2.5 * difficulty, "#e74c3c"))

        # one sweeper
        self.obstacles.append(self.make_horizontal_bar(
            120, 180, 3.0 * difficulty, "#1abc9c"))
        self.obstacles.append(self.make_horizontal_bar(
            -120, 180, 3.0 * difficulty, "#1abc9c"))

        # spinner in the middle
        self.obstacles.extend(self.make_blade(
            0, 0, 95, 4, 0.06 * difficulty, "#9b59b6"))

        # a chaser
        if idx >= 1:
            self.obstacles.append(self.make_chaser(
                280, 200, 1.8 * difficulty, "#e67e22"))
        if idx >= 3:
            self.obstacles.append(self.make_chaser(
                280, -200, 1.8 * difficulty, "#e67e22"))

        # bullets from the goal side
        n_bullets = 4 + idx
        for i in range(n_bullets):
            x = WIDTH / 2 + random.uniform(0, 500)
            y = random.uniform(-HEIGHT / 2 + 60, HEIGHT / 2 - 80)
            self.obstacles.append(self.make_bullet(x, y, 3.5 + idx * 0.4, "#ff0050"))

        # a small orbiter ring near the goal at higher gauntlet levels
        if idx >= 4:
            for k in range(6):
                phase = k * 2 * math.pi / 6
                self.obstacles.append(self.make_orbiter(
                    GOAL_X - 110, 0, 60, phase, 0.07 * difficulty, "#3498db"))

        # final level: extra everything
        if level == 50:
            for k in range(8):
                phase = k * 2 * math.pi / 8
                self.obstacles.append(self.make_orbiter(
                    -200, 0, 70, phase, 0.08, "#ff00ff"))
            self.obstacles.extend(self.make_blade(-340, 0, 90, 4, 0.07, "#ff00ff"))

    # =========================================================================
    # GAME LOOP
    # =========================================================================
    def tick(self):
        self.frame += 1
        if self.state == "GAME":
            self.update_game()
            self.update_goal_pulse()
        self.update_rainbow_skin()
        self.screen.update()
        self.screen.ontimer(self.tick, TICK_MS)

    def update_goal_pulse(self):
        pulse = 0.5 + 0.5 * math.sin(self.frame * 0.12)
        try:
            self.goal_t.color((0.15 + 0.25 * pulse, 0.7 + 0.2 * pulse, 0.35 + 0.25 * pulse))
        except turtle.TurtleGraphicsError:
            pass

    def update_game(self):
        px, py = self.player.position()
        if self.keys["Up"]:    py += MOVE_SPEED
        if self.keys["Down"]:  py -= MOVE_SPEED
        if self.keys["Left"]:  px -= MOVE_SPEED
        if self.keys["Right"]: px += MOVE_SPEED
        px = max(-WIDTH // 2 + 20, min(WIDTH // 2 - 20, px))
        py = max(-HEIGHT // 2 + 20, min(HEIGHT // 2 - 80, py))

        # collision against walls (maze theme) blocks movement and kills
        for wx, wy, ww, wh in self.walls:
            if (abs(px - wx) < (PLAYER_RADIUS + ww / 2)
                    and abs(py - wy) < (PLAYER_RADIUS + wh / 2)):
                self.show_game_over()
                return

        self.player.goto(px, py)

        # update obstacles + collision checks
        for o in self.obstacles:
            o.update(o)
            if not o.deadly:
                continue
            ox, oy = o.t.position()
            hit = PLAYER_RADIUS + o.radius
            if abs(px - ox) < hit and abs(py - oy) < hit:
                d = math.hypot(px - ox, py - oy)
                if d < hit:
                    self.show_game_over()
                    return

        # win condition
        if px >= GOAL_X - 6:
            self.win_level()

    def win_level(self):
        self.save["coins"] += COINS_PER_LEVEL
        if self.level >= self.save["highest_level"]:
            self.save["highest_level"] = min(MAX_LEVEL, self.level + 1)
        save_data(self.save)

        if self.level >= MAX_LEVEL:
            self.show_final_victory()
        else:
            self.show_level_complete()


# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
def main():
    Game()
    turtle.mainloop()


if __name__ == "__main__":
    main()
