import sys
import random
import time
import numpy as np
from scipy.spatial import Voronoi
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow, 
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPolygonF, QPen, QBrush, QPainter, QAction

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
        self.setPen(QPen(QColor("#475569"), 1.5))
        self.setBrush(QBrush(QColor("#1e293b")))

    def mousePressEvent(self, event):
        self.game_parent.handle_region_click(self.region_id)

class MapColoringGame(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DAA Algorithm Lab: Map Coloring")
        self.resize(1200, 900)
        
        self.region_count = 25
        self.adj_graph = {} 
        self.region_colors = {}
        self.region_items = {}
        self.active_brush_color = COLORS[0]

        self.init_ui()
        self.create_menu()
        self.apply_theme()
        QTimer.singleShot(100, self.new_game)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Stats Bar
        stats_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.timer_label = QLabel("Execution Time: 0ms")
        stats_layout.addWidget(self.status_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.timer_label)
        layout.addLayout(stats_layout)

        # Scene
        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)

        # Color Selection Palette (Visible at Bottom)
        palette_container = QWidget()
        palette_layout = QHBoxLayout(palette_container)
        palette_layout.addWidget(QLabel("Manual Brush:"))
        for i, col in enumerate(COLORS):
            btn = QPushButton(COLOR_NAMES[i])
            btn.setFixedSize(80, 30)
            btn.setStyleSheet(f"background-color: {col}; color: white; border-radius: 5px;")
            btn.clicked.connect(lambda chk, c=col: self.set_active_color(c))
            palette_layout.addWidget(btn)
        palette_layout.addStretch()
        layout.addWidget(palette_container)

    def create_menu(self):
        menubar = self.menuBar()
        
        # Map Menu
        map_menu = menubar.addMenu(" Map ")
        map_menu.addAction("Generate New Map", self.new_game)
        
        # Complexity Menu
        comp_menu = menubar.addMenu(" Complexity ")
        for label, count in [("Easy (15)", 15), ("Medium (30)", 30), ("Hard (60)", 60)]:
            act = QAction(label, self)
            act.triggered.connect(lambda chk, c=count: self.set_complexity(c))
            comp_menu.addAction(act)

        # Solve Menu
        solve_menu = menubar.addMenu(" Solve (Algorithms) ")
        solve_menu.addAction("1. Greedy Algorithm", self.solve_greedy)
        solve_menu.addAction("2. Backtracking (Exhaustive)", self.solve_backtracking)
        solve_menu.addAction("3. Divide & Conquer (Spatial)", self.solve_divide_and_conquer)

    def set_active_color(self, color):
        self.active_brush_color = color
        self.status_label.setText(f"Active Color: {color}")

    # --- ALGORITHMS ---

    def solve_greedy(self):
        self.reset_colors()
        start_time = time.perf_counter()
        
        # Greedy logic: Assign the first available color to each node
        for node in self.region_items:
            neighbor_colors = {self.region_colors[nb] for nb in self.adj_graph[node] if self.region_colors[nb]}
            for col in COLORS:
                if col not in neighbor_colors:
                    self.apply_color(node, col)
                    break
        
        self.finalize_solve("Greedy", start_time)

    def solve_backtracking(self):
        self.reset_colors()
        start_time = time.perf_counter()
        nodes = list(self.region_items.keys())
        
        def backtrack(index):
            if index == len(nodes): return True
            node = nodes[index]
            for col in COLORS:
                if all(self.region_colors[nb] != col for nb in self.adj_graph[node]):
                    self.region_colors[node] = col
                    if backtrack(index + 1): return True
                    self.region_colors[node] = None 
            return False

        if backtrack(0):
            for n, c in self.region_colors.items(): self.apply_color(n, c)
            self.finalize_solve("Backtracking", start_time)
        else:
            self.status_label.setText("No solution found.")

    def solve_divide_and_conquer(self):
        
        self.reset_colors()
        start_time = time.perf_counter()
        nodes = list(self.region_items.keys())
        
        def dc_solve(node_list):
            if not node_list: return
            if len(node_list) <= 3:
                for n in node_list:
                    used = {self.region_colors.get(nb) for nb in self.adj_graph[n] if self.region_colors.get(nb)}
                    for c in COLORS:
                        if c not in used:
                            self.region_colors[n] = c
                            break
                return

            # Divide spatially
            node_list.sort(key=lambda n: self.region_items[n].boundingRect().center().x())
            mid = len(node_list) // 2
            dc_solve(node_list[:mid])
            dc_solve(node_list[mid:])

            # Combine: Fix conflicts on the "seam"
            for n in node_list:
                neigh_cols = {self.region_colors.get(nb) for nb in self.adj_graph[n] if self.region_colors.get(nb)}
                if self.region_colors.get(n) in neigh_cols:
                    for c in COLORS:
                        if c not in neigh_cols:
                            self.region_colors[n] = c
                            break
        
        dc_solve(nodes)
        for n, c in self.region_colors.items(): self.apply_color(n, c)
        self.finalize_solve("Divide & Conquer", start_time)

    # --- CORE UTILS ---

    def finalize_solve(self, name, start_time):
        ms = (time.perf_counter() - start_time) * 1000
        self.status_label.setText(f"Algorithm: {name}")
        self.timer_label.setText(f"Time: {ms:.2f}ms")

    def reset_colors(self):
        for rid in self.region_items:
            self.region_colors[rid] = None
            self.region_items[rid].setBrush(QBrush(QColor("#1e293b")))

    def new_game(self):
        self.scene.clear()
        self.adj_graph, self.region_colors, self.region_items = {}, {}, {}
        
        width, height = 800, 600
        # Generate random points but keep them away from the extreme edges
        points = [[random.uniform(50, width-50), random.uniform(50, height-50)] for _ in range(self.region_count)]
        
        # Dummy points to ensure Voronoi covers the whole screen
        points.extend([[-1000, -1000], [2000, -1000], [-1000, 2000], [2000, 2000]])
        vor = Voronoi(points)
        
        # Clipping Rect to stop shapes from being too big at corners
        clip_rect = QRectF(0, 0, width, height)
        rid = 0
        
        for region in vor.regions:
            if not region or -1 in region: continue
            poly_points = [QPointF(vor.vertices[i][0], vor.vertices[i][1]) for i in region]
            poly = QPolygonF(poly_points)
            
            # Intersection with main view area only
            item = RegionItem(poly, rid, self)
            if clip_rect.intersects(item.boundingRect()):
                self.scene.addItem(item)
                self.region_items[rid] = item
                self.region_colors[rid] = None
                self.adj_graph[rid] = set()
                rid += 1

        # Calculate Adjacency
        for id1, item1 in self.region_items.items():
            for id2, item2 in self.region_items.items():
                if id1 >= id2: continue
                # Precision check for shared edges
                p1 = set((round(v.x(), 0), round(v.y(), 0)) for v in item1.polygon())
                p2 = set((round(v.x(), 0), round(v.y(), 0)) for v in item2.polygon())
                if len(p1.intersection(p2)) >= 2:
                    self.adj_graph[id1].add(id2)
                    self.adj_graph[id2].add(id1)

        self.scene.setSceneRect(clip_rect)
        self.view.fitInView(clip_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def apply_color(self, rid, color):
        self.region_colors[rid] = color
        self.region_items[rid].setBrush(QBrush(QColor(color if color else "#1e293b")))

    def set_complexity(self, count):
        self.region_count = count
        self.new_game()

    def handle_region_click(self, rid):
        # Check for conflicts manually
        neighbor_colors = {self.region_colors[nb] for nb in self.adj_graph[rid]}
        if self.active_brush_color in neighbor_colors:
            self.status_label.setText("Conflict! Can't place that color there.")
        else:
            self.apply_color(rid, self.active_brush_color)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QLabel { color: #cbd5e1; font-family: 'Segoe UI'; font-weight: bold; }
            QMenuBar { background-color: #1e293b; color: #f8fafc; padding: 5px; }
            QMenuBar::item:selected { background-color: #3b82f6; border-radius: 4px; }
            QPushButton { background-color: #334155; color: white; border: none; padding: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #475569; }
            QGraphicsView { border: 2px solid #334155; background-color: #020617; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
