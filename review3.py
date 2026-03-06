import sys
import random
import time
import numpy as np
from scipy.spatial import Voronoi

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QMessageBox, QTextEdit
)

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPolygonF, QPen, QBrush


COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]
COLOR_NAMES = ["Red", "Green", "Blue", "Yellow"]

STEP_DELAY = 800


# --------------------------------------------------
# ZOOMABLE VIEW
# --------------------------------------------------

class ZoomableGraphicsView(QGraphicsView):

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


# --------------------------------------------------
# REGION ITEM
# --------------------------------------------------

class RegionItem(QGraphicsPolygonItem):

    def __init__(self, polygon, region_id, game):
        super().__init__(polygon)
        self.region_id = region_id
        self.game = game
        self.setPen(QPen(QColor("#1e3a5f"), 1))
        self.setBrush(QBrush(QColor("#0d1f35")))

    def mousePressEvent(self, event):
        self.game.handle_region_click(self.region_id)


# --------------------------------------------------
# MAIN WINDOW
# --------------------------------------------------

class MapColoringGame(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("CHROMATIC – Map Coloring")
        self.resize(1200, 800)

        self.region_count = 25
        self.region_items = {}
        self.region_colors = {}
        self.adj_graph = {}

        self.human_score = 0
        self.cpu_score = 0

        self.selected_color = None

        self.init_ui()

        QTimer.singleShot(200, self.new_game)


# --------------------------------------------------
# UI
# --------------------------------------------------

    def init_ui(self):

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QHBoxLayout(main_widget)

        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)

        layout.addWidget(self.view, 4)

        side_panel = QVBoxLayout()

        self.score_label = QLabel("Human: 0 | CPU: 0")
        side_panel.addWidget(self.score_label)

        self.status_label = QLabel("Ready")
        side_panel.addWidget(self.status_label)

        self.timer_label = QLabel("CPU Time: 0 ms")
        side_panel.addWidget(self.timer_label)

        side_panel.addSpacing(20)

        for color in COLORS:
            btn = QPushButton(color)
            btn.setStyleSheet(f"background:{color};height:35px")
            btn.clicked.connect(lambda _, c=color: self.select_color(c))
            side_panel.addWidget(btn)

        side_panel.addSpacing(20)

        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self.reset_colors)
        side_panel.addWidget(reset_btn)

        auto_btn = QPushButton("CPU Auto Play")
        auto_btn.clicked.connect(self.cpu_turn)
        side_panel.addWidget(auto_btn)

        side_panel.addSpacing(20)

        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        side_panel.addWidget(self.log_panel)

        layout.addLayout(side_panel, 1)


# --------------------------------------------------
# NEW GAME
# --------------------------------------------------

    def new_game(self):

        self.scene.clear()

        self.region_items.clear()
        self.region_colors.clear()
        self.adj_graph.clear()

        points = np.random.rand(self.region_count, 2) * 600

        vor = Voronoi(points)

        for i, region_index in enumerate(vor.point_region):

            vertices = vor.regions[region_index]

            if -1 in vertices or len(vertices) == 0:
                continue

            polygon_points = [vor.vertices[v] for v in vertices]

            poly = QPolygonF([QPointF(x, y) for x, y in polygon_points])

            item = RegionItem(poly, i, self)

            self.scene.addItem(item)

            self.region_items[i] = item
            self.region_colors[i] = None

        self.build_adjacency_graph()

        self.log("New map generated")


# --------------------------------------------------
# BUILD GRAPH
# --------------------------------------------------

    def build_adjacency_graph(self):

        for r in self.region_items:
            self.adj_graph[r] = set()

        regions = list(self.region_items.keys())

        for i in regions:
            for j in regions:
                if i == j:
                    continue

                if self.region_items[i].collidesWithItem(self.region_items[j]):
                    self.adj_graph[i].add(j)


# --------------------------------------------------
# HUMAN MOVE
# --------------------------------------------------

    def handle_region_click(self, rid):

        if self.selected_color is None:
            return

        if self.region_colors[rid] is not None:
            return

        neighbors = self.adj_graph[rid]

        for n in neighbors:
            if self.region_colors[n] == self.selected_color:
                self.status_label.setText("Invalid move")
                self.human_score -= 1
                self.update_score()
                return

        self.apply_color(rid, self.selected_color)

        self.human_score += 1
        self.update_score()

        self.cpu_turn()


# --------------------------------------------------
# APPLY COLOR
# --------------------------------------------------

    def apply_color(self, rid, color):

        self.region_colors[rid] = color

        item = self.region_items[rid]

        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(QColor(color).lighter(), 1))


# --------------------------------------------------
# CPU TURN (DIVIDE & CONQUER)
# --------------------------------------------------

    def cpu_turn(self):

        start = time.perf_counter()

        uncolored = [r for r in self.region_colors if self.region_colors[r] is None]

        if not uncolored:
            return

        target = self.dc_pick(uncolored)

        if target is None:
            return

        self.greedy_color(target)

        end = time.perf_counter()

        runtime = (end - start) * 1000

        self.timer_label.setText(f"CPU Time: {runtime:.3f} ms")


# --------------------------------------------------
# DIVIDE
# --------------------------------------------------

    def divide(self, regions):

        centroids = [(r, self.compute_centroid(r)) for r in regions]

        xs = sorted(c[1][0] for c in centroids)

        median = xs[len(xs)//2]

        left = [r for r,(x,y) in centroids if x < median]
        right = [r for r,(x,y) in centroids if x >= median]

        return left, right


# --------------------------------------------------
# DC PICK
# --------------------------------------------------

    def dc_pick(self, regions):

        if not regions:
            return None

        if len(regions) == 1:
            return regions[0]

        left, right = self.divide(regions)

        if left:
            return self.dc_pick(left)

        return regions[0]


# --------------------------------------------------
# GREEDY COLOR
# --------------------------------------------------

    def greedy_color(self, rid):

        neighbor_colors = {
            self.region_colors[n]
            for n in self.adj_graph[rid]
            if self.region_colors[n]
        }

        for c in COLORS:

            if c not in neighbor_colors:

                self.apply_color(rid, c)

                self.cpu_score += 1

                self.update_score()

                self.log(f"CPU colored R{rid} → {c}")

                return True

        self.log(f"CPU failed to color R{rid}")

        return False


# --------------------------------------------------
# HELPERS
# --------------------------------------------------

    def compute_centroid(self, rid):

        poly = self.region_items[rid].polygon()

        x = sum(p.x() for p in poly) / len(poly)
        y = sum(p.y() for p in poly) / len(poly)

        return (x, y)


# --------------------------------------------------
# SCORE
# --------------------------------------------------

    def update_score(self):

        self.score_label.setText(
            f"Human: {self.human_score} | CPU: {self.cpu_score}"
        )

# --------------------------------------------------
# LOG
# --------------------------------------------------
    def log(self, text):
        self.log_panel.append(text)
# --------------------------------------------------
# RESET
# --------------------------------------------------

    def reset_colors(self):
        for rid in self.region_items:
            self.region_colors[rid] = None
            item = self.region_items[rid]
            item.setBrush(QBrush(QColor("#0d1f35")))
            item.setPen(QPen(QColor("#1e3a5f"),1))
        self.human_score = 0
        self.cpu_score = 0
        self.update_score()
        self.log("Map reset")
# --------------------------------------------------
# COLOR SELECT
# --------------------------------------------------
    def select_color(self, color):
        self.selected_color = color
        self.status_label.setText(f"Selected {color}")

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():

    app = QApplication(sys.argv)
    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
if __name__ == "__main__":
    main()
