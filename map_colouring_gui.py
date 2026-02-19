import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QGridLayout, QVBoxLayout, QHBoxLayout,
    QComboBox, QDialog
)
from PyQt6.QtCore import Qt, QTimer

COLORS = ["red", "green", "blue", "yellow"]

class MapColoringGame(QWidget):
    def __init__(self):
        super().__init__()

        self.size = 5
        self.graph = {}
        self.colors = {}
        self.initial_colors = {}
        self.buttons = {}

        self.selected_color = None
        self.solving = False

        self.human_score = 0
        self.cpu_score = 0

        self.memo = {}   # DP memoization storage

        self.init_ui()
        self.new_game()

    # ---------------- UI (UNCHANGED) ----------------
    def init_ui(self):
        self.setWindowTitle("Map Coloring Game – DAA Project")
        self.showMaximized()

        self.setStyleSheet("""
            QWidget {
                background-color: #87CEEB;
                background-image:
                    radial-gradient(circle at 20% 30%, #FFD700 1px, transparent 2px),
                    radial-gradient(circle at 70% 60%, #FFD700 1px, transparent 2px);
            }
        """)

        self.main = QVBoxLayout(self)
        self.main.setContentsMargins(20, 15, 20, 15)
        self.main.setSpacing(14)

        header = QWidget()
        header.setStyleSheet("background:#1E3A5F;border-radius:18px;padding:22px;")
        hl = QVBoxLayout(header)

        title = QLabel("Map Coloring Game")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:36px;font-weight:800;color:white;")
        hl.addWidget(title)
        self.main.addWidget(header)

        controls = QHBoxLayout()

        self.type_dropdown = QComboBox()
        self.type_dropdown.addItem("Easy (5x5)", 5)
        self.type_dropdown.addItem("Normal (6x6)", 6)
        self.type_dropdown.addItem("Hard (7x7)", 7)
        self.type_dropdown.setFixedHeight(40)
        self.type_dropdown.setStyleSheet(
            "QComboBox{background:#2C3E50;color:white;border-radius:8px;padding:6px;}"
        )
        self.type_dropdown.currentIndexChanged.connect(self.change_type)
        controls.addWidget(self.type_dropdown)

        for text, fn in [
            ("New Game", self.new_game),
            ("Restart", self.restart_game),
            ("Solve", self.solve_all)
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(40)
            btn.setStyleSheet(
                "QPushButton{background:#2C3E50;color:white;border-radius:8px;padding:10px 22px;}"
            )
            btn.clicked.connect(fn)
            controls.addWidget(btn)

        self.main.addLayout(controls)

        self.score_label = QLabel("Human: 0    Computer: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.addWidget(self.score_label)

        self.status = QLabel("Select a color and click a region")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.addWidget(self.status)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)

        self.main.addWidget(self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter)

        color_bar = QHBoxLayout()
        for c in COLORS:
            btn = QPushButton(c.upper())
            btn.setFixedSize(120, 45)
            btn.setStyleSheet(
                f"background:{c};color:white;border-radius:14px;font-weight:bold;"
            )
            btn.clicked.connect(lambda _, col=c: self.select_color(col))
            color_bar.addWidget(btn)
        self.main.addLayout(color_bar)

    # ---------------- GRAPH ----------------
    def build_graph(self):
        self.graph.clear()
        for r in range(self.size):
            for c in range(self.size):
                self.graph[(r, c)] = []
                for dr, dc in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.size and 0 <= nc < self.size:
                        self.graph[(r, c)].append((nr, nc))

    # ---------------- GAME SETUP ----------------
    def change_type(self):
        self.size = self.type_dropdown.currentData()
        self.new_game()

    def new_game(self):
        self.memo.clear()
        self.colors.clear()
        self.buttons.clear()
        self.build_graph()

        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.colors[cell] = None
                btn = QPushButton("")
                btn.setFixedSize(60, 60)
                btn.setStyleSheet("background:#F5F5F5;border:1px solid #B0BEC5;")
                btn.clicked.connect(lambda _, cell=cell: self.human_move(cell))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        self.initial_colors = self.colors.copy()

    # ---------------- HELPERS ----------------
    def select_color(self, color):
        self.selected_color = color

    def valid(self, cell, color):
        return all(self.colors[n] != color for n in self.graph[cell])

    def paint(self, cell):
        self.buttons[cell].setStyleSheet(
            f"background:{self.colors[cell]};border:1px solid #455A64;"
        )

    # ---------------- HUMAN MOVE ----------------
    def human_move(self, cell):
        if not self.selected_color or self.colors[cell] is not None:
            return
        if not self.valid(cell, self.selected_color):
            return

        self.colors[cell] = self.selected_color
        self.paint(cell)

        QTimer.singleShot(400, self.cpu_move)

    # ---------------- DC + DP SOLVER ----------------
    def dc_dp_solve(self):
        state = tuple(sorted(self.colors.items()))

        if state in self.memo:
            return False

        uncolored = [c for c in self.colors if self.colors[c] is None]

        if not uncolored:
            return True

        cell = uncolored[0]

        for col in COLORS:
            if self.valid(cell, col):
                self.colors[cell] = col
                if self.dc_dp_solve():
                    return True
                self.colors[cell] = None

        self.memo[state] = False
        return False

    # ---------------- CPU MOVE (DC + DP) ----------------
    def cpu_move(self):
        self.memo.clear()

        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return

        cell = uncolored[0]

        for col in COLORS:
            if self.valid(cell, col):
                self.colors[cell] = col
                if self.dc_dp_solve():
                    self.paint(cell)
                    return
                self.colors[cell] = None

    # ---------------- SOLVE ALL ----------------
    def solve_all(self):
        self.memo.clear()
        if self.dc_dp_solve():
            for cell in self.colors:
                if self.colors[cell]:
                    self.paint(cell)

# RUN
if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
