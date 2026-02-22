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
        self.setWindowTitle("DAA Lab: D&C CPU Map Coloring")
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
        
        stats_layout = QHBoxLayout()
        self.status_label = QLabel("Mode: Divide & Conquer CPU Selection")
        self.timer_label = QLabel("Execution Time: 0ms")
        stats_layout.addWidget(self.status_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.timer_label)
        layout.addLayout(stats_layout)

        self.scene = QGraphicsScene()
        self.view = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)

        palette_container = QWidget()
        palette_layout = QHBoxLayout(palette_container)
        palette_layout.addWidget(QLabel("Your Brush:"))
        for i, col in enumerate(COLORS):
            btn = QPushButton(COLOR_NAMES[i])
            btn.setFixedSize(80, 30)
            btn.setStyleSheet(f"background-color: {col}; color: white; border-radius: 5px;")
            btn.clicked.connect(lambda chk, c=col: self.set_active_color(c))
            palette_layout.addWidget(btn)
        
        reset_btn = QPushButton("Reset Map")
        reset_btn.setFixedSize(100, 30)
        reset_btn.clicked.connect(self.reset_colors)
        palette_layout.addStretch()
        palette_layout.addWidget(reset_btn)
        layout.addWidget(palette_container)

    def create_menu(self):
        menubar = self.menuBar()
        map_menu = menubar.addMenu(" Map ")
        map_menu.addAction("Generate New Map", self.new_game)
        
        comp_menu = menubar.addMenu(" Complexity ")
        for label, count in [("Easy (15)", 15), ("Medium (30)", 30), ("Hard (60)", 60)]:
            act = QAction(label, self)
            act.triggered.connect(lambda chk, c=count: self.set_complexity(c))
            comp_menu.addAction(act)

        solve_menu = menubar.addMenu(" Full Solve Algorithms ")
        solve_menu.addAction("Greedy", self.solve_greedy)
        solve_menu.addAction("Backtracking", self.solve_backtracking)
        solve_menu.addAction("Divide & Conquer", self.solve_divide_and_conquer)

    def set_active_color(self, color):
        self.active_brush_color = color
        self.status_label.setText(f"Active Brush: {color}")

    # --- UPDATED CPU LOGIC (DIVIDE AND CONQUER) ---

    def handle_region_click(self, rid):
        if self.region_colors.get(rid) is not None:
            return

        neighbor_colors = {self.region_colors[nb] for nb in self.adj_graph[rid] if self.region_colors[nb]}
        
        if self.active_brush_color in neighbor_colors:
            self.status_label.setText("Conflict! Check neighbors.")
        else:
            self.apply_color(rid, self.active_brush_color)
            self.status_label.setText("User move placed. CPU calculating D&C split...")
            QTimer.singleShot(400, self.cpu_move_dc)

    def cpu_move_dc(self):
        """
        CPU move using Divide & Conquer selection strategy:
        1. Find uncolored regions.
        2. Divide them spatially (Sort by X).
        3. Pick the median (pivot) to resolve the seam of the current sub-problem.
        """
        start_time = time.perf_counter()
        uncolored = [rid for rid, col in self.region_colors.items() if col is None]
        
        if not uncolored:
            self.status_label.setText("Map Completed!")
            return

        # --- DIVIDE ---
        # Sort spatially (X-axis) - Complexity O(V log V)
        uncolored.sort(key=lambda rid: self.region_items[rid].boundingRect().center().x())
        
        # --- CONQUER ---
        # Pick the median as the pivot for this move
        mid_idx = len(uncolored) // 2
        target_rid = uncolored[mid_idx]

        # --- COMBINE (Validating against neighbors) ---
        neighbor_colors = {self.region_colors[nb] for nb in self.adj_graph[target_rid] if self.region_colors[nb]}
        
        found_color = False
        for col in COLORS:
            if col not in neighbor_colors:
                self.apply_color(target_rid, col)
                found_color = True
                break
        
        ms = (time.perf_counter() - start_time) * 1000
        if found_color:
            self.status_label.setText(f"CPU used D&C on Region {target_rid}")
        else:
            self.status_label.setText("CPU D&C couldn't find a valid move.")
        self.timer_label.setText(f"CPU Time: {ms:.4f}ms")

    # --- ALGORITHMS (FULL SOLVE) ---

    def solve_greedy(self):
        self.reset_colors()
        start_time = time.perf_counter()
        for node in self.region_items:
            neighbor_colors = {self.region_colors[nb] for nb in self.adj_graph[node] if self.region_colors[nb]}
            for col in COLORS:
                if col not in neighbor_colors:
                    self.apply_color(node, col)
                    break
        self.finalize_solve("Full Greedy", start_time)

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
            self.finalize_solve("Full Backtracking", start_time)

    def solve_divide_and_conquer(self):
        self.reset_colors()
        start_time = time.perf_counter()
        nodes = list(self.region_items.keys())
        
        

            # Divide
            node_list.sort(key=lambda n: self.region_items[n].boundingRect().center().x())
            mid = len(node_list) // 2
            dc_solve(node_list[:mid])
            dc_solve(node_list[mid:])

            # Combine (Fix conflicts)
            for n in node_list:
                neigh_cols = {self.region_colors.get(nb) for nb in self.adj_graph[n] if self.region_colors.get(nb)}
                if self.region_colors.get(n) in neigh_cols:
                    for c in COLORS:
                        if c not in neigh_cols:
                            self.region_colors[n] = c
                            break
        
        dc_solve(nodes)
        for n, c in self.region_colors.items(): self.apply_color(n, c)
        self.finalize_solve("Full D&C", start_time)

    # --- CORE UTILS ---

    def finalize_solve(self, name, start_time):
        ms = (time.perf_counter() - start_time) * 1000
        self.status_label.setText(f"Algorithm: {name}")
        self.timer_label.setText(f"Time: {ms:.2f}ms")

    def reset_colors(self):
        for rid in self.region_items:
            self.region_colors[rid] = None
            self.region_items[rid].setBrush(QBrush(QColor("#1e293b")))
        self.status_label.setText("Map Reset. Your turn!")

    def new_game(self):
        self.scene.clear()
        self.adj_graph, self.region_colors, self.region_items = {}, {}, {}
        width, height = 800, 600
        points = [[random.uniform(50, width-50), random.uniform(50, height-50)] for _ in range(self.region_count)]
        points.extend([[-1000, -1000], [2000, -1000], [-1000, 2000], [2000, 2000]])
        vor = Voronoi(points)
        clip_rect = QRectF(0, 0, width, height)
        rid = 0
        
        for region in vor.regions:
            if not region or -1 in region: continue
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
                if id1 >= id2: continue
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
