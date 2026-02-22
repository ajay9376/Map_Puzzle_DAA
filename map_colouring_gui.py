import sys
import random
import numpy as np
from scipy.spatial import Voronoi
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QComboBox, QDialog, 
    QFrame, QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QFont, QColor, QPolygonF, QPen, QBrush, QPainter

COLORS = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]
COLOR_NAMES = ["Red", "Green", "Blue", "Yellow"]

class ZoomableGraphicsView(QGraphicsView):
    """Custom view to handle mouse wheel zooming"""
    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

class RegionItem(QGraphicsPolygonItem):
    """Custom Polygon Item to handle clicks and coloring"""
    def __init__(self, polygon, region_id, game_parent):
        super().__init__(polygon)
        self.region_id = region_id
        self.game_parent = game_parent
        self.setAcceptHoverEvents(True)
        self.setPen(QPen(QColor("#475569"), 2))
        self.setBrush(QBrush(QColor("#1e293b")))

    def mousePressEvent(self, event):
        self.game_parent.handle_region_click(self.region_id)

class MapColoringGame(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Polygonal Map Coloring - Graph Theory")
        self.resize(1200, 900)
        
        self.region_count = 15
        self.adj_graph = {} 
        self.region_colors = {}
        self.region_items = {}
        self.human_score = 0
        self.cpu_score = 0
        self.selected_color = None

        self.init_ui()
        self.apply_theme()
        QTimer.singleShot(100, self.new_game)

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Voronoi Map Game")
        title.setStyleSheet("font-size:30px; font-weight:800;")
        self.status_label = QLabel("Scroll to Zoom | Drag to Pan")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Controls
        controls = QHBoxLayout()
        self.diff_dropdown = QComboBox()
        self.diff_dropdown.addItems(["Easy (10 regions)", "Medium (20 regions)", "Hard (35 regions)"])
        self.diff_dropdown.currentIndexChanged.connect(self.change_difficulty)
        
        new_btn = QPushButton("Generate New Map")
        new_btn.clicked.connect(self.new_game)

        solve_btn = QPushButton("Solve (Backtracking)")
        solve_btn.setStyleSheet("background-color: #10b981;")
        solve_btn.clicked.connect(self.solve_map)
        
        controls.addWidget(QLabel("Complexity:"))
        controls.addWidget(self.diff_dropdown)
        controls.addStretch()
        controls.addWidget(solve_btn)
        controls.addWidget(new_btn)
        layout.addLayout(controls)

        # Score Board
        self.score_label = QLabel("Human: 0 | Computer: 0")
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("font-size:20px; background: rgba(255,255,255,0.1); border-radius:10px; padding:10px;")
        layout.addWidget(self.score_label)

        # Game Area
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.view.setStyleSheet("background: #0f172a; border-radius: 15px; border: 1px solid #334155;")
        layout.addWidget(self.view)

        # Color Palette
        palette = QHBoxLayout()
        palette.addStretch()
        for color, name in zip(COLORS, COLOR_NAMES):
            btn = QPushButton(name)
            btn.setFixedSize(100, 40)
            btn.setStyleSheet(f"background: {color}; color: white; font-weight: bold; border-radius: 8px;")
            btn.clicked.connect(lambda _, c=color: self.select_color(c))
            palette.addWidget(btn)
        palette.addStretch()
        layout.addLayout(palette)

    def change_difficulty(self):
        counts = [10, 20, 35]
        self.region_count = counts[self.diff_dropdown.currentIndex()]
        self.new_game()

    def generate_map(self):
        self.scene.clear()
        self.adj_graph = {}
        self.region_colors = {}
        self.region_items = {}
        
        v_w, v_h = 1000, 1000
        points = [[random.uniform(0, v_w), random.uniform(0, v_h)] for _ in range(self.region_count)]
        points.extend([[-v_w, -v_h], [-v_w, 2*v_h], [2*v_w, -v_h], [2*v_w, 2*v_h]])
        
        vor = Voronoi(points)
        region_idx = 0
        
        for region in vor.regions:
            if not region or -1 in region: continue
            
            polygon_points = [QPointF(vor.vertices[i][0], vor.vertices[i][1]) for i in region]
            poly_item = RegionItem(QPolygonF(polygon_points), region_idx, self)
            
            if poly_item.boundingRect().width() > v_w * 1.2: continue

            self.scene.addItem(poly_item)
            self.region_items[region_idx] = poly_item
            self.region_colors[region_idx] = None
            self.adj_graph[region_idx] = set()
            region_idx += 1

        for id1, item1 in self.region_items.items():
            for id2, item2 in self.region_items.items():
                if id1 >= id2: continue
                set1 = set((round(p.x(), 1), round(p.y(), 1)) for p in item1.polygon())
                set2 = set((round(p.x(), 1), round(p.y(), 1)) for p in item2.polygon())
                if len(set1.intersection(set2)) >= 2:
                    self.adj_graph[id1].add(id2)
                    self.adj_graph[id2].add(id1)

        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def select_color(self, color):
        self.selected_color = color
        self.status_label.setText(f"Active Color: {color}")

    def handle_region_click(self, region_id):
        if not self.selected_color or self.region_colors[region_id]:
            return

        for neighbor in self.adj_graph.get(region_id, []):
            if self.region_colors[neighbor] == self.selected_color:
                self.status_label.setText("Conflict!")
                return

        self.region_colors[region_id] = self.selected_color
        self.region_items[region_id].setBrush(QBrush(QColor(self.selected_color)))
        self.human_score += 1
        self.update_stats()
        QTimer.singleShot(400, self.cpu_move)

    def cpu_move(self):
        uncolored = [r for r, c in self.region_colors.items() if c is None]
        if not uncolored: return

        random.shuffle(uncolored)
        for rid in uncolored:
            available_colors = list(COLORS)
            random.shuffle(available_colors)
            for col in available_colors:
                if all(self.region_colors.get(nb) != col for nb in self.adj_graph.get(rid, [])):
                    self.region_colors[rid] = col
                    self.region_items[rid].setBrush(QBrush(QColor(col)))
                    self.cpu_score += 1
                    self.update_stats()
                    return

    def solve_map(self):
        """Backtracking solver for the polygonal graph"""
        def is_safe(node, color, assignment):
            for neighbor in self.adj_graph.get(node, []):
                if neighbor in assignment and assignment[neighbor] == color:
                    return False
            return True

        def backtrack(nodes, assignment):
            if not nodes:
                return assignment
            
            node = nodes[0]
            for color in COLORS:
                if is_safe(node, color, assignment):
                    assignment[node] = color
                    result = backtrack(nodes[1:], assignment)
                    if result: return result
                    del assignment[node]
            return None

        all_nodes = list(self.region_items.keys())
        solution = backtrack(all_nodes, {})
        
        if solution:
            for rid, color in solution.items():
                self.region_colors[rid] = color
                self.region_items[rid].setBrush(QBrush(QColor(color)))
            self.status_label.setText("Map Solved via Backtracking")
        else:
            self.status_label.setText("No solution possible with 4 colors!")

    def update_stats(self):
        self.score_label.setText(f"Human: {self.human_score} | Computer: {self.cpu_score}")

    def new_game(self):
        self.human_score = 0
        self.cpu_score = 0
        self.update_stats()
        self.generate_map()
        self.view.resetTransform()
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def apply_theme(self):
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; color: #f8fafc; font-family: 'Segoe UI'; }
            QPushButton { background-color: #6366f1; border: none; padding: 8px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #4f46e5; }
            QComboBox { background: #1e293b; border: 1px solid #334155; padding: 5px; border-radius: 5px; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    game = MapColoringGame()
    game.show()
    sys.exit(app.exec())
