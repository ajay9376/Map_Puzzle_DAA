import sys
import random
import time
from scipy.spatial import Voronoi
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QGraphicsTextItem, QMessageBox, QGraphicsLineItem
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPolygonF, QPen, QBrush, QPainter, QAction, QFont

COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]
COLOR_NAMES = ["Red", "Green", "Blue", "Yellow"]


class ZoomableGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


class RegionItem(QGraphicsPolygonItem):
    def __init__(self, polygon, region_id, game_parent):
        super().__init__(polygon)
        self.region_id = region_id
        self.game_parent = game_parent
        self.setPen(QPen(QColor("#1e3a5f"), 1))
        self.setBrush(QBrush(QColor("#0d1f35")))

    def mousePressEvent(self, event):
        self.game_parent.handle_region_click(self.region_id)


class MapColoringGame(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("CHROMATIC – D&C Map Coloring")
        self.resize(1200, 800)

        self.region_count = 25
        self.adj_graph = {}
        self.region_colors = {}
        self.region_items = {}

        self.human_score = 0
        self.cpu_score = 0

        self.selected_color = None

        self.dc_steps = []
        self.current_step = 0

        self.init_ui()
        self.create_menu()

        QTimer.singleShot(100, self.new_game)

    # ---------------- USER MOVE ----------------

    def handle_region_click(self, rid):

        if self.selected_color is None:
            return

        if self.region_colors.get(rid) is not None:
            return

        neighbor_colors = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if self.region_colors[nb]
        }

        if self.selected_color not in neighbor_colors:
            self.apply_color(rid, self.selected_color, player="HUMAN")
            self.human_score += 1

        else:
            self.human_score -= 1

        self.update_score()
        QTimer.singleShot(300, self.cpu_move_dc)
        self.check_game_complete()

    # ---------------- CPU MOVE ----------------

    def cpu_move_dc(self):

        start = time.perf_counter()
        uncolored = [rid for rid, c in self.region_colors.items() if c is None]

        if not uncolored:
            return
        target = self.dc_select(uncolored)

        if target is not None:
            if not self.greedy_color(target):
                visited = set()
                self.resolve_deadlock(target, visited, depth=0)

        runtime = (time.perf_counter() - start) * 1000
        self.timer_label.setText(f"CPU Time: {runtime:.3f} ms")
        self.update_score()
        self.check_game_complete()

    # ---------------- DIVIDE & CONQUER ----------------

    def dc_select(self, region_list):

        if len(region_list) == 1:
            return region_list[0]

        centroids = [(rid, self.compute_centroid(rid)) for rid in region_list]
        x_values = sorted([c[1][0] for c in centroids])
        median_x = x_values[len(x_values) // 2]

        left = [rid for rid, (x, y) in centroids if x < median_x]
        right = [rid for rid, (x, y) in centroids if x >= median_x]

        if not left:
            left = right[:1]
        return self.dc_select(left)

    def compute_centroid(self, rid):
        polygon = self.region_items[rid].polygon()

        x = sum(p.x() for p in polygon) / len(polygon)
        y = sum(p.y() for p in polygon) / len(polygon)

        return (x, y)

    # ---------------- GREEDY COLOR ----------------

    def greedy_color(self, rid):

        neighbor_colors = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if self.region_colors[nb]
        }

        for col in COLORS:

            if col not in neighbor_colors:
                self.apply_color(rid, col, player="CPU")
                return True

        return False

    # ---------------- DEADLOCK REPAIR ----------------

    def resolve_deadlock(self, rid, visited, depth, max_depth=10):

        if depth > max_depth:
            return False

        visited.add(rid)
        neighbors = sorted(
            self.adj_graph[rid],
            key=lambda x: len(self.adj_graph[x])
        )

        for nb in neighbors:

            if nb in visited:
                continue

            alt_colors = self.get_alternative_colors(nb, exclude=rid)
            if alt_colors:

                new_color = alt_colors[0]
                self.region_colors[nb] = new_color
                self.region_items[nb].setBrush(QBrush(QColor(new_color)))

                if self.greedy_color(rid):
                    return True

                if self.resolve_deadlock(nb, visited, depth + 1):
                    return True

        return False

    def get_alternative_colors(self, rid, exclude=None):

        used = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if nb != exclude and self.region_colors[nb]
        }

        return [
            c for c in COLORS
            if c not in used and c != self.region_colors[rid]
        ]

    # ---------------- APPLY COLOR ----------------

    def apply_color(self, rid, color, player="CPU"):

        self.region_colors[rid] = color
        item = self.region_items[rid]
        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(QColor(color).lighter(150), 1))
        if player == "CPU":
            self.cpu_score += 1

    # ---------------- SCORE ----------------

    def update_score(self):
        self.score_label.setText(
            f"Human: {self.human_score} | CPU: {self.cpu_score}"
        )

    # ---------------- RESET ----------------

    def reset_colors(self):

        for rid in self.region_items:
            self.region_colors[rid] = None
            self.region_items[rid].setBrush(QBrush(QColor("#0d1f35")))

        self.human_score = 0
        self.cpu_score = 0
        self.update_score()

    # ---------------- GAME COMPLETE ----------------

    def check_game_complete(self):

        if any(c is None for c in self.region_colors.values()):
            return

        if self.human_score > self.cpu_score:
            winner = "Human Wins!"
        elif self.cpu_score > self.human_score:
            winner = "CPU Wins!"
        else:
            winner = "It's a Tie!"

        msg = QMessageBox(self)
        msg.setWindowTitle("Game Over")
        msg.setText(winner)
        msg.setInformativeText(
            f"Final Score\nHuman: {self.human_score}\nCPU: {self.cpu_score}"
        )
        msg.exec()

    # ---------------- COLOR SELECT ----------------

    def select_color(self, color):
        self.selected_color = color

    # ---------------- D&C VISUALIZATION ----------------

    def prepare_dc_steps(self):
        nodes = list(self.region_items.keys())
        self.dc_steps = []

        def collect(node_list):
            if len(node_list) <= 1:
                return

            centroids = [(rid, self.compute_centroid(rid)) for rid in node_list]
            xs = sorted([c[1][0] for c in centroids])
            median_x = xs[len(xs)//2]
            self.dc_steps.append(median_x)

            left = [rid for rid,(x,y) in centroids if x < median_x]
            right = [rid for rid,(x,y) in centroids if x >= median_x]
            collect(left)
            collect(right)

        collect(nodes)

    def show_next_dc_step(self):
        if self.current_step >= len(self.dc_steps):
            return
        x = self.dc_steps[self.current_step]
        line = QGraphicsLineItem(x, 0, x, 600)
        line.setPen(QPen(QColor("yellow"), 3, Qt.PenStyle.DashLine))
        self.scene.addItem(line)
        self.current_step += 1

    # ---------------- MAP GENERATION ----------------

    def new_game(self):

        self.scene.clear()
        self.adj_graph = {}
        self.region_colors = {}
        self.region_items = {}
        width, height = 800, 600

        points = [
            [random.uniform(50, width - 50),
             random.uniform(50, height - 50)]
            for _ in range(self.region_count)
        ]

        points.extend([
            [-1000, -1000],
            [2000, -1000],
            [-1000, 2000],
            [2000, 2000]
        ])

        vor = Voronoi(points)
        clip_rect = QRectF(0, 0, width, height)
        rid = 0

        for region in vor.regions:
            if not region or -1 in region:
                continue
            poly_points = [
                QPointF(vor.vertices[i][0], vor.vertices[i][1])
                for i in region
            ]

            poly = QPolygonF(poly_points)
            item = RegionItem(poly, rid, self)

            if clip_rect.intersects(item.boundingRect()):
                self.scene.addItem(item)
                self.region_items[rid] = item
                self.region_colors[rid] = None
                self.adj_graph[rid] = set()

                center = item.boundingRect().center()
                text = QGraphicsTextItem(str(rid))
                text.setDefaultTextColor(QColor("white"))
                text.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                text.setPos(center)
                self.scene.addItem(text)

                rid += 1

        for id1, item1 in self.region_items.items():
            for id2, item2 in self.region_items.items():
                if id1 >= id2:
                    continue
                p1 = set((round(v.x(), 0), round(v.y(), 0))
                         for v in item1.polygon())
                p2 = set((round(v.x(), 0), round(v.y(), 0))
                         for v in item2.polygon())
                if len(p1.intersection(p2)) >= 2:

                    self.adj_graph[id1].add(id2)
                    self.adj_graph[id2].add(id1)

        self.prepare_dc_steps()
        self.current_step = 0

        self.scene.setSceneRect(clip_rect)
        self.view.fitInView(clip_rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ---------------- SOLVE ALGORITHMS ----------------

    def solve_greedy(self):

        self.reset_colors()
        for node in self.region_items:
            neighbor_colors = {
                self.region_colors[nb]
                for nb in self.adj_graph[node]
                if self.region_colors[nb]
            }

            for col in COLORS:
                if col not in neighbor_colors:
                    self.apply_color(node, col)
                    break

    def solve_backtracking(self):

        self.reset_colors()
        nodes = list(self.region_items.keys())

        def backtrack(index):
            if index == len(nodes):
                return True
            node = nodes[index]
            for col in COLORS:
                if all(self.region_colors[nb] != col for nb in self.adj_graph[node]):
                    self.region_colors[node] = col
                    if backtrack(index + 1):
                        return True
                    self.region_colors[node] = None
            return False
        if backtrack(0):
            for n, c in self.region_colors.items():
                self.apply_color(n, c)

    def solve_divide_and_conquer(self):
        self.reset_colors()
        nodes = list(self.region_items.keys())
        def dc_solve(node_list):
            if not node_list:
                return
            if len(node_list) == 1:
                n = node_list[0]
                used = {
                    self.region_colors[nb]
                    for nb in self.adj_graph[n]
                    if self.region_colors[nb] is not None
                }
                for c in COLORS:
                    if c not in used:
                        self.region_colors[n] = c
                        break
                return

            node_list.sort(
                key=lambda n: self.region_items[n].boundingRect().center().x()
            )
            mid = len(node_list) // 2
            dc_solve(node_list[:mid])
            dc_solve(node_list[mid:])

        dc_solve(nodes)

        for n, c in self.region_colors.items():
            if c:
                self.apply_color(n, c)

    # ---------------- MENU ----------------

    def create_menu(self):

        menubar = self.menuBar()
        map_menu = menubar.addMenu("Map")
        map_menu.addAction("Generate New Map", self.new_game)
        comp_menu = menubar.addMenu("Complexity")

        for label, count in [("Easy (15)", 15), ("Medium (30)", 30), ("Hard (60)", 60)]:
            act = QAction(label, self)
            act.triggered.connect(lambda chk, c=count: self.set_complexity(c))
            comp_menu.addAction(act)

        solve_menu = menubar.addMenu("Solve")
        solve_menu.addAction("Greedy", self.solve_greedy)
        solve_menu.addAction("Divide & Conquer", self.solve_divide_and_conquer)
        solve_menu.addAction("Backtracking", self.solve_backtracking)

    def set_complexity(self, count):
        self.region_count = count
        self.new_game()

    # ---------------- UI ----------------

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        top_layout = QHBoxLayout()
        self.timer_label = QLabel("CPU Time: 0 ms")
        top_layout.addWidget(self.timer_label)
        layout.addLayout(top_layout)
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)
        bottom_layout = QHBoxLayout()
        self.score_label = QLabel("Human: 0 | CPU: 0")
        bottom_layout.addWidget(self.score_label)

        for i, c in enumerate(COLORS):
            btn = QPushButton(COLOR_NAMES[i])
            btn.setStyleSheet(f"background:{c}; height:40px")
            btn.clicked.connect(
                lambda _, col=c: self.select_color(col)
            )
            bottom_layout.addWidget(btn)
        reset_btn = QPushButton("Reset Map")
        reset_btn.clicked.connect(self.reset_colors)
        bottom_layout.addWidget(reset_btn)
        step_btn = QPushButton("Next D&C Step")
        step_btn.clicked.connect(self.show_next_dc_step)
        bottom_layout.addWidget(step_btn)
        layout.addLayout(bottom_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
