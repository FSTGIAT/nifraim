"""
Turtle Obby - a 50-level obstacle course game built with Python's turtle module.

How to play:
    python obby.py

Controls:
    Arrow keys = move
    Escape     = leave a level and return to the home screen

Goal:
    Reach the green line on the right of the screen without touching any
    red obstacle. Each level cleared = +10 coins. Spend coins in the shop
    to unlock cooler (and more expensive) skins.

Progress is saved to `save.json` in the same folder as this file.
"""

import json
import random
import turtle
from pathlib import Path

WIDTH, HEIGHT = 800, 600
PLAYER_RADIUS = 15
OBSTACLE_RADIUS = 18
GOAL_X = WIDTH // 2 - 30
PLAYER_START_X = -WIDTH // 2 + 40
MOVE_SPEED = 5
TICK_MS = 30
MAX_LEVEL = 50

SAVE_FILE = Path(__file__).parent / "save.json"

SKINS = [
    {"id": "green",   "name": "Classic Green",   "color": "#2ecc71", "shape": "turtle", "price": 0},
    {"id": "blue",    "name": "Ocean Blue",      "color": "#3498db", "shape": "turtle", "price": 50},
    {"id": "yellow",  "name": "Sunny Yellow",    "color": "#f1c40f", "shape": "turtle", "price": 120},
    {"id": "purple",  "name": "Royal Purple",    "color": "#9b59b6", "shape": "turtle", "price": 220},
    {"id": "red",     "name": "Crimson Red",     "color": "#e74c3c", "shape": "turtle", "price": 350},
    {"id": "bubble",  "name": "Pink Bubble",     "color": "#ff69b4", "shape": "circle", "price": 500},
    {"id": "black",   "name": "Shadow Knight",   "color": "#1a1a1a", "shape": "turtle", "price": 700},
    {"id": "cyan",    "name": "Cyan Glow",       "color": "#1abc9c", "shape": "turtle", "price": 950},
    {"id": "gold",    "name": "Gold Champion",   "color": "#d4af37", "shape": "turtle", "price": 1300},
    {"id": "magenta", "name": "Rainbow Master",  "color": "#ff00ff", "shape": "turtle", "price": 2000},
]

DEFAULT_SAVE = {
    "coins": 0,
    "owned": ["green"],
    "current": "green",
    "highest_level": 1,
}


def load_save():
    if SAVE_FILE.exists():
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
            for k, v in DEFAULT_SAVE.items():
                data.setdefault(k, v if not isinstance(v, list) else list(v))
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"coins": 0, "owned": ["green"], "current": "green", "highest_level": 1}


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


class Game:
    def __init__(self):
        self.screen = turtle.Screen()
        self.screen.setup(WIDTH, HEIGHT)
        self.screen.title("Turtle Obby - 50 Levels")
        self.screen.bgcolor("#0f1626")
        self.screen.tracer(0)

        self.save = load_save()
        self.state = "HOME"
        self.level = max(1, min(MAX_LEVEL, self.save["highest_level"]))

        self.keys = {"Up": False, "Down": False, "Left": False, "Right": False}

        self.ui = turtle.Turtle(visible=False)
        self.ui.penup()
        self.ui.speed(0)

        self.bg = turtle.Turtle(visible=False)
        self.bg.penup()
        self.bg.speed(0)

        self.player = turtle.Turtle()
        self.player.hideturtle()
        self.player.penup()
        self.player.speed(0)
        self.apply_skin()

        self.obstacles = []
        self.click_areas = []

        self.screen.onclick(self.on_click)
        for k in self.keys:
            self.screen.onkeypress(self._make_press(k), k)
            self.screen.onkeyrelease(self._make_release(k), k)
        self.screen.onkey(self.escape_to_home, "Escape")
        self.screen.listen()

        self.show_home()
        self.screen.ontimer(self.tick, TICK_MS)

    # ---------- input ----------
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

    # ---------- ui primitives ----------
    def clear_ui(self):
        self.ui.clear()
        self.bg.clear()
        self.click_areas = []

    def draw_rect(self, x, y, w, h, color):
        self.bg.penup()
        self.bg.goto(x - w / 2, y - h / 2)
        self.bg.pencolor(color)
        self.bg.fillcolor(color)
        self.bg.begin_fill()
        self.bg.setheading(0)
        self.bg.pendown()
        for _ in range(2):
            self.bg.forward(w)
            self.bg.left(90)
            self.bg.forward(h)
            self.bg.left(90)
        self.bg.end_fill()
        self.bg.penup()

    def write_text(self, x, y, text, size=14, color="white", bold=False):
        self.ui.penup()
        self.ui.goto(x, y)
        self.ui.pencolor(color)
        style = "bold" if bold else "normal"
        self.ui.write(text, align="center", font=("Arial", size, style))

    def draw_button(self, x, y, w, h, label, callback, bg="#3498db", fg="white", size=14):
        self.draw_rect(x, y, w, h, bg)
        self.write_text(x, y - size + 2, label, size=size, color=fg, bold=True)
        self.click_areas.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2, callback))

    # ---------- skins ----------
    def apply_skin(self):
        skin = find_skin(self.save["current"])
        self.player.shape(skin["shape"])
        self.player.color(skin["color"])
        self.player.shapesize(1.4, 1.4)

    # ---------- screens ----------
    def show_home(self):
        self.state = "HOME"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()

        self.draw_rect(0, 0, WIDTH, HEIGHT, "#0f1626")
        self.draw_rect(0, 220, 520, 80, "#1f2a44")

        self.write_text(0, 200, "TURTLE OBBY", size=38, color="#f1c40f", bold=True)
        self.write_text(0, 145, "50 levels of obstacle madness", size=13, color="#bdc3c7")

        self.write_text(0, 90, f"Coins: {self.save['coins']}", size=20, color="#f1c40f", bold=True)
        self.write_text(0, 60, f"Highest level reached: {self.save['highest_level']}", size=13, color="#95a5a6")

        self.draw_button(0, 0, 240, 60, "START GAME", self.start_game, bg="#27ae60")
        self.draw_button(0, -80, 240, 60, "SHOP", self.show_shop, bg="#9b59b6")

        self.write_text(0, -180, "Arrow keys to move. Reach the green line.", size=11, color="#7f8c8d")
        self.write_text(0, -210, "Press Esc during a level to return here.", size=11, color="#7f8c8d")

    def show_shop(self):
        self.state = "SHOP"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()

        self.write_text(0, 260, "SHOP", size=30, color="#f1c40f", bold=True)
        self.write_text(0, 228, f"Coins: {self.save['coins']}", size=15, color="#f1c40f")

        for i, skin in enumerate(SKINS):
            col = i % 2
            row = i // 2
            x = -180 + col * 360
            y = 180 - row * 78

            owned = skin["id"] in self.save["owned"]
            selected = skin["id"] == self.save["current"]
            affordable = self.save["coins"] >= skin["price"]

            if selected:
                label = f"{skin['name']}  [EQUIPPED]"
                cb = lambda s=skin: None
            elif owned:
                label = f"{skin['name']}  [EQUIP]"
                cb = lambda s=skin: self.equip(s)
            elif affordable:
                label = f"{skin['name']}  -  BUY {skin['price']}"
                cb = lambda s=skin: self.buy(s)
            else:
                label = f"{skin['name']}  -  LOCKED ({skin['price']})"
                cb = lambda s=skin: None

            self.draw_button(x, y, 340, 60, label, cb, bg=skin["color"], fg="white", size=12)

        self.draw_button(0, -255, 200, 50, "BACK", self.show_home, bg="#34495e")

    def start_game(self):
        if self.level > MAX_LEVEL:
            self.level = MAX_LEVEL
        self.state = "GAME"
        self.clear_ui()
        self.build_level(self.level)

        self.write_text(0, HEIGHT // 2 - 32,
                        f"Level {self.level} / {MAX_LEVEL}    Coins: {self.save['coins']}",
                        size=14, color="white", bold=True)

        self.bg.penup()
        self.bg.goto(GOAL_X, -HEIGHT // 2 + 40)
        self.bg.pencolor("#2ecc71")
        self.bg.pensize(5)
        self.bg.pendown()
        self.bg.goto(GOAL_X, HEIGHT // 2 - 60)
        self.bg.penup()
        self.bg.pensize(1)

        self.player.goto(PLAYER_START_X, 0)
        self.player.showturtle()

    def show_level_complete(self):
        self.state = "WIN"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()

        self.write_text(0, 100, f"LEVEL {self.level} COMPLETE!", size=28, color="#2ecc71", bold=True)
        self.write_text(0, 60, "+10 coins", size=20, color="#f1c40f", bold=True)
        self.write_text(0, 30, f"Total coins: {self.save['coins']}", size=14, color="white")

        next_level = min(self.level + 1, MAX_LEVEL)
        self.level = next_level
        self.draw_button(0, -30, 260, 55, f"NEXT LEVEL ({next_level})", self.start_game, bg="#27ae60")
        self.draw_button(0, -100, 260, 50, "HOME", self.show_home, bg="#34495e")
        self.draw_button(0, -160, 260, 45, "SHOP", self.show_shop, bg="#9b59b6")

    def show_game_over(self):
        self.state = "LOSE"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()

        self.write_text(0, 90, "OOPS!", size=42, color="#e74c3c", bold=True)
        self.write_text(0, 40, "You hit an obstacle.", size=16, color="white")

        self.draw_button(0, -30, 240, 55, "TRY AGAIN", self.start_game, bg="#e74c3c")
        self.draw_button(0, -100, 240, 50, "HOME", self.show_home, bg="#34495e")

    def show_final_victory(self):
        self.state = "FINAL"
        self.clear_obstacles()
        self.clear_ui()
        self.player.hideturtle()

        self.write_text(0, 120, "CHAMPION!", size=46, color="#f1c40f", bold=True)
        self.write_text(0, 70, "You completed all 50 levels!", size=18, color="white")
        self.write_text(0, 40, f"Total coins: {self.save['coins']}", size=15, color="#f1c40f")

        self.draw_button(0, -20, 240, 55, "HOME", self.show_home, bg="#27ae60")
        self.draw_button(0, -90, 240, 50, "SHOP", self.show_shop, bg="#9b59b6")

    # ---------- shop actions ----------
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

    # ---------- levels ----------
    def clear_obstacles(self):
        for o in self.obstacles:
            o["t"].hideturtle()
        self.obstacles = []

    def build_level(self, n):
        self.clear_obstacles()
        random.seed(n * 1237 + 11)

        count = min(2 + n // 2, 22)
        speed = 1.6 + n * 0.18

        lane_min = -WIDTH // 2 + 110
        lane_max = GOAL_X - 30

        for i in range(count):
            x = lane_min + (lane_max - lane_min) * (i + 1) / (count + 1)
            ob = turtle.Turtle()
            ob.shape("square")
            ob.shapesize(stretch_wid=1.6, stretch_len=1.6)
            ob.color("#e74c3c")
            ob.penup()
            ob.speed(0)

            top = random.randint(60, HEIGHT // 2 - 60)
            bottom = -random.randint(60, HEIGHT // 2 - 60)
            y0 = random.randint(bottom, top)
            ob.goto(x, y0)
            dy = speed * random.choice([-1, 1])
            self.obstacles.append({"t": ob, "dy": dy, "top": top, "bottom": bottom})

    # ---------- game loop ----------
    def tick(self):
        if self.state == "GAME":
            self.update_game()
        self.screen.update()
        self.screen.ontimer(self.tick, TICK_MS)

    def update_game(self):
        px, py = self.player.position()
        if self.keys["Up"]:
            py += MOVE_SPEED
        if self.keys["Down"]:
            py -= MOVE_SPEED
        if self.keys["Left"]:
            px -= MOVE_SPEED
        if self.keys["Right"]:
            px += MOVE_SPEED

        px = max(-WIDTH // 2 + 20, min(WIDTH // 2 - 20, px))
        py = max(-HEIGHT // 2 + 20, min(HEIGHT // 2 - 80, py))
        self.player.goto(px, py)

        hit_radius = PLAYER_RADIUS + OBSTACLE_RADIUS

        for o in self.obstacles:
            t = o["t"]
            x, y = t.position()
            y += o["dy"]
            if y > o["top"]:
                y = o["top"]
                o["dy"] = -abs(o["dy"])
            elif y < o["bottom"]:
                y = o["bottom"]
                o["dy"] = abs(o["dy"])
            t.goto(x, y)

            if abs(px - x) < hit_radius and abs(py - y) < hit_radius:
                self.show_game_over()
                return

        if px >= GOAL_X:
            self.win_level()

    def win_level(self):
        self.save["coins"] += 10
        if self.level >= self.save["highest_level"]:
            self.save["highest_level"] = min(MAX_LEVEL, self.level + 1)
        save_data(self.save)

        if self.level >= MAX_LEVEL:
            self.show_final_victory()
        else:
            self.show_level_complete()


def main():
    Game()
    turtle.mainloop()


if __name__ == "__main__":
    main()
