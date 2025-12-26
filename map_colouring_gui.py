import sys
import random
from PyQt6.QtWidgets import ( 
    QApplication, QWidget, QPushButton, QLabel,
    QGridLayout, QVBoxLayout, QHBoxLayout,
    QComboBox
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

        self.init_ui()
        self.new_game()

    # UI 
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

        #  HEADER 
        header = QWidget()
        header.setStyleSheet("background:#1E3A5F;border-radius:18px;padding:22px;")
        hl = QVBoxLayout(header)

        title = QLabel("Map Coloring Game")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:36px;font-weight:800;color:white;")

        # CONTROLS 
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

        #  SCORE 
        self.score_label = QLabel("Human: 0    Computer: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size:15px;font-weight:600;color:#1E3A5F;")
        self.main.addWidget(self.score_label)

        #STATUS
        self.status = QLabel("Select a color and click a region")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main.addWidget(self.status)

        # GRID
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background:white;border-radius:10px;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(0)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.main.addStretch()
        self.main.addWidget(self.grid_container, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main.addStretch()

        # COLOR BUTTONS
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

    #GAME SETUP 
    def change_type(self):
        self.size = self.type_dropdown.currentData()
        self.new_game()

    def new_game(self):
        self.solving = False
        self.colors.clear()
        self.buttons.clear()
        self.human_score = 0
        self.cpu_score = 0
        self.update_score()
        self.build_graph()

        while self.grid_layout.count():
            self.grid_layout.takeAt(0).widget().deleteLater()

        screen = QApplication.primaryScreen().availableGeometry()
        self.cell_size = min(90, (screen.height() - 360) // self.size)

        self.grid_container.setFixedSize(
            self.size * self.cell_size,
            self.size * self.cell_size
        )

        for r in range(self.size):
            for c in range(self.size):
                cell = (r, c)
                self.colors[cell] = None
                btn = QPushButton("")
                btn.setFixedSize(self.cell_size, self.cell_size)
                btn.setStyleSheet("background:#F5F5F5;border:1px solid #B0BEC5;")
                btn.clicked.connect(lambda _, cell=cell: self.human_move(cell))
                self.grid_layout.addWidget(btn, r, c)
                self.buttons[cell] = btn

        # SAFE PREFILL
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

    def restart_game(self):
        self.solving = False
        self.colors = self.initial_colors.copy()
        self.human_score = 0
        self.cpu_score = 0
        self.update_score()

        for cell in self.colors:
            if self.colors[cell]:
                self.paint(cell)
            else:
                self.buttons[cell].setStyleSheet(
                    "background:#F5F5F5;border:1px solid #B0BEC5;"
                )

    #  HELPERS 
    def update_score(self):
        self.score_label.setText(
            f"Human: {self.human_score}    Computer: {self.cpu_score}"
        )

    def select_color(self, color):
        if not self.solving:
            self.selected_color = color
            self.status.setText(f"Selected color: {color.upper()}")

    def valid(self, cell, color):
        return all(self.colors[n] != color for n in self.graph[cell])

    def paint(self, cell):
        self.buttons[cell].setStyleSheet(
            f"background:{self.colors[cell]};border:1px solid #455A64;"
        )

    # SORTING
    def selection_sort_by_degree(self, nodes):
        nodes = nodes[:]
        for i in range(len(nodes)):
            max_i = i
            for j in range(i + 1, len(nodes)):
                if len(self.graph[nodes[j]]) > len(self.graph[nodes[max_i]]):
                    max_i = j
            nodes[i], nodes[max_i] = nodes[max_i], nodes[i]
        return nodes

    #  GAME OVER CHECK 
    def check_game_over(self):
        if all(self.colors[cell] is not None for cell in self.colors):
            self.show_winner()

    # MOVES
    def human_move(self, cell):
        if self.solving or not self.selected_color:
            return
        if self.colors[cell] is not None:
            return

        if not self.valid(cell, self.selected_color):
            self.human_score -= 1
            self.update_score()
            self.status.setText("Wrong move! (-1)")
            return

        self.colors[cell] = self.selected_color
        self.paint(cell)
        self.human_score += 1
        self.update_score()

        self.check_game_over()
        self.status.setText("Computer's turn...")
        QTimer.singleShot(400, self.cpu_move)

    def cpu_move(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            self.show_winner()
            return

        cell = self.selection_sort_by_degree(uncolored)[0]
        for col in COLORS:
            if self.valid(cell, col):
                self.colors[cell] = col
                self.paint(cell)
                self.cpu_score += 1
                self.update_score()
                break

        self.check_game_over()
        self.status.setText("Your turn")

    #  SOLVE 
    def solve_all(self):
        self.solving = True
        self.status.setText("Solving automatically...")
        QTimer.singleShot(200, self.solve_step)

    def solve_step(self):
        uncolored = [c for c in self.colors if self.colors[c] is None]
        if not uncolored:
            self.show_winner()
            return

        cell = self.selection_sort_by_degree(uncolored)[0]
        for col in COLORS:
            if self.valid(cell, col):
                self.colors[cell] = col
                self.paint(cell)
                break

        QTimer.singleShot(150, self.solve_step)

    def show_winner(self):
        if self.human_score > self.cpu_score:
            title = "HUMAN WINS!"
            color = "#2ECC71"
        elif self.cpu_score > self.human_score:
            title = "COMPUTER WINS!"
            color = "#E74C3C"
        else:
            title = "DRAW!"
            color = "#3498DB"

        popup = QWidget(self)
        popup.setWindowTitle("Game Result")
        popup.setFixedSize(420, 280)
        popup.setWindowModality(Qt.WindowModality.ApplicationModal)
        popup.setStyleSheet("background:white;border-radius:18px;")

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(25, 25, 25, 25)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"font-size:28px;font-weight:800;color:{color};")

        score = QLabel(
            f"Human Score: {self.human_score}\nComputer Score: {self.cpu_score}"
        )
        score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score.setStyleSheet("font-size:16px;font-weight:600;color:#2C3E50;")

        btn = QPushButton("Play Again")
        btn.setStyleSheet(
            "background:#2ECC71;color:white;border-radius:10px;padding:10px;font-weight:bold;"
        )
        btn.clicked.connect(lambda: [popup.close(), self.new_game()])

        layout.addWidget(t)
        layout.addWidget(score)
        layout.addStretch()
        layout.addWidget(btn)

    
        screen = QApplication.primaryScreen().availableGeometry()
        popup.move(
            (screen.width() - popup.width()) // 2,
            (screen.height() - popup.height()) // 2
        )

        popup.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
