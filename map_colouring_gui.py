import sys
import random
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QGridLayout, QVBoxLayout, QHBoxLayout,
    QComboBox, QDialog, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]
COLOR_NAMES = ["Red", "Green", "Blue", "Yellow"]

class MapColoringGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Map Coloring Game – DAA Project")
        self.resize(1100, 900)

        self.size = 5
        self.graph = {}
        self.colors = {}
        self.initial_colors = {}
        self.buttons = {}
        self.selected_color = None
        self.human_score = 0
        self.cpu_score = 0

        self.init_ui()
        self.apply_theme()
        self.new_game()

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                            stop:0 #0f172a, stop:1 #1e293b);
                color: #e2e8f0;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QFrame#card {
                background: rgba(30, 41, 59, 180);
                border: 1px solid rgba(148, 163, 184, 100);
                border-radius: 16px;
            }
            QPushButton {
                background: #6366f1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
                font-size: 15px;
            }
            QPushButton:hover {
                background: #4f46e5;
            }
            QPushButton#color-btn {
                font-size: 16px;
                font-weight: bold;
                min-width: 110px;
                min-height: 54px;
                border-radius: 12px;
            }
            QPushButton#cell {
                background: #1e293b;
                border: 2px solid #475569;
                border-radius: 10px;
            }
            QPushButton#cell:hover {
                border: 3px solid #818cf8;
                background: #334155;
            }
            QLabel {
                color: #e2e8f0;
            }
            QComboBox {
                background: #1e293b;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px;
                font-size: 15px;
            }
        """)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(30, 20, 30, 30)
        self.main_layout.setSpacing(20)

        # Header row with title + status
        header = QHBoxLayout()
        title = QLabel("Map Coloring Game")
        title.setStyleSheet("font-size: 36px; font-weight: 800;")
        header.addWidget(title)
        header.addStretch()

        self.status = QLabel("Select a color → click a region")
        self.status.setStyleSheet("font-size: 17px; color: #94a3b8;")
        header.addWidget(self.status)

        self.main_layout.addLayout(header)

        # Controls row
        controls = QHBoxLayout()
        controls.setSpacing(15)

        lbl = QLabel("Difficulty:")
        lbl.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItem("Easy (5×5)", 5)
        self.type_dropdown.addItem("Normal (6×6)", 6)
        self.type_dropdown.addItem("Hard (7×7)", 7)
        self.type_dropdown.currentIndexChanged.connect(self.change_type)

        controls.addWidget(lbl)
        controls.addWidget(self.type_dropdown)
        controls.addStretch()

        for text, func in [
            ("New Game", self.new_game),
            ("Restart", self.restart_game),
            ("Solve", self.solve_all)
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(46)
            btn.clicked.connect(func)
            controls.addWidget(btn)

        self.main_layout.addLayout(controls)

        # Score panel
        score_frame = QFrame()
        score_frame.setObjectName("card")
        score_layout = QHBoxLayout(score_frame)
        score_layout.setContentsMargins(25, 15, 25, 15)

        self.score_label = QLabel("Human: 0   •   Computer: 0")
        self.score_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_layout.addWidget(self.score_label)

        self.main_layout.addWidget(score_frame)

        # ── This is the key part for centering the grid ───────────────────────
        # Center container with stretches on all sides
        center_container = QVBoxLayout()
        center_container.addStretch(1)  # push down

        grid_and_palette = QVBoxLayout()
        grid_and_palette.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grid_frame = QFrame()
        self.grid_frame.setObjectName("card")
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)

        grid_and_palette.addWidget(self.grid_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Color buttons (palette)
        palette_layout = QHBoxLayout()
        palette_layout.setSpacing(14)
        palette_layout.addStretch()

        for col, name in zip(COLORS, COLOR_NAMES):
            btn = QPushButton(name)
            btn.setObjectName("color-btn")
            btn.setStyleSheet(f"""
                background: {col};
                color: {'black' if col == COLORS[3] else 'white'};
            """)
            btn.clicked.connect(lambda _, c=col: self.select_color(c))
            palette_layout.addWidget(btn)

        palette_layout.addStretch()
        grid_and_palette.addLayout(palette_layout)

        center_container.addLayout(grid_and_palette)
        center_container.addStretch(1)  # push up

        self.main_layout.addLayout(center_container, stretch=1)

    # ───────────────────────────────────────────────────────────────
    #  The rest of your game logic remains unchanged
    # ───────────────────────────────────────────────────────────────

    def build_graph(self):
        self.graph.clear()
        for r in range(self.size):
            for c in range(self.size):
                self.graph[(r, c)] = []
                for dr, dc in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.size and 0 <= nc < self.size:
                        self.graph[(r, c)].append((nr, nc))

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
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        screen = QApplication.primaryScreen().availableGeometry()
        side = min(screen.width() - 600, screen.height() - 500)
        cell_size = max(60, side // self.size)

        self.grid_frame.setFixedSize(
            self.size * (cell_size + 6) + 24,
            self.size * (cell_size + 6) + 24
        )

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.colors[cell] = None
                btn = QPushButton("")
                btn.setObjectName("cell")
                btn.setFixedSize(cell_size, cell_size)
                btn.clicked.connect(lambda _, pos=cell: self.human_move(pos))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        # Prefill
        cells = list(self.colors.keys())
        random.shuffle(cells)
        for cell in cells[:self.size]:
            for col in COLORS:
                if self.valid(cell, col):
                    self.colors[cell] = col
                    self.paint(cell)
                    break

        self.initial_colors = self.colors.copy()
        self.status.setText("New game started • Your turn")

    def restart_game(self):
        self.colors = self.initial_colors.copy()
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None
        self.update_score()
        self.status.setText("Game restarted • Your turn")

        for cell in self.colors:
            if self.colors[cell] is None:
                self.buttons[cell].setStyleSheet("")
            else:
                self.paint(cell)

    def update_score(self):
        self.score_label.setText(f"Human: {self.human_score}   •   Computer: {self.cpu_score}")

    def select_color(self, color):
        self.selected_color = color
        self.status.setText(f"Selected → {color.upper()}")

    def valid(self, cell, color):
        return all(self.colors.get(n) != color for n in self.graph[cell] if self.colors.get(n) is not None)

    def paint(self, cell):
        col = self.colors[cell]
        self.buttons[cell].setStyleSheet(f"background:{col}; border:2px solid #334155;")

    def check_game_over(self):
        if all(self.colors.get(cell) is not None for cell in self.colors):
            self.show_winner()

    def human_move(self, cell):
        if not self.selected_color or self.colors.get(cell) is not None:
            return

        if not self.valid(cell, self.selected_color):
            self.human_score = max(0, self.human_score - 1)
            self.update_score()
            self.status.setText("❌ Invalid! -1 point")
            QTimer.singleShot(1400, lambda: self.status.setText("Your turn"))
            return

        self.colors[cell] = self.selected_color
        self.paint(cell)
        self.human_score += 1
        self.update_score()
        self.check_game_over()

        if all(v is not None for v in self.colors.values()):
            return

        QTimer.singleShot(400, self.cpu_move)

    def cpu_move(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return

        sorted_cells = sorted(uncolored, key=lambda c: len(self.graph[c]), reverse=True)

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

    def show_fail_popup(self):
        popup = QDialog(self)
        popup.setWindowTitle("Stuck")
        popup.setFixedSize(380, 220)
        lay = QVBoxLayout(popup)
        lay.setContentsMargins(30, 30, 30, 30)

        msg = QLabel("Dead-end reached!\nNo valid moves left.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(msg)

        btn = QPushButton("New Game")
        btn.clicked.connect(lambda: [popup.accept(), self.new_game()])
        lay.addWidget(btn)

        popup.exec()

    def show_winner(self):
        if self.human_score > self.cpu_score:
            result = "HUMAN WINS! 🎉"
            color = "#22c55e"
        elif self.cpu_score > self.human_score:
            result = "COMPUTER WINS"
            color = "#ef4444"
        else:
            result = "DRAW"
            color = "#3b82f6"

        popup = QDialog(self)
        popup.setWindowTitle("Result")
        popup.setFixedSize(380, 260)
        lay = QVBoxLayout(popup)
        lay.setContentsMargins(30, 30, 30, 30)

        t = QLabel(result)
        t.setStyleSheet(f"font-size:32px; font-weight:800; color:{color};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        s = QLabel(f"Human: {self.human_score}\nComputer: {self.cpu_score}")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(s)

        btn = QPushButton("Play Again")
        btn.clicked.connect(lambda: [popup.accept(), self.new_game()])
        lay.addWidget(btn)

        popup.exec()

    def solve_all(self):
        self.status.setText("Solving with backtracking...")
        success = self.divide_and_conquer()

        if success:
            for cell in self.colors:
                if self.colors[cell]:
                    self.paint(cell)
            self.status.setText("Solved!")
        else:
            self.status.setText("No solution found")

        self.check_game_over()

    def divide_and_conquer(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            return True

        sorted_cells = sorted(uncolored, key=lambda c: len(self.graph[c]), reverse=True)
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
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 11)
    app.setFont(font)

    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
