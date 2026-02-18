import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QGridLayout, QVBoxLayout, QHBoxLayout,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt

COLORS = ["red", "green", "blue", "yellow"]


class MapColoringGame(QWidget):
    def __init__(self):
        super().__init__()

        self.size = 5
        self.graph = {}
        self.colors = {}
        self.buttons = {}
        self.move_history = []

        self.selected_color = None
        self.human_score = 0
        self.cpu_score = 0

        self.init_ui()
        self.new_game()

    # ---------------- UI ---------------- #

    def init_ui(self):
        self.setWindowTitle("Map Coloring Game – Review 2")
        self.resize(1100, 850)

        self.setStyleSheet("""
            QWidget { background-color: #87CEEB; }
        """)

        main = QVBoxLayout(self)

        title = QLabel("MAP COLORING GAME")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size:32px;
            font-weight:bold;
            color:#1E3A5F;
        """)
        main.addWidget(title)

        # Controls Row
        control_row = QHBoxLayout()

        self.level_box = QComboBox()
        self.level_box.addItem("Easy (5x5)", 5)
        self.level_box.addItem("Normal (6x6)", 6)
        self.level_box.addItem("Hard (7x7)", 7)
        self.level_box.currentIndexChanged.connect(self.change_level)

        control_row.addWidget(self.level_box)

        for text, func in [
            ("New Game", self.new_game),
            ("Restart", self.restart_game),
            ("Undo", self.undo_move)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            btn.setFixedHeight(35)
            control_row.addWidget(btn)

        main.addLayout(control_row)

        # Info Row
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size:15px; font-weight:600; color:#1E3A5F;")
        main.addWidget(self.info_label)

        # Grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(5)
        main.addWidget(self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Color Buttons
        color_row = QHBoxLayout()
        for color in COLORS:
            btn = QPushButton(color.upper())
            btn.setStyleSheet(f"""
                background:{color};
                color:white;
                font-weight:bold;
                border-radius:8px;
                padding:10px;
            """)
            btn.clicked.connect(lambda _, c=color: self.select_color(c))
            color_row.addWidget(btn)

        main.addLayout(color_row)

    # ---------------- Graph ---------------- #

    def build_graph(self):
        self.graph.clear()
        for r in range(self.size):
            for c in range(self.size):
                self.graph[(r, c)] = []
                for dr, dc in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.size and 0 <= nc < self.size:
                        self.graph[(r, c)].append((nr, nc))

    # ---------------- Game Setup ---------------- #

    def change_level(self):
        self.size = self.level_box.currentData()
        self.new_game()

    def new_game(self):
        self.colors.clear()
        self.buttons.clear()
        self.move_history.clear()
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None

        self.build_graph()

        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        cell_size = 70 if self.size == 5 else 60 if self.size == 6 else 50

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.colors[cell] = None
                btn = QPushButton()
                btn.setFixedSize(cell_size, cell_size)
                btn.setStyleSheet("background:white; border:1px solid gray;")
                btn.clicked.connect(lambda _, cell=cell: self.human_move(cell))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        # Safe Prefill (important!)
        cells = list(self.colors.keys())
        random.shuffle(cells)
        for cell in cells[:self.size]:
            for col in COLORS:
                if self.valid(cell, col):
                    self.colors[cell] = col
                    self.paint(cell)
                    break

        self.update_info()

    def restart_game(self):
        self.new_game()

    # ---------------- Helpers ---------------- #

    def update_info(self):
        remaining = sum(1 for c in self.colors.values() if c is None)
        self.info_label.setText(
            f"Human: {self.human_score}    "
            f"Computer: {self.cpu_score}    "
            f"Remaining: {remaining}"
        )

    def select_color(self, color):
        self.selected_color = color
        self.info_label.setText(
            f"Human: {self.human_score}    "
            f"Computer: {self.cpu_score}    "
            f"Remaining: {sum(1 for c in self.colors.values() if c is None)}    "
            f"Selected: {color.upper()}"
        )

    def valid(self, cell, color):
        return all(self.colors[n] != color for n in self.graph[cell])

    def paint(self, cell):
        self.buttons[cell].setStyleSheet(
            f"background:{self.colors[cell]}; border:1px solid black;"
        )

    # ---------------- Sorting ---------------- #

    def selection_sort_by_degree(self, nodes):
        nodes = nodes[:]
        for i in range(len(nodes)):
            max_i = i
            for j in range(i+1, len(nodes)):
                if len(self.graph[nodes[j]]) > len(self.graph[nodes[max_i]]):
                    max_i = j
            nodes[i], nodes[max_i] = nodes[max_i], nodes[i]
        return nodes

    # ---------------- Divide & Conquer ---------------- #

    def dc_select(self, nodes):
        if len(nodes) == 1:
            return nodes[0]

        mid = len(nodes)//2
        left = self.dc_select(nodes[:mid])
        right = self.dc_select(nodes[mid:])

        if len(self.graph[left]) >= len(self.graph[right]):
            return left
        else:
            return right

    # ---------------- Moves ---------------- #

    def human_move(self, cell):
        if not self.selected_color:
            return
        if self.colors[cell] is not None:
            return
        if not self.valid(cell, self.selected_color):
            return

        self.colors[cell] = self.selected_color
        self.paint(cell)
        self.human_score += 1
        self.move_history.append(("H", cell))

        self.update_info()
        self.check_game_over()

        self.cpu_move()

    def cpu_move(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return

        sorted_nodes = self.selection_sort_by_degree(uncolored)
        best_cell = self.dc_select(sorted_nodes)

        valid_colors = [c for c in COLORS if self.valid(best_cell, c)]
        if valid_colors:
            chosen_color = random.choice(valid_colors[:2])
            self.colors[best_cell] = chosen_color
            self.paint(best_cell)
            self.cpu_score += 1
            self.move_history.append(("C", best_cell))

        self.update_info()
        self.check_game_over()

    # ---------------- Undo ---------------- #

    def undo_move(self):
        if not self.move_history:
            return

        player, cell = self.move_history.pop()
        self.colors[cell] = None
        self.buttons[cell].setStyleSheet("background:white; border:1px solid gray;")

        if player == "H":
            self.human_score -= 1
        else:
            self.cpu_score -= 1

        self.update_info()

    # ---------------- Game Over ---------------- #

    def check_game_over(self):
        if all(c is not None for c in self.colors.values()):
            if self.human_score > self.cpu_score:
                msg = "HUMAN WINS!"
            elif self.cpu_score > self.human_score:
                msg = "COMPUTER WINS!"
            else:
                msg = "DRAW!"

            QMessageBox.information(
                self,
                "Game Over",
                f"{msg}\n\nHuman: {self.human_score}\nComputer: {self.cpu_score}"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
