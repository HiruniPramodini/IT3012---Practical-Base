import random
import tkinter as tk


class VisualGridHuntGame:


    #---------------------LAB-02-1.1------------------------

    

    # Clockwise turn order used for turn_left / turn_right
    TURN_ORDER = ['Up', 'Right', 'Down', 'Left']
    DIRECTION_DELTAS = {
        'Up': (0, 1),
        'Down': (0, -1),
        'Left': (-1, 0),
        'Right': (1, 0),
    }

    def __init__(self, width=10, height=10, num_food=10, num_opponents=2, num_traps=4, custom_walls=None):
        self.width = width
        self.height = height
        self.agent_pos = [0, 0]  # Starting position (x, y)

        #---------------------LAB-02-1.1------------------------
        self.direction = "Right"

        if custom_walls is not None:
            self.walls = set(custom_walls)
        else:
            # Generate some default scattered walls for a larger grid
            self.walls = {(2, 2), (2, 3), (5, 5), (6, 5), (3, 7)}

        # Dynamically generate random food positions avoiding walls and agent start
        self.food_positions = set()
        while len(self.food_positions) < num_food:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            pos_tuple = (fx, fy)
            if pos_tuple != (0, 0) and pos_tuple not in self.walls:
                self.food_positions.add(pos_tuple)

        # Generate adversarial opponents
        self.opponents = []
        while len(self.opponents) < num_opponents:
            ox = random.randint(0, self.width - 1)
            oy = random.randint(0, self.height - 1)
            op_pos = [ox, oy]
            if tuple(op_pos) != (0, 0) and tuple(op_pos) not in self.walls and tuple(op_pos) not in self.food_positions:
                self.opponents.append(op_pos)

        #---------------------Step 2.1------------------------
        self.score = 0
        self.steps = 0
        self.collision = False

        self.toxic_traps = set()
        while len(self.toxic_traps) < num_traps:
            tx = random.randint(0, self.width - 1)
            ty = random.randint(0, self.height - 1)
            pos_tuple = (tx, ty)
            if (pos_tuple != (0, 0)
                    and pos_tuple not in self.walls
                    and pos_tuple not in self.food_positions
                    and pos_tuple not in [tuple(op) for op in self.opponents]):
                self.toxic_traps.add(pos_tuple)

    # ------------------------------------------------------------------
    # Helpers for direction-relative movement
    # ------------------------------------------------------------------
    def _rotate(self, direction, way):
        idx = self.TURN_ORDER.index(direction)
        if way == 'left':
            return self.TURN_ORDER[(idx - 1) % 4]
        return self.TURN_ORDER[(idx + 1) % 4]

    def _cell_ahead(self):
        dx, dy = self.DIRECTION_DELTAS[self.direction]
        return (self.agent_pos[0] + dx, self.agent_pos[1] + dy)

    # ------------------------------------------------------------------
    # Step 1.1: Partial Observability
    # ------------------------------------------------------------------
    def get_percept(self) -> dict:
        """Local-only percept. No more `agent_pos` / global coordinates —
        the agent can only sense what's directly in front of it and what
        it's currently standing on, plus feedback signals (score/steps)."""
        ahead = self._cell_ahead()
        within_bounds = 0 <= ahead[0] < self.width and 0 <= ahead[1] < self.height
        wall_ahead = (not within_bounds) or (ahead in self.walls)

        current = tuple(self.agent_pos)

        return {
            'direction': self.direction,          # proprioception: agent knows its own facing, not its location
            'wall_ahead': wall_ahead,
            'food_here': current in self.food_positions,
            'toxin_here': current in self.toxic_traps,
            'collision': self.collision,
            'score': self.score,
            'remaining_food': len(self.food_positions),
        }

    # ------------------------------------------------------------------
    # Action execution — now relative to the agent's facing direction
    # ------------------------------------------------------------------
    def execute_action(self, action: str):
        self.steps += 1

        if action == 'turn_left':
            self.direction = self._rotate(self.direction, 'left')

        elif action == 'turn_right':
            self.direction = self._rotate(self.direction, 'right')

        elif action == 'suck':
            pos = tuple(self.agent_pos)
            if pos in self.food_positions:
                self.food_positions.remove(pos)
                self.score += 20

        elif action == 'move_forward':
            new_pos = list(self._cell_ahead())
            new_pos[0] = max(0, min(self.width - 1, new_pos[0]))
            new_pos[1] = max(0, min(self.height - 1, new_pos[1]))

            if tuple(new_pos) in self.walls:
                # Bumping a wall: penalize, agent stays where it was
                self.score -= 5
            elif tuple(new_pos) in self.toxic_traps:
                #-------------------Step 2.3-----------------------
                # Stepping on a trap: penalize, but the agent still moves there
                self.score -= 15
                self.agent_pos = new_pos
            else:
                self.agent_pos = new_pos

        # Opponents move randomly, as before
        for op in self.opponents:
            move = random.choice(['Up', 'Down', 'Left', 'Right', 'Stay'])
            if move == 'Up' and op[1] < self.height - 1:
                op[1] += 1
            elif move == 'Down' and op[1] > 0:
                op[1] -= 1
            elif move == 'Left' and op[0] > 0:
                op[0] -= 1
            elif move == 'Right' and op[0] < self.width - 1:
                op[0] += 1

            if op == self.agent_pos:
                self.score -= 50
                self.collision = True

    def is_done(self) -> bool:
        return len(self.food_positions) == 0 or self.steps >= 60 or self.collision


# ==========================================================================
# Step 1.2: Simple Reflex Agent
# ==========================================================================
class SimpleReflexAgent:
   
    def sense_and_act(self, percept: dict) -> str:
        # --- Condition-Action Rules ---
        if percept['food_here']:
            return 'suck'
        if percept['wall_ahead']:
            return 'turn_left'
        return 'move_forward'


# ==========================================================================
# Step 1.3: Model-Based Agent
# ==========================================================================
class ModelBasedAgent:
   

    TURN_ORDER = ['Up', 'Right', 'Down', 'Left']
    DIRECTION_DELTAS = {
        'Up': (0, 1),
        'Down': (0, -1),
        'Left': (-1, 0),
        'Right': (1, 0),
    }

    def __init__(self):
        # Internal memory state — this is what a Simple Reflex Agent lacks.
        self.internal_pos = (0, 0)          # agent's own estimate of its position
        self.internal_direction = 'Right'   # agent's own estimate of its facing
        self.visited_cells = {(0, 0)}       # memory of where it has already been
        self.last_action = None

    def _rotate(self, direction, way):
        idx = self.TURN_ORDER.index(direction)
        if way == 'left':
            return self.TURN_ORDER[(idx - 1) % 4]
        return self.TURN_ORDER[(idx + 1) % 4]

    def _update_state(self, action: str):
      
        if action == 'move_forward':
            dx, dy = self.DIRECTION_DELTAS[self.internal_direction]
            self.internal_pos = (self.internal_pos[0] + dx, self.internal_pos[1] + dy)
        elif action == 'turn_left':
            self.internal_direction = self._rotate(self.internal_direction, 'left')
        elif action == 'turn_right':
            self.internal_direction = self._rotate(self.internal_direction, 'right')
        self.visited_cells.add(self.internal_pos)

    def sense_and_act(self, percept: dict) -> str:
        # --- Sensor Model: fold the effect of our last action into memory ---
        if self.last_action is not None:
            self._update_state(self.last_action)

        dx, dy = self.DIRECTION_DELTAS[self.internal_direction]
        ahead_cell = (self.internal_pos[0] + dx, self.internal_pos[1] + dy)

        left_dir = self._rotate(self.internal_direction, 'left')
        ldx, ldy = self.DIRECTION_DELTAS[left_dir]
        left_cell = (self.internal_pos[0] + ldx, self.internal_pos[1] + ldy)

        right_dir = self._rotate(self.internal_direction, 'right')
        rdx, rdy = self.DIRECTION_DELTAS[right_dir]
        right_cell = (self.internal_pos[0] + rdx, self.internal_pos[1] + rdy)

        # --- Condition-Action rules, now querying memory ---
        if percept['food_here']:
            action = 'suck'
        elif percept['wall_ahead']:
            # IF wall_ahead AND left_is_visited THEN turn_right ELSE turn_left
            if left_cell in self.visited_cells:
                action = 'turn_right'
            else:
                action = 'turn_left'
        elif ahead_cell not in self.visited_cells:
            action = 'move_forward'
        elif left_cell not in self.visited_cells:
            # Ahead is old ground, but the left looks unexplored — try it.
            action = 'turn_left'
        elif right_cell not in self.visited_cells:
            action = 'turn_right'
        else:
            # Everywhere nearby is already visited (fully explored pocket) —
            # push forward anyway rather than spin turns forever.
            action = 'move_forward'

        self.last_action = action
        return action


class GridGameGUI:
    """Tkinter wrapper that dynamically scales cell sizes to keep larger grids on screen."""

    def __init__(self, root, width=10, height=10, num_food=12, num_opponents=2, num_traps=4, walls=None):
        self.root = root
        self.root.title("IT3012 - Scalable Multi-Agent Grid Hunt")

        self._env_kwargs = dict(width=width, height=height, num_food=num_food,
                                 num_opponents=num_opponents, num_traps=num_traps, custom_walls=walls)
        self.env = VisualGridHuntGame(**self._env_kwargs)
        self.agent = None

        # Dynamically calculate cell size so the total canvas fits nicely within a 600x600 window ceiling
        max_canvas_dim = 600
        self.cell_size = max(20, min(max_canvas_dim // self.env.width, max_canvas_dim // self.env.height))

        canvas_w = self.env.width * self.cell_size
        canvas_h = self.env.height * self.cell_size

        self.canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, bg="white")
        self.canvas.pack()

        self.label = tk.Label(root, text="Score: 0 | Steps: 0", font=("Arial", 14))
        self.label.pack(pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)

        self.btn_simple = tk.Button(btn_frame, text="Run Simple Reflex Agent",
                                     command=lambda: self.start_run(SimpleReflexAgent()),
                                     font=("Arial", 12), bg="#7a0000", fg="white")
        self.btn_simple.grid(row=0, column=0, padx=5)

        self.btn_model = tk.Button(btn_frame, text="Run Model-Based Agent",
                                    command=lambda: self.start_run(ModelBasedAgent()),
                                    font=("Arial", 12), bg="#000066", fg="white")
        self.btn_model.grid(row=0, column=1, padx=5)

        self.draw_grid()

    def reset_env(self):
        self.env = VisualGridHuntGame(**self._env_kwargs)

    def draw_grid(self):
        self.canvas.delete("all")

        for x in range(self.env.width):
            for y in range(self.env.height):
                x1 = x * self.cell_size
                y1 = (self.env.height - 1 - y) * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                is_wall = (x, y) in self.env.walls
                is_trap = (x, y) in self.env.toxic_traps

                if is_wall:
                    color = "#64748b"
                elif is_trap:
                    color = "#7c3aed22"  # light purple tint for traps
                else:
                    color = "#f1f5f9"

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#cbd5e1")

                # Only draw text if cell is large enough
                if self.cell_size >= 40:
                    if is_wall:
                        self.canvas.create_text(x1 + self.cell_size / 2, y1 + self.cell_size / 2, text="W",
                                                fill="white", font=("Arial", 8, "bold"))
                    #-------------------Step 2.3-----------------------
                    elif is_trap:
                        self.canvas.create_text(x1 + self.cell_size / 2, y1 + self.cell_size / 2, text="T",
                                                fill="purple", font=("Arial", 8, "bold"))

        for fx, fy in self.env.food_positions:
            offset = self.cell_size * 0.25
            x1 = fx * self.cell_size + offset
            y1 = (self.env.height - 1 - fy) * self.cell_size + offset
            self.canvas.create_oval(x1, y1, x1 + self.cell_size * 0.5, y1 + self.cell_size * 0.5, fill="#f59e0b",
                                    outline="#d97706")

        for ox, oy in self.env.opponents:
            offset = self.cell_size * 0.2
            x1 = ox * self.cell_size + offset
            y1 = (self.env.height - 1 - oy) * self.cell_size + offset
            self.canvas.create_rectangle(x1, y1, x1 + self.cell_size * 0.6, y1 + self.cell_size * 0.6, fill="#990000",
                                         outline="#7a0000")

        ax, ay = self.env.agent_pos
        offset = self.cell_size * 0.15
        x1 = ax * self.cell_size + offset
        y1 = (self.env.height - 1 - ay) * self.cell_size + offset
        x2 = x1 + self.cell_size * 0.7
        y2 = y1 + self.cell_size * 0.7
        self.canvas.create_oval(x1, y1, x2, y2, fill="#000066", outline="#1e3a8a")

        # Draw a small facing-direction indicator so you can see the agent turn
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = self.env.DIRECTION_DELTAS[self.env.direction]
        tip_x = cx + dx * self.cell_size * 0.35
        tip_y = cy - dy * self.cell_size * 0.35  # canvas y is flipped
        self.canvas.create_line(cx, cy, tip_x, tip_y, fill="#ffffff", width=3)

    def start_run(self, agent):
        self.reset_env()
        self.agent = agent
        self.btn_simple.config(state="disabled")
        self.btn_model.config(state="disabled")
        self.draw_grid()
        self.run_loop()

    def run_loop(self):
        def step():
            if not self.env.is_done():
                percept = self.env.get_percept()
                action = self.agent.sense_and_act(percept)
                self.env.execute_action(action)

                self.draw_grid()
                self.label.config(
                    text=f"Score: {self.env.score} | Steps: {self.env.steps} | "
                         f"Action: {action} | Facing: {self.env.direction}"
                )
                self.root.after(250, step)
            else:
                end_text = (f"Collision! Game Over! Final Score: {self.env.score}" if self.env.collision
                            else f"Finished! Final Score: {self.env.score}")
                self.label.config(text=end_text)
                self.btn_simple.config(state="normal")
                self.btn_model.config(state="normal")

        step()


if __name__ == "__main__":
    root = tk.Tk()
    # Try a larger grid size like 12x12 with 15 food and 3 opponents!
    app = GridGameGUI(root, width=12, height=12, num_food=15, num_opponents=0, num_traps=4)
    root.mainloop()