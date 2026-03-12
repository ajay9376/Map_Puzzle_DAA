import sys
import random
import time
from scipy.spatial import Voronoi
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QMainWindow,
    QGraphicsView, QGraphicsScene, QGraphicsPolygonItem,
    QGraphicsTextItem, QMessageBox, QGraphicsLineItem,
    QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPolygonF, QPen, QBrush, QPainter, QAction, QFont, QPalette

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
COLORS       = ["#ef4444", "#22c55e", "#3b82f6", "#eab308"]
COLOR_NAMES  = ["Red",     "Green",   "Blue",    "Yellow"]
STEP_DELAY   = 1000   # ms between each animation step


# ─────────────────────────────────────────────
#  ZOOMABLE VIEW
# ─────────────────────────────────────────────
class ZoomableGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


# ─────────────────────────────────────────────
#  REGION ITEM
# ─────────────────────────────────────────────
class RegionItem(QGraphicsPolygonItem):
    def __init__(self, polygon, region_id, game_parent):
        super().__init__(polygon)
        self.region_id   = region_id
        self.game_parent = game_parent
        self.deadlocked  = False
        self._reset_style()

    def _reset_style(self):
        self.setPen(QPen(QColor("#1e3a5f"), 1))
        self.setBrush(QBrush(QColor("#0d1f35")))

    def mark_deadlock(self, active: bool):
        self.deadlocked = active
        if active:
            self.setPen(QPen(QColor("#ff0000"), 4))
            self.setBrush(QBrush(QColor("#3a0000")))
        else:
            self._reset_style()

    def highlight_target(self):
        """White glow = CPU is targeting this region."""
        self.setPen(QPen(QColor("#ffffff"), 4))

    def highlight_boundary(self):
        """Orange glow = boundary region being checked."""
        self.setPen(QPen(QColor("#ff6600"), 4))

    def highlight_considering(self):
        """Yellow = backtrack considering this neighbor."""
        self.setPen(QPen(QColor("#facc15"), 4))

    def highlight_trying(self, color):
        """Lighter shade = tentative recolor."""
        self.setPen(QPen(QColor("#ffffff"), 3))
        self.setBrush(QBrush(QColor(color).lighter(130)))

    def highlight_undo(self, old_color):
        """Orange = undo happening."""
        self.setPen(QPen(QColor("#ff6600"), 3))
        self.setBrush(QBrush(QColor(old_color)))

    def mousePressEvent(self, event):
        self.game_parent.handle_region_click(self.region_id)


# ─────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────
class MapColoringGame(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CHROMATIC – Map Coloring  [Review 3 - backtracking D&C]")
        self.resize(1280, 860)

        self.region_count   = 25
        self.adj_graph      = {}
        self.region_colors  = {}
        self.region_items   = {}

        self.human_score    = 0
        self.cpu_score      = 0
        self.selected_color = None

        self.dc_steps       = []
        self.current_step   = 0

        # ── In-order pick queue ──────────────────
        # Built once per game/reset; CPU pops from front each turn.
        self._inorder_queue = []

        self.deadlocked_regions = set()
        self.auto_play_active   = False

        # Animation engine
        self._animating  = False
        self._anim_steps = []
        self._anim_index = 0
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._run_next_anim_step)

        # Pulse timer
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_state = False
        self._pulse_timer.start(500)

        self.init_ui()
        self.create_menu()
        QTimer.singleShot(100, self.new_game)

    # ══════════════════════════════════════════
    #  IN-ORDER TRAVERSAL BUILDER
    #  Produces the picking order:
    #    left-leaf, left-node, right-leaf, parent, ...
    #  exactly like in-order traversal of a binary tree.
    # ══════════════════════════════════════════
    def _build_inorder_queue(self, region_list=None):
        """
        Recursively traverse the D&C binary tree in IN-ORDER:
            inorder(left)  → root (current split midpoint region)
                           → inorder(right)

        The 'root' of each subproblem is the median-X region
        (the region closest to the split line), representing
        the node that 'owns' this divide step.

        Picking order example (your diagram):
            Tree:        1
                      2     3
                    4  5  6   7 ...

            In-order: 4, 2, 5, 1, 6, 3, 7
        """
        if region_list is None:
            region_list = list(self.region_items.keys())

        self._inorder_queue = []
        self._inorder_collect(region_list, self._inorder_queue)

        self.log(
            f"📋 dc built: {self._inorder_queue}",
            "#888"
        )

    def _inorder_collect(self, region_list, result):
        """
        Recursive in-order D&C collection.
        Base cases:
          - empty  → nothing
          - 1 item → that item is both left-leaf and root; just append it
        Recursive case:
          1. Split by median X → left, right
          2. Find the 'root' region = closest to the median line
          3. Remove root from left/right to avoid double-pick
          4. inorder(left_without_root)
          5. append root
          6. inorder(right_without_root)
        """
        if not region_list:
            return

        if len(region_list) == 1:
            result.append(region_list[0])
            return

        # Compute centroids
        centroids = {rid: self.compute_centroid(rid) for rid in region_list}

        # Find median X
        x_values = sorted(centroids[rid][0] for rid in region_list)
        median_x = x_values[len(x_values) // 2]

        # Split
        left  = [rid for rid in region_list if centroids[rid][0] <  median_x]
        right = [rid for rid in region_list if centroids[rid][0] >= median_x]

        # Ensure both sides non-empty
        if not left:
            left  = right[:len(right) // 2]
            right = right[len(right) // 2:]

        # The 'root' of this sub-tree = region closest to the split line
        root = min(region_list,
                   key=lambda rid: abs(centroids[rid][0] - median_x))

        # Remove root from whichever side it landed in
        left_sub  = [r for r in left  if r != root]
        right_sub = [r for r in right if r != root]

        self.log(
            f"  📐 Split: left({len(left_sub)}) ← root=R{root} → right({len(right_sub)})",
            "#facc15"
        )

        # IN-ORDER: left → root → right
        self._inorder_collect(left_sub,  result)
        result.append(root)
        self._inorder_collect(right_sub, result)

    # ══════════════════════════════════════════
    #  ANIMATION ENGINE
    # ══════════════════════════════════════════
    def _queue_animation(self, steps: list, on_done=None):
        self._animating  = True
        self._anim_steps = list(steps)
        self._anim_steps.append(lambda: self._finish_animation(on_done))
        self._anim_index = 0
        self._anim_timer.start(STEP_DELAY)

    def _run_next_anim_step(self):
        if self._anim_index >= len(self._anim_steps):
            self._anim_timer.stop()
            return
        self._anim_steps[self._anim_index]()
        self._anim_index += 1

    def _finish_animation(self, on_done):
        self._anim_timer.stop()
        self._animating = False
        if on_done:
            on_done()

    # ══════════════════════════════════════════
    #  PULSE (deadlock flash)
    # ══════════════════════════════════════════
    def _pulse_tick(self):
        self._pulse_state = not self._pulse_state
        for rid in self.deadlocked_regions:
            item = self.region_items.get(rid)
            if item is None or self.region_colors.get(rid) is not None:
                continue
            if self._pulse_state:
                item.setPen(QPen(QColor("#ff0000"), 4))
                item.setBrush(QBrush(QColor("#3a0000")))
            else:
                item.setPen(QPen(QColor("#ff6600"), 3))
                item.setBrush(QBrush(QColor("#1a0000")))

    # ══════════════════════════════════════════
    #  LOG
    # ══════════════════════════════════════════
    def log(self, msg: str, color: str = "white"):
        self.log_panel.append(f'<span style="color:{color};">{msg}</span>')
        sb = self.log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_clear(self):
        self.log_panel.clear()

    # ══════════════════════════════════════════
    #  DEADLOCK DETECTION
    # ══════════════════════════════════════════
    def detect_deadlocks(self):
        new_deadlocks = set()
        for rid, color in self.region_colors.items():
            if color is not None:
                continue
            neighbor_colors = {
                self.region_colors[nb]
                for nb in self.adj_graph[rid]
                if self.region_colors[nb] is not None
            }
            if len(neighbor_colors) == len(COLORS):
                new_deadlocks.add(rid)

        for rid in self.deadlocked_regions - new_deadlocks:
            item = self.region_items.get(rid)
            if item and self.region_colors[rid] is None:
                item.mark_deadlock(False)

        for rid in new_deadlocks - self.deadlocked_regions:
            item = self.region_items.get(rid)
            if item:
                item.mark_deadlock(True)

        self.deadlocked_regions = new_deadlocks

        if new_deadlocks:
            ids = ", ".join(f"R{r}" for r in new_deadlocks)
            self.status_label.setText(f"⚠ Deadlock: {ids}")
            self.status_label.setStyleSheet("color:#ff4444; font-weight:bold;")
            self.log(f"⚠ Deadlock on: {ids}", "#ff4444")
        else:
            self.status_label.setText("✓ No deadlocks")
            self.status_label.setStyleSheet("color:#22c55e;")

        return new_deadlocks

    # ══════════════════════════════════════════
    #  HUMAN MOVE
    # ══════════════════════════════════════════
    def handle_region_click(self, rid):
        if self._animating or self.auto_play_active:
            return
        if self.selected_color is None:
            return
        if self.region_colors.get(rid) is not None:
            return

        neighbor_colors = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if self.region_colors[nb]
        }

        color_name = COLOR_NAMES[COLORS.index(self.selected_color)]

        if self.selected_color not in neighbor_colors:
            self.apply_color(rid, self.selected_color, player="HUMAN")
            self.human_score += 1
            self.log(f"👤 Human colored R{rid} → {color_name}", "#88ccff")
        else:
            self.human_score -= 1
            self.log(f"❌ Invalid move on R{rid} (−1 point)", "#ff6666")
            self.status_label.setText("Invalid move! −1 point")
            self.status_label.setStyleSheet("color:#ff4444;")

        self.update_score()
        self.detect_deadlocks()
        QTimer.singleShot(400, self.cpu_turn)
        self.check_game_complete()

    # ══════════════════════════════════════════
    #  CPU TURN
    #  Uses the pre-built in-order queue to pick
    #  the next target region.  Queue was built in
    #  _build_inorder_queue() after map generation.
    #
    #  Picking order mirrors in-order binary tree:
    #    left-leaf → left-root → right-leaf →
    #    parent-root → ...
    # ══════════════════════════════════════════
    def cpu_turn(self):
        if self._animating:
            return

        self._cpu_start_time = time.perf_counter()

        # ── Pop next target from in-order queue ──
        # Skip already-colored regions (human may have
        # colored some, or backtrack colored them early).
        target = None
        while self._inorder_queue:
            candidate = self._inorder_queue.pop(0)
            if self.region_colors.get(candidate) is None:
                target = candidate
                break

        if target is None:
            # Queue empty — check if truly done
            uncolored = [rid for rid, c in self.region_colors.items() if c is None]
            if uncolored:
                # Fallback: re-build queue for remaining regions
                self.log("🔄 Queue exhausted, rebuilding for remaining regions…", "#aaa")
                self._build_inorder_queue(uncolored)
                self._finish_cpu_turn()
                return
            self.check_game_complete()
            return

        self.log("─" * 36, "#333")

        # Show which node in the in-order sequence we're at
        remaining = len([r for r in self._inorder_queue
                         if self.region_colors.get(r) is None])
        self.log(
            f"🌲 dc pick: R{target}  (queue remaining: {remaining})",
            "#facc15"
        )

        # Highlight target
        item = self.region_items.get(target)
        if item:
            item.highlight_target()

        self.log(f"🎯 CONQUER → targeting R{target}", "#a78bfa")

        # CONQUER — greedy color it
        colored = self._greedy_color_region(target)

        if not colored:
            self.log(f"⚠ Greedy failed on R{target} → backtrack repair", "#ff4444")
            self.detect_deadlocks()
            self._run_animated_repair(
                [target],
                on_done=self._finish_cpu_turn
            )
            return

        # COMBINE — check boundary between left/right halves
        uncolored_rest = [r for r in self._inorder_queue
                          if self.region_colors.get(r) is None]
        if uncolored_rest:
            left, right   = self._divide(
                [target] + uncolored_rest
            )
            boundary = self._find_boundary(left, right)
            if boundary:
                self.log(
                    f"🔗 COMBINE → boundary: {[f'R{r}' for r in boundary]}",
                    "#facc15"
                )
                for br in boundary:
                    bitem = self.region_items.get(br)
                    if bitem and self.region_colors[br] is None:
                        bitem.highlight_boundary()

        self.detect_deadlocks()

        if self.deadlocked_regions:
            self.log("🔧 Boundary deadlock found → backtrack repair...", "#ff4444")
            self._run_animated_repair(
                list(self.deadlocked_regions),
                on_done=self._finish_cpu_turn
            )
        else:
            self._finish_cpu_turn()

    def _finish_cpu_turn(self):
        runtime = (time.perf_counter() - self._cpu_start_time) * 1000
        self.timer_label.setText(f"CPU Time: {runtime:.3f} ms")
        self.detect_deadlocks()
        self.update_score()
        self.check_game_complete()

        if self.auto_play_active:
            uncolored = [rid for rid, c in self.region_colors.items() if c is None]
            if uncolored:
                QTimer.singleShot(STEP_DELAY, self.cpu_turn)
            else:
                self._end_auto_play()
        else:
            self.log("✓ CPU done. Your move!", "#22c55e")

    # ══════════════════════════════════════════
    #  AUTO PLAY
    # ══════════════════════════════════════════
    def start_auto_play(self):
        if self._animating:
            return

        self.auto_play_active = True
        self.auto_btn.setText("⏹ Stop Auto Play")
        self.auto_btn.setStyleSheet(
            "background:#dc2626; color:white; height:38px;"
            "font-weight:bold; border-radius:5px; padding:0 14px;"
        )
        self.log("═" * 36, "#facc15")
        self.log("🤖 CPU AUTO PLAY STARTED", "#facc15")
        self.log("Watch: D&C → Divide → Conquer → Combine", "#aaa")
        self.log("═" * 36, "#facc15")

        QTimer.singleShot(500, self.cpu_turn)

    def stop_auto_play(self):
        self.auto_play_active = False
        self._anim_timer.stop()
        self._animating = False
        self.auto_btn.setText("▶ CPU Auto Play")
        self.auto_btn.setStyleSheet(
            "background:#7c3aed; color:white; height:38px;"
            "font-weight:bold; border-radius:5px; padding:0 14px;"
        )
        self.log("⏹ Auto play stopped.", "#aaa")

    def _end_auto_play(self):
        self.auto_play_active = False
        self.auto_btn.setText("▶ CPU Auto Play")
        self.auto_btn.setStyleSheet(
            "background:#7c3aed; color:white; height:38px;"
            "font-weight:bold; border-radius:5px; padding:0 14px;"
        )
        self.log("✅ Auto play complete!", "#22c55e")
        self.check_game_complete()

    def toggle_auto_play(self):
        if self.auto_play_active:
            self.stop_auto_play()
        else:
            self.reset_colors()
            QTimer.singleShot(300, self.start_auto_play)

    # ══════════════════════════════════════════
    #  DIVIDE
    # ══════════════════════════════════════════
    def _divide(self, region_list):
        if not region_list:
            return [], []
        centroids = [(rid, self.compute_centroid(rid)) for rid in region_list]
        x_values  = sorted(c[1][0] for c in centroids)
        median_x  = x_values[len(x_values) // 2]
        left  = [rid for rid, (x, y) in centroids if x < median_x]
        right = [rid for rid, (x, y) in centroids if x >= median_x]
        if not left:
            left  = right[:len(right) // 2]
            right = right[len(right) // 2:]
        return left, right

    # ══════════════════════════════════════════
    #  FIND BOUNDARY
    # ══════════════════════════════════════════
    def _find_boundary(self, left, right):
        left_set  = set(left)
        right_set = set(right)
        boundary  = set()
        for rid in left_set:
            for nb in self.adj_graph[rid]:
                if nb in right_set:
                    boundary.add(rid)
                    boundary.add(nb)
        return list(boundary)

    # ══════════════════════════════════════════
    #  GREEDY COLOR ONE REGION
    # ══════════════════════════════════════════
    def _greedy_color_region(self, rid):
        if self.region_colors[rid] is not None:
            return True
        neighbor_colors = {
            self.region_colors[nb]
            for nb in self.adj_graph[rid]
            if self.region_colors[nb]
        }
        for col in COLORS:
            if col not in neighbor_colors:
                self.region_colors[rid] = col
                item = self.region_items[rid]
                item.setBrush(QBrush(QColor(col)))
                item.setPen(QPen(QColor(col).lighter(150), 1))
                item.deadlocked = False
                self.deadlocked_regions.discard(rid)
                self.cpu_score += 1
                cname = COLOR_NAMES[COLORS.index(col)]
                self.log(f"⚡ GREEDY → R{rid} = {cname}", "#6ee7b7")
                return True
        self.log(f"  ⚠ R{rid} greedy failed", "#ff4444")
        return False

    # ══════════════════════════════════════════
    #  ANIMATED BACKTRACK REPAIR
    # ══════════════════════════════════════════
    def _run_animated_repair(self, stuck_list: list, on_done=None):
        steps = []
        for stuck_rid in stuck_list:
            if self.region_colors.get(stuck_rid) is not None:
                continue
            found = self._build_repair_steps(stuck_rid, steps, visited=set(), depth=0)
            if not found:
                self.log(f"  ⚠ Could not repair R{stuck_rid}", "#ff4444")

        if steps:
            self._queue_animation(steps, on_done=on_done)
        else:
            if on_done:
                on_done()

    def _build_repair_steps(self, stuck_rid, steps, visited, depth):
        visited.add(stuck_rid)

        def used_by_stuck():
            return {
                self.region_colors[nb]
                for nb in self.adj_graph[stuck_rid]
                if self.region_colors[nb] is not None
            }

        colored_neighbors = sorted(
            [nb for nb in self.adj_graph[stuck_rid]
             if self.region_colors[nb] is not None],
            key=lambda x: len(self.adj_graph[x]),
            reverse=True
        )

        for nb in colored_neighbors:
            if nb in visited:
                continue

            old_color = self.region_colors[nb]
            old_name  = COLOR_NAMES[COLORS.index(old_color)]

            nb_used = {
                self.region_colors[nn]
                for nn in self.adj_graph[nb]
                if nn != stuck_rid and self.region_colors[nn] is not None
            }
            alternatives = [c for c in COLORS
                            if c != old_color and c not in nb_used]

            for alt_color in alternatives:
                alt_name = COLOR_NAMES[COLORS.index(alt_color)]

                steps.append(
                    (lambda r=nb, sr=stuck_rid, on=old_name, an=alt_name:
                     self._step_consider(r, sr, on, an))
                )
                steps.append(
                    (lambda r=nb, ac=alt_color, an=alt_name, sr=stuck_rid:
                     self._step_try(r, ac, an, sr))
                )

                self.region_colors[nb] = alt_color

                if len(used_by_stuck()) < len(COLORS):
                    if not self._causes_new_deadlock(nb, alt_color):
                        free_color = next(
                            c for c in COLORS if c not in used_by_stuck()
                        )
                        free_name = COLOR_NAMES[COLORS.index(free_color)]

                        self.region_colors[nb]        = old_color
                        self.region_colors[stuck_rid] = None

                        steps.append(
                            (lambda r=nb, ac=alt_color, an=alt_name,
                                    sr=stuck_rid, fc=free_color, fn=free_name:
                             self._step_success(r, ac, an, sr, fc, fn))
                        )
                        return True

                self.region_colors[nb] = old_color

                steps.append(
                    (lambda r=nb, oc=old_color, on=old_name, an=alt_name:
                     self._step_undo(r, oc, on, an))
                )

                visited.add(nb)
                deeper = self._build_repair_steps(
                    stuck_rid, steps, visited, depth + 1
                )
                visited.discard(nb)
                if deeper:
                    return True

        return False

    # ── Animation step handlers ──

    def _step_consider(self, nb, stuck_rid, old_name, alt_name):
        item = self.region_items.get(nb)
        if item:
            item.highlight_considering()
            item.update()
        self.log(
            f"  🔍 Checking R{nb} ({old_name}) → try {alt_name}",
            "#facc15"
        )
        self.status_label.setText(f"Backtrack: checking R{nb}...")
        self.status_label.setStyleSheet("color:#facc15; font-weight:bold;")

    def _step_try(self, nb, alt_color, alt_name, stuck_rid):
        item = self.region_items.get(nb)
        if item:
            item.highlight_trying(alt_color)
            item.update()
        self.log(
            f"  🎨 Trying R{nb} = {alt_name} ... frees R{stuck_rid}?",
            "#a78bfa"
        )

    def _step_success(self, nb, alt_color, alt_name, stuck_rid, free_color, free_name):
        self.region_colors[nb] = alt_color
        item_nb = self.region_items.get(nb)
        if item_nb:
            item_nb.deadlocked = False
            item_nb.setBrush(QBrush(QColor(alt_color)))
            item_nb.setPen(QPen(QColor(alt_color).lighter(150), 1))
            item_nb.update()

        self.region_colors[stuck_rid] = free_color
        item_stuck = self.region_items.get(stuck_rid)
        if item_stuck:
            item_stuck.deadlocked = False
            item_stuck.setBrush(QBrush(QColor(free_color)))
            item_stuck.setPen(QPen(QColor(free_color).lighter(150), 1))
            item_stuck.update()

        self.deadlocked_regions.discard(nb)
        self.deadlocked_regions.discard(stuck_rid)
        self.cpu_score += 1
        self.update_score()

        if self.scene:
            self.scene.update()

        self.log(
            f"  ✅ R{nb} → {alt_name} | R{stuck_rid} → {free_name} [Repaired!]",
            "#22c55e"
        )
        self.status_label.setText(f"✓ R{stuck_rid} resolved!")
        self.status_label.setStyleSheet("color:#22c55e; font-weight:bold;")

    def _step_undo(self, nb, old_color, old_name, tried_name):
        item = self.region_items.get(nb)
        if item:
            item.highlight_undo(old_color)
            item.update()
        if self.scene:
            self.scene.update()
        self.log(
            f"  ↩ {tried_name} failed → restoring R{nb} → {old_name}",
            "#f87171"
        )

    # ══════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════
    def _causes_new_deadlock(self, changed_rid, new_color):
        for nb in self.adj_graph[changed_rid]:
            if self.region_colors[nb] is not None:
                continue
            nc = {
                self.region_colors[nn]
                for nn in self.adj_graph[nb]
                if self.region_colors[nn] is not None
            }
            if len(nc) == len(COLORS):
                return True
        return False

    def compute_centroid(self, rid):
        polygon = self.region_items[rid].polygon()
        x = sum(p.x() for p in polygon) / len(polygon)
        y = sum(p.y() for p in polygon) / len(polygon)
        return (x, y)

    # ══════════════════════════════════════════
    #  APPLY COLOR (human)
    # ══════════════════════════════════════════
    def apply_color(self, rid, color, player="CPU"):
        self.region_colors[rid] = color
        item = self.region_items[rid]
        item.setBrush(QBrush(QColor(color)))
        item.setPen(QPen(QColor(color).lighter(150), 1))
        item.deadlocked = False
        self.deadlocked_regions.discard(rid)
        if player == "CPU":
            self.cpu_score += 1

    # ══════════════════════════════════════════
    #  SCORE / STATUS
    # ══════════════════════════════════════════
    def update_score(self):
        self.score_label.setText(
            f"Human: {self.human_score}  |  CPU: {self.cpu_score}"
        )

    # ══════════════════════════════════════════
    #  RESET
    # ══════════════════════════════════════════
    def reset_colors(self):
        self._anim_timer.stop()
        self._animating       = False
        self.auto_play_active = False
        for rid in self.region_items:
            self.region_colors[rid] = None
            self.region_items[rid].mark_deadlock(False)
            self.region_items[rid]._reset_style()
        self.deadlocked_regions.clear()
        self.human_score = 0
        self.cpu_score   = 0
        self.update_score()
        self.status_label.setText("✓ No deadlocks")
        self.status_label.setStyleSheet("color:#22c55e;")
        self.auto_btn.setText("▶ CPU Auto Play")
        self.auto_btn.setStyleSheet(
            "background:#7c3aed; color:white; height:38px;"
            "font-weight:bold; border-radius:5px; padding:0 14px;"
        )
        # Rebuild in-order queue for fresh game
        self._build_inorder_queue()
        self.log_clear()
        self.log("🔄 Map reset. rebuilt.", "#aaa")

    # ══════════════════════════════════════════
    #  GAME COMPLETE
    # ══════════════════════════════════════════
    def check_game_complete(self):
        if any(c is None for c in self.region_colors.values()):
            return
        if self.human_score > self.cpu_score:
            winner = "🏆 Human Wins!"
        elif self.cpu_score > self.human_score:
            winner = "🤖 CPU Wins!"
        else:
            winner = "🤝 It's a Tie!"
        self.log(f"\n{winner}  Human:{self.human_score}  CPU:{self.cpu_score}", "#facc15")
        if not self.auto_play_active:
            msg = QMessageBox(self)
            msg.setWindowTitle("Game Over")
            msg.setText(winner)
            msg.setInformativeText(
                f"Final Score\nHuman: {self.human_score}\nCPU: {self.cpu_score}"
            )
            msg.exec()

    # ══════════════════════════════════════════
    #  COLOR SELECT
    # ══════════════════════════════════════════
    def select_color(self, color):
        self.selected_color = color
        idx = COLORS.index(color)
        self.selected_label.setText(f"Selected: {COLOR_NAMES[idx]}")
        self.selected_label.setStyleSheet(
            f"color:{color}; font-weight:bold; font-size:13px;"
        )

    # ══════════════════════════════════════════
    #  D&C STEP VISUALIZATION
    # ══════════════════════════════════════════
    def prepare_dc_steps(self):
        self.dc_steps = []

        def collect(node_list):
            if len(node_list) <= 1:
                return
            centroids = [(rid, self.compute_centroid(rid)) for rid in node_list]
            xs        = sorted(c[1][0] for c in centroids)
            median_x  = xs[len(xs) // 2]
            self.dc_steps.append(median_x)
            left  = [rid for rid, (x, y) in centroids if x < median_x]
            right = [rid for rid, (x, y) in centroids if x >= median_x]
            collect(left)
            collect(right)

        collect(list(self.region_items.keys()))

    def show_next_dc_step(self):
        if self.current_step >= len(self.dc_steps):
            return
        x = self.dc_steps[self.current_step]
        line = QGraphicsLineItem(x, 0, x, 600)
        line.setPen(QPen(QColor("#facc15"), 2, Qt.PenStyle.DashLine))
        self.scene.addItem(line)
        self.log(f"📐 D&C split at X = {x:.1f}", "#facc15")
        self.current_step += 1

    # ══════════════════════════════════════════
    #  MAP GENERATION
    # ══════════════════════════════════════════
    def new_game(self):
        self._anim_timer.stop()
        self._animating       = False
        self.auto_play_active = False
        self.scene.clear()
        self.adj_graph          = {}
        self.region_colors      = {}
        self.region_items       = {}
        self.deadlocked_regions = set()
        self._inorder_queue     = []
        self.human_score        = 0
        self.cpu_score          = 0
        self.update_score()
        self.status_label.setText("✓ No deadlocks")
        self.status_label.setStyleSheet("color:#22c55e;")
        self.log_clear()
        self.log("🗺 New map generated.", "#aaa")

        width, height = 800, 600
        points = [
            [random.uniform(50, width - 50), random.uniform(50, height - 50)]
            for _ in range(self.region_count)
        ]
        points.extend([
            [-1000, -1000], [2000, -1000],
            [-1000,  2000], [2000,  2000]
        ])

        vor       = Voronoi(points)
        clip_rect = QRectF(0, 0, width, height)
        rid       = 0

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
                self.region_items[rid]  = item
                self.region_colors[rid] = None
                self.adj_graph[rid]     = set()

                center = item.boundingRect().center()
                text   = QGraphicsTextItem(str(rid))
                text.setDefaultTextColor(QColor("white"))
                text.setFont(QFont("Arial", 8, QFont.Weight.Bold))
                text.setPos(center)
                self.scene.addItem(text)
                rid += 1

        for id1, item1 in self.region_items.items():
            for id2, item2 in self.region_items.items():
                if id1 >= id2:
                    continue
                p1 = {(round(v.x(), 0), round(v.y(), 0)) for v in item1.polygon()}
                p2 = {(round(v.x(), 0), round(v.y(), 0)) for v in item2.polygon()}
                if len(p1 & p2) >= 2:
                    self.adj_graph[id1].add(id2)
                    self.adj_graph[id2].add(id1)

        self.prepare_dc_steps()
        self.current_step = 0
        self.scene.setSceneRect(clip_rect)
        self.view.fitInView(clip_rect, Qt.AspectRatioMode.KeepAspectRatio)

        # ── Build in-order queue after map is ready ──
        self._build_inorder_queue()
        self.log(
            f"🌲 D&C ready ({len(self._inorder_queue)} regions)",
            "#22c55e"
        )

    # ══════════════════════════════════════════
    #  SOLVERS (menu)
    # ══════════════════════════════════════════
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
                if all(self.region_colors[nb] != col
                       for nb in self.adj_graph[node]):
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
                n    = node_list[0]
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

    # ══════════════════════════════════════════
    #  MENU
    # ══════════════════════════════════════════
    def create_menu(self):
        menubar = self.menuBar()

        map_menu = menubar.addMenu("Map")
        map_menu.addAction("Generate New Map", self.new_game)

        comp_menu = menubar.addMenu("Complexity")
        for label, count in [("Easy (15)", 15), ("Medium (25)", 25), ("Hard (50)", 50)]:
            act = QAction(label, self)
            act.triggered.connect(lambda chk, c=count: self.set_complexity(c))
            comp_menu.addAction(act)

        solve_menu = menubar.addMenu("Solve")
        solve_menu.addAction("Greedy",           self.solve_greedy)
        solve_menu.addAction("Divide & Conquer", self.solve_divide_and_conquer)
        solve_menu.addAction("Backtracking",     self.solve_backtracking)

    def set_complexity(self, count):
        self.region_count = count
        self.new_game()

    # ══════════════════════════════════════════
    #  UI LAYOUT
    # ══════════════════════════════════════════
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(4)

        # Top bar
        top = QHBoxLayout()
        self.timer_label = QLabel("CPU Time: 0.000 ms")
        self.timer_label.setStyleSheet("color:#aaa; font-size:12px;")
        top.addWidget(self.timer_label)
        top.addStretch()
        self.status_label = QLabel("✓ No deadlocks")
        self.status_label.setStyleSheet("color:#22c55e; font-size:12px;")
        top.addWidget(self.status_label)
        main_layout.addLayout(top)

        # Map + Log
        mid = QHBoxLayout()

        self.scene = QGraphicsScene()
        self.view  = ZoomableGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setStyleSheet("background:#0a1628; border:1px solid #1e3a5f;")
        mid.addWidget(self.view, stretch=3)

        # Log panel
        log_layout = QVBoxLayout()
        log_title  = QLabel("📋 Algorithm Log")
        log_title.setStyleSheet("color:white; font-weight:bold; font-size:13px;")
        log_layout.addWidget(log_title)

        self.log_panel = QTextEdit()
        self.log_panel.setReadOnly(True)
        self.log_panel.setStyleSheet(
            "background:#0d1117; color:white; font-size:11px;"
            "border:1px solid #1e3a5f; border-radius:4px;"
        )
        self.log_panel.setMinimumWidth(280)
        self.log_panel.setMaximumWidth(320)
        log_layout.addWidget(self.log_panel)

        # Legend
        legend_title = QLabel("Legend")
        legend_title.setStyleSheet("color:#aaa; font-size:11px; margin-top:6px;")
        log_layout.addWidget(legend_title)

        for symbol, text, color in [
            ("⬛", "Uncolored",               "#aaa"),
            ("⬜", "CPU targeting (white)",   "#ffffff"),
            ("🟧", "Boundary region",         "#ff6600"),
            ("🟥", "Deadlocked (all 4 used)", "#ff4444"),
            ("🟨", "Backtrack: considering",  "#facc15"),
            ("🟪", "Backtrack: trying",       "#a78bfa"),
            ("🟫", "Backtrack: undo",         "#f87171"),
            ("🟩", "Repaired",                "#22c55e"),
        ]:
            lbl = QLabel(f"{symbol} {text}")
            lbl.setStyleSheet(f"color:{color}; font-size:10px;")
            log_layout.addWidget(lbl)

        mid.addLayout(log_layout)
        main_layout.addLayout(mid)

        # Bottom bar
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.score_label = QLabel("Human: 0  |  CPU: 0")
        self.score_label.setStyleSheet(
            "font-size:14px; font-weight:bold; color:white;"
        )
        bottom.addWidget(self.score_label)
        bottom.addStretch()

        for i, c in enumerate(COLORS):
            btn = QPushButton(COLOR_NAMES[i])
            btn.setStyleSheet(
                f"background:{c}; color:white; height:38px;"
                f"font-weight:bold; border-radius:5px; padding:0 14px;"
            )
            btn.clicked.connect(lambda _, col=c: self.select_color(col))
            bottom.addWidget(btn)

        self.selected_label = QLabel("Selected: None")
        self.selected_label.setStyleSheet("color:#aaa; font-size:12px;")
        bottom.addWidget(self.selected_label)

        bottom.addStretch()

        self.auto_btn = QPushButton("▶ CPU Auto Play")
        self.auto_btn.setStyleSheet(
            "background:#7c3aed; color:white; height:38px;"
            "font-weight:bold; border-radius:5px; padding:0 14px;"
        )
        self.auto_btn.clicked.connect(self.toggle_auto_play)
        bottom.addWidget(self.auto_btn)

        reset_btn = QPushButton("Reset Map")
        reset_btn.setStyleSheet(
            "background:#374151; color:white; height:38px;"
            "border-radius:5px; padding:0 14px;"
        )
        reset_btn.clicked.connect(self.reset_colors)
        bottom.addWidget(reset_btn)

        step_btn = QPushButton("Next D&C Step")
        step_btn.setStyleSheet(
            "background:#1d4ed8; color:white; height:38px;"
            "border-radius:5px; padding:0 14px;"
        )
        step_btn.clicked.connect(self.show_next_dc_step)
        bottom.addWidget(step_btn)

        main_layout.addLayout(bottom)


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,        QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.WindowText,    QColor("white"))
    palette.setColor(QPalette.ColorRole.Base,          QColor("#161b22"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#0d1117"))
    palette.setColor(QPalette.ColorRole.Text,          QColor("white"))
    palette.setColor(QPalette.ColorRole.Button,        QColor("#21262d"))
    palette.setColor(QPalette.ColorRole.ButtonText,    QColor("white"))
    app.setPalette(palette)

    window = MapColoringGame()
    window.show()
    sys.exit(app.exec())
