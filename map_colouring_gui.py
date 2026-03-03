import sys
import random
import time
from scipy.spatial import Voronoi
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QFrame, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPolygonF, QPen, QBrush, QPainter, QAction

COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]

# ─────────────────────────────────────────────────────────────
# GRAPHICS ITEMS
# ─────────────────────────────────────────────────────────────

class ZoomableGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


class RegionItem(QGraphicsPolygonItem):
    def __init__(self, polygon, region_id, game_parent):
        super().__init__(polygon)
        self.region_id = region_id
        self.game_parent = game_parent
        self.setPen(QPen(QColor("#1e3a5f"), 1.2))
        self.setBrush(QBrush(QColor("#0d1f35")))

    def mousePressEvent(self, event):
        self.game_parent.handle_region_click(self.region_id)


# ─────────────────────────────────────────────────────────────
# MAIN GAME CLASS
# ─────────────────────────────────────────────────────────────

class MapColoringGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Geometric Divide & Conquer Map Coloring")
        self.resize(1200, 850)

        self.region_count = 25
        self.adj_graph = {}
        self.region_colors = {}
        self.region_items = {}
        self.active_brush_color = COLORS[0]

        self.human_score = 0
        self.cpu_score = 0

        self.init_ui()
        QTimer.singleShot(100, self.new_game)

    # ───────────────── USER MOVE ─────────────────

    def handle_region_click(self, rid):
        if self.region_colors.get(rid) is not None:
            return

        neighbor_colors = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if self.region_colors[nb]
        }

        if self.active_brush_color in neighbor_colors:
            self.status_label.setText("Conflict detected!")
        else:
            self.apply_color(rid, self.active_brush_color, player="HUMAN")
            QTimer.singleShot(400, self.cpu_move_dc)

    # ───────────────── CPU MOVE ─────────────────

    def cpu_move_dc(self):
        start_time = time.perf_counter()

        uncolored = [rid for rid, col in self.region_colors.items() if col is None]

        if not uncolored:
            self.status_label.setText("Map Complete!")
            return

        target = self.dc_select(uncolored)

        if target is not None:
            success = self.greedy_color(target)

            if not success:
                resolved = self.resolve_deadlock(target)

                # Safe fallback (rare case)
                if not resolved:
                    self.status_label.setText("Rare deadlock — restarting map")
                    self.new_game()
                    return

        ms = (time.perf_counter() - start_time) * 1000
        self.status_label.setText(f"CPU Move Time: {ms:.3f} ms")

    # ───────────────── GEOMETRIC D&C ─────────────────

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
        if not right:
            right = left[:1]

        # Divide → Conquer → Combine (selection)
        left_candidate = self.dc_select(left)
        if left_candidate is not None:
            return left_candidate
        return self.dc_select(right)

    def compute_centroid(self, rid):
        polygon = self.region_items[rid].polygon()
        x_sum = sum(point.x() for point in polygon)
        y_sum = sum(point.y() for point in polygon)
        return (x_sum / len(polygon), y_sum / len(polygon))

    # ───────────────── GREEDY COLORING ─────────────────

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

    # ───────────────── DEADLOCK RESOLUTION ─────────────────

    def resolve_deadlock(self, rid):
        neighbors = list(self.adj_graph[rid])
        candidates = []

        for nb in neighbors:
            alt_colors = self.get_alternative_colors(nb, exclude=rid)
            if alt_colors:
                degree = len(self.adj_graph[nb])
                candidates.append((degree, nb, alt_colors))

        if not candidates:
            return False

        # Select smallest degree neighbor
        candidates.sort(key=lambda x: x[0])
        _, chosen_nb, alt_colors = candidates[0]

        new_color = alt_colors[0]
        self.region_colors[chosen_nb] = new_color
        self.region_items[chosen_nb].setBrush(QBrush(QColor(new_color)))

        return self.greedy_color(rid)

    def get_alternative_colors(self, rid, exclude=None):
        used = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if nb != exclude and self.region_colors[nb]
        }

        return [c for c in COLORS if c not in used and c != self.region_colors[rid]]

    # ───────────────── APPLY COLOR ─────────────────

    def apply_color(self, rid, color, player="CPU"):
        self.region_colors[rid] = color
        self.region_items[rid].setBrush(QBrush(QColor(color)))

        if player == "HUMAN":
            self.human_score += 1
        else:
            self.cpu_score += 1

    # ───────────────── MAP GENERATION ─────────────────

    def new_game(self):
        self.scene.clear()
        self.adj_graph, self.region_colors, self.region_items = {}, {}, {}
        self.human_score = 0
        self.cpu_score = 0

        width, height = 800, 600
        points = [
            [random.uniform(50, width - 50), random.uniform(50, height - 50)]
            for _ in range(self.region_count)
        ]
        points.extend([[-1000, -1000], [2000, -1000], [-1000, 2000], [2000, 2000]])
        vor = Voronoi(points)
        clip_rect = QRectF(0, 0, width, height)
        rid = 0

        for region in vor.regions:
            if not region or -1 in region:
                continue
            poly_points = [QPointF(vor.vertices[i][0], vor.vertices[i][1]) for i in region]
            poly = QPolygonF(poly_points)
            item = RegionItem(poly, rid, self)
            if clip_rect.intersects(item.boundingRect()):
                self.scene.addItem(item)
                self.region_items[rid] = item
                self.region_colors[rid] = None
                self.adj_graph[rid] = set()
                rid += 1

        for id1, item1 in self.region_items.items():
            for id2, item2 in self.region_items.items():
                if id1 >= id2:
                    continue
                p1 = set((round(v.x(), 0), round(v.y(), 0)) for v in item1.polygon())
                p2 = set((round(v.x(), 0), round(v.y(), 0)) for v in item2.polygon())
                if len(p1.intersection(p2)) >= 2:
                    self.adj_graph[id1].add(id2)
                    self.adj_graph[id2].add(id1)

        self.scene.setSceneRect(clip_rect)
        self.view.fitInView(clip_rect, Qt.AspectRatioMode.KeepAspectRatio)

    # ───────────────── UI ─────────────────

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)

        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)


# ───────────────── MAIN ─────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
