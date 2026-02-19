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
        self.human_score = 0
        self.cpu_score = 0

        self.init_ui()
        self.new_game()

    # ---------------- UI ----------------
    def init_ui(self):
        self.setWindowTitle("Map Coloring Game – DAA Project")
        self.showMaximized()

        self.setStyleSheet("""
            QWidget {
                background-color: #7fb3c9;
            }
        """)

        self.main = QVBoxLayout(self)
        self.main.setContentsMargins(20, 15, 20, 15)
        self.main.setSpacing(14)

        # HEADER
        header = QWidget()
        header.setStyleSheet("background:#2C3E50;border-radius:18px;padding:25px;")
        hl = QVBoxLayout(header)

        title = QLabel("Map Coloring Game")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:36px;font-weight:800;color:white;")
        hl.addWidget(title)

        self.main.addWidget(header)

        # CONTROLS
        controls = QHBoxLayout()

        self.type_dropdown = QComboBox()
        self.type_dropdown.addItem("Easy (5x5)", 5)
        self.type_dropdown.addItem("Normal (6x6)", 6)
        self.type_dropdown.addItem("Hard (7x7)", 7)
        self.type_dropdown.setFixedHeight(40)
        self.type_dropdown.setStyleSheet("""
            QComboBox {
                background:#34495E;
                color:white;
                border-radius:10px;
                padding:6px;
            }
        """)
        self.type_dropdown.currentIndexChanged.connect(self.change_type)
        controls.addWidget(self.type_dropdown)

        for text, fn in [
            ("New Game", self.new_game),
            ("Restart", self.restart_game),
            ("Solve", self.solve_all)
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background:#34495E;
                    color:white;
                    border-radius:10px;
                    padding:10px 22px;
                }
                QPushButton:hover {
                    background:#2C3E50;
                }
            """)
            btn.clicked.connect(fn)
            controls.addWidget(btn)

        self.main.addLayout(controls)

        # SCORE
        self.score_label = QLabel("Human: 0    Computer: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size:16px;font-weight:bold;color:#2C3E50;")
        self.main.addWidget(self.score_label)

        # STATUS
        self.status = QLabel("Select a color and click a region")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color:white;font-weight:bold;")
        self.main.addWidget(self.status)

        # GRID
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("""
            background:white;
            border-radius:15px;
            padding:10px;
        """)
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(6)

        self.main.addStretch()
        self.main.addWidget(self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main.addStretch()

        # COLOR BUTTONS
        color_bar = QHBoxLayout()
        for c in COLORS:
            btn = QPushButton(c.upper())
            btn.setFixedSize(150, 55)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{c};
                    color:white;
                    border-radius:18px;
                    font-weight:bold;
                }}
            """)
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
        self.colors.clear()
        self.buttons.clear()
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None
        self.update_score()
        self.build_graph()

        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.colors[cell] = None

                btn = QPushButton("")
                btn.setFixedSize(70, 70)
                btn.setStyleSheet("""
                    QPushButton {
                        background:#F5F5F5;
                        border:2px solid #B0BEC5;
                        border-radius:12px;
                    }
                    QPushButton:hover {
                        border:2px solid #2C3E50;
                    }
                """)
                btn.clicked.connect(lambda _, cell=cell: self.human_move(cell))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        # Prefill safe cells
        cells = list(self.colors.keys())
        random.shuffle(cells)
        for cell in cells[:self.size]:
            for col in COLORS:
                if self.valid(cell, col):
                    self.colors[cell] = col
                    self.paint(cell)
                    break

        self.initial_colors = self.colors.copy()
        self.status.setText("New game started")

    # ---------------- FIXED RESTART ----------------
    def restart_game(self):
        self.colors = self.initial_colors.copy()
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None
        self.update_score()
        self.status.setText("Game restarted")

        for cell in self.colors:
            if self.colors[cell] is None:
                self.buttons[cell].setStyleSheet("""
                    QPushButton {
                        background:#F5F5F5;
                        border:2px solid #B0BEC5;
                        border-radius:12px;
                    }
                """)
            else:
                self.paint(cell)

    # ---------------- HELPERS ----------------
    def update_score(self):
        self.score_label.setText(
            f"Human: {self.human_score}    Computer: {self.cpu_score}"
        )

    def select_color(self, color):
        self.selected_color = color
        self.status.setText(f"Selected color: {color.upper()}")

    def valid(self, cell, color):
        return all(self.colors[n] != color for n in self.graph[cell])

    def paint(self, cell):
        self.buttons[cell].setStyleSheet(f"""
            QPushButton {{
                background:{self.colors[cell]};
                border:2px solid #2C3E50;
                border-radius:12px;
            }}
        """)

    def check_game_over(self):
        if all(self.colors[cell] is not None for cell in self.colors):
            self.show_winner()

    # ---------------- HUMAN ----------------
    def human_move(self, cell):
        if not self.selected_color or self.colors[cell] is not None:
            return

        if not self.valid(cell, self.selected_color):
            self.human_score -= 1
            self.update_score()
            return

        self.colors[cell] = self.selected_color
        self.paint(cell)
        self.human_score += 1
        self.update_score()

        self.check_game_over()
        QTimer.singleShot(400, self.cpu_move)

    # ---------------- SAFE CPU ----------------
    def cpu_move(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return

        sorted_cells = sorted(
            uncolored,
            key=lambda cell: len(self.graph[cell]),
            reverse=True
        )

        move_made = False

        for cell in sorted_cells:
            for col in COLORS:
                if self.valid(cell, col):
                    self.colors[cell] = col
                    self.paint(cell)
                    self.cpu_score += 1
                    self.update_score()
                    move_made = True
                    break
            if move_made:
                break

        if not move_made:
            self.show_fail_popup()
            return

        self.check_game_over()

    # ---------------- FAIL POPUP ----------------
    def show_fail_popup(self):
        popup = QDialog(self)
        popup.setWindowTitle("Game Over")
        popup.setFixedSize(350, 200)

        layout = QVBoxLayout(popup)
        msg = QLabel("Dead-end reached!\nNo valid moves left.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("Play Again")
        btn.clicked.connect(lambda: [popup.close(), self.new_game()])

        layout.addWidget(msg)
        layout.addWidget(btn)

        popup.exec()

    # ---------------- WINNER POPUP ----------------
    def show_winner(self):
        if self.human_score > self.cpu_score:
            result = "HUMAN WINS!"
        elif self.cpu_score > self.human_score:
            result = "COMPUTER WINS!"
        else:
            result = "DRAW!"

        popup = QDialog(self)
        popup.setWindowTitle("Game Result")
        popup.setFixedSize(350, 200)

        layout = QVBoxLayout(popup)
        msg = QLabel(result)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        score = QLabel(
            f"Human: {self.human_score}\nComputer: {self.cpu_score}"
        )
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("Play Again")
        btn.clicked.connect(lambda: [popup.close(), self.new_game()])

        layout.addWidget(msg)
        layout.addWidget(score)
        layout.addWidget(btn)

        popup.exec()

    # ---------------- SOLVER ----------------
    def solve_all(self):
        self.divide_and_conquer()
        for cell in self.colors:
            if self.colors[cell]:
                self.paint(cell)
        self.check_game_over()

    def divide_and_conquer(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return True

        sorted_cells = sorted(
            uncolored,
            key=lambda cell: len(self.graph[cell]),
            reverse=True
        )

        current = sorted_cells[0]

        for col in COLORS:
            if self.valid(current, col):
                self.colors[current] = col
                if self.divide_and_conquer():
                    return True
                self.colors[current] = None

        return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
