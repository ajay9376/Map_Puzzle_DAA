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
        self.setWindowTitle("Map Coloring Game – Advanced Divide & Conquer")
        self.resize(1100, 900)

        self.size = 5
        self.graph = {}
        self.cell_colors = {}
        self.initial_colors = {}
        self.buttons = {}
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None

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
                min-width: 110px;
                min-height: 54px;
                border-radius: 12px;
                font-size: 15px;
                font-weight: bold;
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
        main = QVBoxLayout(self)
        main.setContentsMargins(30, 20, 30, 30)
        main.setSpacing(20)

        # Title + status
        header = QHBoxLayout()
        title = QLabel("Map Coloring Game")
        title.setStyleSheet("font-size:34px; font-weight:800;")
        header.addWidget(title)
        header.addStretch()

        self.status_label = QLabel("Select a color and click a cell")
        self.status_label.setStyleSheet("font-size:17px; color:#94a3b8;")
        header.addWidget(self.status_label)

        main.addLayout(header)

        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(15)

        lbl = QLabel("Difficulty:")
        lbl.setStyleSheet("font-size:16px; font-weight:600;")
        self.type_dropdown = QComboBox()
        self.type_dropdown.addItem("Easy (5×5)", 5)
        self.type_dropdown.addItem("Normal (6×6)", 6)
        self.type_dropdown.addItem("Hard (7×7)", 7)
        self.type_dropdown.currentIndexChanged.connect(self.change_type)

        controls.addWidget(lbl)
        controls.addWidget(self.type_dropdown)
        controls.addStretch()

        for text, fn in [
            ("New Game", self.new_game),
            ("Restart", self.restart_game),
            ("Solve (Backtracking)", self.solve_board)
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(46)
            btn.clicked.connect(fn)
            controls.addWidget(btn)

        main.addLayout(controls)

        # Score
        score_frame = QFrame()
        score_frame.setObjectName("card")
        score_lay = QHBoxLayout(score_frame)
        score_lay.setContentsMargins(25, 15, 25, 15)

        self.score_label = QLabel("Human: 0 | Computer: 0")
        self.score_label.setStyleSheet("font-size:20px; font-weight:bold;")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_lay.addWidget(self.score_label)

        main.addWidget(score_frame)

        # Center container → grid + color bar
        center_container = QVBoxLayout()
        center_container.addStretch(1)

        grid_section = QVBoxLayout()
        grid_section.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.grid_frame = QFrame()
        self.grid_frame.setObjectName("card")
        self.grid_layout = QGridLayout(self.grid_frame)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)

        grid_section.addWidget(self.grid_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Color buttons with text
        color_bar = QHBoxLayout()
        color_bar.setSpacing(14)
        color_bar.addStretch()

        for color, name in zip(COLORS, COLOR_NAMES):
            btn = QPushButton(name)
            btn.setObjectName("color-btn")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: {'black' if color == COLORS[3] else 'white'};
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    border: 3px solid white;
                }}
            """)
            btn.clicked.connect(lambda _, c=color: self.select_color(c))
            color_bar.addWidget(btn)

        color_bar.addStretch()
        grid_section.addLayout(color_bar)

        center_container.addLayout(grid_section)
        center_container.addStretch(1)

        main.addLayout(center_container, stretch=1)

    # GRAPH 
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

    # NEW GAME 
    def new_game(self):
        self.cell_colors.clear()
        self.buttons.clear()
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None
        self.update_score()
        self.build_graph()

        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        screen = QApplication.primaryScreen().availableGeometry()
        side = min(screen.width() - 600, screen.height() - 500)
        cell_size = max(64, side // self.size)

        self.grid_frame.setFixedSize(
            self.size * (cell_size + 6) + 24,
            self.size * (cell_size + 6) + 24
        )

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.cell_colors[cell] = None
                btn = QPushButton("")
                btn.setObjectName("cell")
                btn.setFixedSize(cell_size, cell_size)
                btn.clicked.connect(lambda _, pos=cell: self.human_move(pos))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        # DEFAULT PREFILL
        cells = list(self.cell_colors.keys())
        random.shuffle(cells)
        filled = 0
        for cell in cells:
            if filled >= self.size:
                break
            for color in COLORS:
                if self.is_valid(cell, color):
                    self.cell_colors[cell] = color
                    self.paint_cell(cell)
                    filled += 1
                    break

        self.initial_colors = self.cell_colors.copy()
        self.status_label.setText("New Game Started with Default Pattern")

    def restart_game(self):
        self.cell_colors = self.initial_colors.copy()
        self.human_score = 0
        self.cpu_score = 0
        self.update_score()

        for cell in self.cell_colors:
            if self.cell_colors[cell]:
                self.paint_cell(cell)
            else:
                self.buttons[cell].setStyleSheet("")

        self.status_label.setText("Game Restarted")

    # HELPERS 
    def update_score(self):
        self.score_label.setText(f"Human: {self.human_score} | Computer: {self.cpu_score}")

    def select_color(self, color):
        self.selected_color = color
        self.status_label.setText(f"Selected: {color.upper()}")

    def is_valid(self, cell, color):
        return all(
            self.cell_colors.get(n) != color
            for n in self.graph[cell]
            if self.cell_colors.get(n) is not None
        )

    def paint_cell(self, cell):
        self.buttons[cell].setStyleSheet(
            f"background:{self.cell_colors[cell]}; border:2px solid #334155;"
        )

    # GAME END CHECK 
    def check_complete(self):
        if all(self.cell_colors[c] is not None for c in self.cell_colors):
            self.show_winner()

    # HUMAN MOVE 
    def human_move(self, cell):
        if not self.selected_color:
            return
        if self.cell_colors.get(cell) is not None:
            return
        if not self.is_valid(cell, self.selected_color):
            self.human_score = max(0, self.human_score - 1)
            self.update_score()
            self.status_label.setText("Invalid Move (-1)")
            QTimer.singleShot(1400, lambda: self.status_label.setText("Your turn"))
            return

        self.cell_colors[cell] = self.selected_color
        self.paint_cell(cell)
        self.human_score += 1
        self.update_score()
        self.check_complete()
        QTimer.singleShot(400, self.cpu_move)

    # CPU MOVE (TRUE D&C) 
    def cpu_move(self):
        result = self.divide_and_conquer_cpu(0, 0, self.size, self.size)
        if result:
            best_cell, _ = result
            color = self.find_valid_color(best_cell)
            if color:
                self.cell_colors[best_cell] = color
                self.paint_cell(best_cell)
                self.cpu_score += 1
                self.update_score()
                self.check_complete()
        else:
            self.show_fail_popup()

    def divide_and_conquer_cpu(self, sr, sc, er, ec):
        region_size = (er - sr) * (ec - sc)
        # Base Case
        if region_size <= 4:
            best_cell = None
            best_score = -1
            for r in range(sr, er):
                for c in range(sc, ec):
                    cell = (r, c)
                    if self.cell_colors.get(cell) is None:
                        color = self.find_valid_color(cell)
                        if color:
                            score = self.evaluate_cell(cell)
                            if score > best_score:
                                best_score = score
                                best_cell = cell
            if best_cell:
                return (best_cell, best_score)
            return None

        # Divide
        mid_r = (sr + er) // 2
        mid_c = (sc + ec) // 2

        q1 = self.divide_and_conquer_cpu(sr, sc, mid_r, mid_c)
        q2 = self.divide_and_conquer_cpu(sr, mid_c, mid_r, ec)
        q3 = self.divide_and_conquer_cpu(mid_r, sc, er, mid_c)
        q4 = self.divide_and_conquer_cpu(mid_r, mid_c, er, ec)

        # Combine
        candidates = [q for q in [q1, q2, q3, q4] if q is not None]
        if not candidates:
            return None
        return max(candidates, key=lambda x: x[1])

    def evaluate_cell(self, cell):
        score = 0
        for n in self.graph[cell]:
            if self.cell_colors.get(n) is None:
                score += 1
        return score

    def find_valid_color(self, cell):
        for color in COLORS:
            if self.is_valid(cell, color):
                return color
        return None

    #SOLVER 
    def solve_board(self):
        self.status_label.setText("Solving using backtracking...")
        success = self.solve_recursive()
        if success:
            for cell in self.cell_colors:
                if self.cell_colors[cell]:
                    self.paint_cell(cell)
            self.status_label.setText("Board Solved")
        else:
            self.status_label.setText("No Solution Found")
        self.check_complete()

    def solve_recursive(self):
        uncolored = [c for c in self.cell_colors if self.cell_colors[c] is None]
        if not uncolored:
            return True
        cell = uncolored[0]
        for color in COLORS:
            if self.is_valid(cell, color):
                self.cell_colors[cell] = color
                if self.solve_recursive():
                    return True
                self.cell_colors[cell] = None
        return False

    # POPUPS
    def show_fail_popup(self):
        popup = QDialog(self)
        popup.setWindowTitle("Game Over")
        popup.setFixedSize(340, 180)
        popup.setStyleSheet("background:#0f172a; color:#e2e8f0;")

        lay = QVBoxLayout(popup)
        lay.setContentsMargins(30, 30, 30, 30)

        label = QLabel("No valid moves left!")
        label.setStyleSheet("font-size:18px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(label)

        btn = QPushButton("New Game")
        btn.setStyleSheet("background:#6366f1; font-size:16px; padding:12px;")
        btn.clicked.connect(lambda: [popup.accept(), self.new_game()])
        lay.addWidget(btn)

        popup.exec()

    def show_winner(self):
        popup = QDialog(self)
        popup.setWindowTitle("Game Result")
        popup.setFixedSize(380, 240)
        popup.setStyleSheet("background:#0f172a; color:#e2e8f0;")

        lay = QVBoxLayout(popup)
        lay.setContentsMargins(30, 30, 30, 30)

        if self.human_score > self.cpu_score:
            result = "HUMAN WINS! 🎉"
            color = "#22c55e"
        elif self.cpu_score > self.human_score:
            result = "COMPUTER WINS 🤖"
            color = "#ef4444"
        else:
            result = "DRAW!"
            color = "#3b82f6"

        label = QLabel(result)
        label.setStyleSheet(f"font-size:32px; font-weight:800; color:{color};")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(label)

        score = QLabel(f"Human: {self.human_score}\nCPU: {self.cpu_score}")
        score.setStyleSheet("font-size:18px;")
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(score)

        btn = QPushButton("Play Again")
        btn.setStyleSheet("background:#6366f1; font-size:16px; padding:12px;")
        btn.clicked.connect(lambda: [popup.accept(), self.new_game()])
        lay.addWidget(btn)

        popup.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
