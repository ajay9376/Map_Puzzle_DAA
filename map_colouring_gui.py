import tkinter as tk
from tkinter import messagebox

# -------------------------------------------------
# MAP COLORING GAME – REVIEW 1 (FINAL VERSION)
# Player 1: Human (own logic)
# Player 2: Computer (Greedy Algorithm)
# Penalty for invalid human moves
# -------------------------------------------------

# -------- GRAPH (4x4 GRID) --------
graph = {
    0: [1, 4],
    1: [0, 2, 5],
    2: [1, 3, 6],
    3: [2, 7],
    4: [0, 5, 8],
    5: [1, 4, 6, 9],
    6: [2, 5, 7, 10],
    7: [3, 6, 11],
    8: [4, 9, 12],
    9: [5, 8, 10, 13],
    10: [6, 9, 11, 14],
    11: [7, 10, 15],
    12: [8, 13],
    13: [9, 12, 14],
    14: [10, 13, 15],
    15: [11, 14]
}

color_map = {
    "RED": "red",
    "GREEN": "green",
    "BLUE": "blue",
    "YELLOW": "yellow"
}

# -------- GAME STATE --------
colors = {}
selected_color = None
human_score = 0
cpu_score = 0
game_over = False

# -------- VALID MOVE CHECK --------
def is_valid(region, color):
    return all(colors[n] != color for n in graph[region])

# -------- CPU GREEDY MOVE --------
def cpu_move():
    global cpu_score
    for r in range(16):
        if colors[r] is None:
            used = {colors[n] for n in graph[r] if colors[n]}
            for c in color_map.values():
                if c not in used:
                    colors[r] = c
                    buttons[r].config(bg=c)
                    cpu_score += 1
                    break
            break
    update_status()
    check_game_over()

# -------- HUMAN MOVE --------
def human_move(region):
    global human_score

    if game_over:
        return

    if selected_color is None:
        status_label.config(text="Select a color first!", fg="red")
        return

    if colors[region] is not None:
        status_label.config(text="Region already colored! (-1)", fg="red")
        human_score -= 1
        update_status()
        return

    if not is_valid(region, selected_color):
        status_label.config(text="Invalid move! Penalty applied (-1)", fg="red")
        human_score -= 1
        update_status()
        return

    # Valid human move
    colors[region] = selected_color
    buttons[region].config(bg=selected_color)
    human_score += 1
    status_label.config(text="Computer's turn...", fg="blue")
    update_status()

    root.after(400, cpu_move)

# -------- STATUS UPDATE --------
def update_status():
    score_label.config(
        text=f"Human Score: {human_score}    Computer Score: {cpu_score}"
    )

# -------- CHECK GAME OVER --------
def check_game_over():
    global game_over
    if all(colors[r] is not None for r in colors):
        game_over = True
        winner = "Human" if human_score >= cpu_score else "Computer"
        messagebox.showinfo(
            "Game Over",
            f"All regions are colored!\n\n"
            f"Human Score: {human_score}\n"
            f"Computer Score: {cpu_score}\n\n"
            f"Winner: {winner}"
        )

# -------- COLOR SELECTION --------
def choose_color(c):
    global selected_color
    selected_color = c
    status_label.config(text=f"Selected Color: {c.upper()}", fg=c)

# -------- RESET GAME --------
def reset_game():
    global colors, selected_color, human_score, cpu_score, game_over
    colors = {i: None for i in range(16)}
    selected_color = None
    human_score = 0
    cpu_score = 0
    game_over = False
    status_label.config(text="Select a color and click a region", fg="black")
    score_label.config(text="Human Score: 0    Computer Score: 0")
    for btn in buttons.values():
        btn.config(bg="white")

# -------- GUI SETUP --------
root = tk.Tk()
root.title("Map Coloring Game – Review 1")
root.geometry("440x560")
root.resizable(False, False)

tk.Label(
    root,
    text="Map Coloring Game",
    font=("Arial", 16, "bold")
).pack(pady=5)

tk.Label(
    root,
    text="Human vs Computer (Greedy Algorithm)",
    font=("Arial", 11)
).pack()

status_label = tk.Label(
    root,
    text="Select a color and click a region",
    font=("Arial", 10)
)
status_label.pack(pady=6)

score_label = tk.Label(
    root,
    text="Human Score: 0    Computer Score: 0",
    font=("Arial", 11, "bold")
)
score_label.pack(pady=4)

# -------- GRID --------
grid_frame = tk.Frame(root)
grid_frame.pack(pady=5)

buttons = {}
reset_game()

for i in range(16):
    btn = tk.Button(
        grid_frame,
        text=str(i),
        width=6,
        height=3,
        bg="white",
        font=("Arial", 10, "bold"),
        command=lambda r=i: human_move(r)
    )
    btn.grid(row=i // 4, column=i % 4, padx=4, pady=4)
    buttons[i] = btn

# -------- COLOR BUTTONS --------
color_frame = tk.Frame(root)
color_frame.pack(pady=10)

for name, clr in color_map.items():
    tk.Button(
        color_frame,
        text=name,
        bg=clr,
        fg="white",
        width=9,
        font=("Arial", 10, "bold"),
        command=lambda c=clr: choose_color(c)
    ).pack(side=tk.LEFT, padx=5)

# -------- RESTART BUTTON --------
tk.Button(
    root,
    text="Restart Game",
    font=("Arial", 11, "bold"),
    bg="#444",
    fg="white",
    width=22,
    command=reset_game
).pack(pady=12)

root.mainloop()
