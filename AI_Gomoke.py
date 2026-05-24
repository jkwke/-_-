import tkinter as tk
from tkinter import messagebox
import math
import random
import concurrent.futures
import os


class MCTSNode:
    """蒙特卡洛树搜索节点"""

    def __init__(self, board_state, parent=None, move=None, player=1):
        self.board_state = [row[:] for row in board_state]
        self.parent = parent
        self.move = move  # 导致这个状态的移动
        self.player = player  # 当前玩家
        self.children = []
        self.wins = 0
        self.visits = 0
        self.untried_moves = self._get_all_moves()

    def _get_all_moves(self):
        """获取所有可用的移动位置（仅考虑已有棋子附近的空位）"""
        board_size = len(self.board_state)

        has_stone = any(
            self.board_state[r][c] != 0
            for r in range(board_size)
            for c in range(board_size)
        )

        if not has_stone:
            center = board_size // 2
            return [(center, center)]

        moves = set()
        for row in range(board_size):
            for col in range(board_size):
                if self.board_state[row][col] != 0:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            r, c = row + dr, col + dc
                            if 0 <= r < board_size and 0 <= c < board_size:
                                if self.board_state[r][c] == 0:
                                    moves.add((r, c))
        return list(moves)

    def is_terminal(self):
        """检查是否是终止状态"""
        if self.parent:
            last_move = self.move
            if last_move and self._check_win(last_move[0], last_move[1]):
                return True
        return len(self.untried_moves) == 0

    def _check_win(self, row, col):
        """检查是否在(row, col)位置形成五连珠"""
        board_size = len(self.board_state)
        current_player = self.board_state[row][col]
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and self.board_state[r][c] == current_player:
                count += 1
                r += dr
                c += dc

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and self.board_state[r][c] == current_player:
                count += 1
                r -= dr
                c -= dc

            if count >= 5:
                return True
        return False

    def get_result(self, original_player):
        """获取游戏结果（相对于原始玩家的视角）"""
        if not self.parent or not self.move:
            return 0

        winner = None
        last_move = self.move
        board_size = len(self.board_state)

        for player in [1, 2]:
            if self._check_win_with_player(last_move[0], last_move[1], player):
                winner = player
                break

        if winner is None:
            return 0

        if winner == original_player:
            return 1
        else:
            return -1

    def _check_win_with_player(self, row, col, player):
        """检查指定玩家是否在(row, col)位置获胜"""
        board_size = len(self.board_state)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and self.board_state[r][c] == player:
                count += 1
                r += dr
                c += dc

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and self.board_state[r][c] == player:
                count += 1
                r -= dr
                c -= dc

            if count >= 5:
                return True
        return False

    def uct_score(self, exploration_constant=1.414):
        """计算UCT分数"""
        if self.visits == 0:
            return float('inf')
        exploitation = self.wins / self.visits
        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration


class BoardEvaluator:
    """棋盘评估器 - 识别各种棋型并评分"""

    SCORES = {
        'FIVE': 100000,
        'FOUR': 10000,
        'BLOCKED_FOUR': 5000,
        'THREE': 1000,
        'BLOCKED_THREE': 700,
        'TWO': 500,
        'BLOCKED_TWO': 250,
    }

    @staticmethod
    def evaluate_position(board, row, col, player):
        """评估某个位置的分数"""
        board_size = len(board)
        total_score = 0
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            blocked_end = 0

            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r += dr
                c += dc

            if r < 0 or r >= board_size or c < 0 or c >= board_size or board[r][c] != 0:
                blocked_end += 1

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r -= dr
                c -= dc

            if r < 0 or r >= board_size or c < 0 or c >= board_size or board[r][c] != 0:
                blocked_end += 1

            if count >= 5:
                total_score += BoardEvaluator.SCORES['FIVE']
            elif count == 4:
                if blocked_end == 0:
                    total_score += BoardEvaluator.SCORES['FOUR']
                elif blocked_end == 1:
                    total_score += BoardEvaluator.SCORES['BLOCKED_FOUR']
            elif count == 3:
                if blocked_end == 0:
                    total_score += BoardEvaluator.SCORES['THREE']
                elif blocked_end == 1:
                    total_score += BoardEvaluator.SCORES['BLOCKED_THREE']
            elif count == 2:
                if blocked_end == 0:
                    total_score += BoardEvaluator.SCORES['TWO']
                elif blocked_end == 1:
                    total_score += BoardEvaluator.SCORES['BLOCKED_TWO']

        return total_score

    @staticmethod
    def evaluate_board(board, player):
        """评估整个棋盘的分数"""
        board_size = len(board)
        total_score = 0

        for row in range(board_size):
            for col in range(board_size):
                if board[row][col] == player:
                    total_score += BoardEvaluator.evaluate_position(board, row, col, player)
                elif board[row][col] == (2 if player == 1 else 1):
                    opponent = 2 if player == 1 else 1
                    total_score -= BoardEvaluator.evaluate_position(board, row, col, opponent) * 1.1

        return total_score


def _run_mcts_worker(board, player, board_size, sim_count):
    """多进程Worker：独立运行指定次数的MCTS模拟，返回子节点统计"""
    mcts = MonteCarloTreeSearch(board_size, simulation_count=sim_count, use_heuristic=True)
    root = MCTSNode(board, player=player)
    for _ in range(sim_count):
        node = mcts._select(root)
        winner = mcts._simulate(node)
        mcts._backpropagate(node, winner)
    results = {}
    for child in root.children:
        results[child.move] = (child.wins, child.visits)
    return results


class MonteCarloTreeSearch:
    """蒙特卡洛树搜索AI"""

    def __init__(self, board_size, simulation_count=2000, use_heuristic=True):
        self.board_size = board_size
        self.simulation_count = simulation_count
        self.use_heuristic = use_heuristic
        self.evaluator = BoardEvaluator()

    def find_best_move(self, board, player):
        """找到最佳的移动位置（多进程并行加速）"""
        opponent = 2 if player == 1 else 1
        candidates = self._get_candidate_moves(board)

        if len(candidates) == 1:
            return candidates[0]

        # 快速预判：直接能赢就下
        for move in candidates:
            test = [row[:] for row in board]
            test[move[0]][move[1]] = player
            if self._check_win_on_board(test, move[0], move[1]):
                return move

        # 快速预判：必须堵对手的即时获胜
        for move in candidates:
            test = [row[:] for row in board]
            test[move[0]][move[1]] = opponent
            if self._check_win_on_board(test, move[0], move[1]):
                return move

        # 快速预判：自己能造活四
        for move in candidates:
            test = [row[:] for row in board]
            test[move[0]][move[1]] = player
            if self._creates_live_four(test, move[0], move[1], player):
                return move

        # 快速预判：对手能造活四
        for move in candidates:
            test = [row[:] for row in board]
            test[move[0]][move[1]] = opponent
            if self._creates_live_four(test, move[0], move[1], opponent):
                return move

        # 多进程并行 MCTS
        num_workers = max(1, min(os.cpu_count() or 4, self.simulation_count // 100))
        sims_per_worker = max(50, self.simulation_count // num_workers)

        all_results = []
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_run_mcts_worker, board, player, self.board_size, sims_per_worker)
                for _ in range(num_workers)
            ]
            for future in concurrent.futures.as_completed(futures):
                all_results.append(future.result())

        if not all_results:
            return None

        # 合并所有进程的结果，按总胜率取最佳
        merged = {}
        for result in all_results:
            for move, (wins, visits) in result.items():
                if move not in merged:
                    merged[move] = [0, 0]
                merged[move][0] += wins
                merged[move][1] += visits

        best_move = max(merged, key=lambda m: merged[m][0] / max(merged[m][1], 1))
        return best_move

    def _select(self, node):
        """选择阶段：使用UCT策略选择节点"""
        while node.untried_moves == [] and node.children:
            node = self._uct_select(node)

        if node.untried_moves:
            return self._expand(node)

        return node

    def _uct_select(self, node):
        """使用UCT公式选择最佳子节点"""
        def score(child):
            if child.visits == 0:
                return float('inf')
            exploitation = -child.wins / child.visits
            exploration = 1.414 * math.sqrt(math.log(node.visits) / child.visits)
            return exploitation + exploration
        return max(node.children, key=score)

    def _expand(self, node):
        """扩展阶段：按启发式评分优先扩展"""
        if self.use_heuristic and len(node.untried_moves) > 1:
            scored = []
            opponent = 2 if node.player == 1 else 1
            for move in node.untried_moves:
                attack = self.evaluator.evaluate_position(node.board_state, move[0], move[1], node.player)
                defend = self.evaluator.evaluate_position(node.board_state, move[0], move[1], opponent)
                score_val = attack * 1.1 + defend
                scored.append((move, score_val))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_n = min(3, len(scored))
            move = random.choice(scored[:top_n])[0]
        else:
            move = random.choice(node.untried_moves)

        node.untried_moves.remove(move)

        new_board = [row[:] for row in node.board_state]
        new_board[move[0]][move[1]] = node.player

        next_player = 2 if node.player == 1 else 1
        child_node = MCTSNode(new_board, parent=node, move=move, player=next_player)
        node.children.append(child_node)

        return child_node

    def _simulate(self, node):
        """模拟阶段：使用启发式策略进行游戏直到结束"""
        current_board = [row[:] for row in node.board_state]
        current_player = node.player

        if node.is_terminal():
            return node.get_result(node.player)

        move_count = 0
        max_moves = self.board_size * self.board_size

        while move_count < max_moves:
            # 使用候选落子代替全棋盘扫描（方案二优化）
            available_moves = self._get_candidate_moves(current_board)

            if not available_moves:
                return 0

            if self.use_heuristic:
                move = self._heuristic_move_selection(current_board, current_player, available_moves)
            else:
                move = random.choice(available_moves)

            current_board[move[0]][move[1]] = current_player

            if self._check_win_on_board(current_board, move[0], move[1]):
                if current_player == node.player:
                    return 1
                else:
                    return -1

            current_player = 2 if current_player == 1 else 2
            move_count += 1

        return 0

    def _heuristic_move_selection(self, board, player, available_moves):
        """启发式移动选择"""
        opponent = 2 if player == 1 else 1

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = player
            if self._check_win_on_board(test_board, move[0], move[1]):
                return move

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = opponent
            if self._check_win_on_board(test_board, move[0], move[1]):
                return move

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = player
            if self._creates_live_four(test_board, move[0], move[1], player):
                return move

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = opponent
            if self._creates_live_four(test_board, move[0], move[1], opponent):
                return move

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = player
            if self._creates_four(test_board, move[0], move[1], player):
                return move

        for move in available_moves:
            test_board = [row[:] for row in board]
            test_board[move[0]][move[1]] = opponent
            if self._creates_four(test_board, move[0], move[1], opponent):
                return move

        scored_moves = []
        for move in available_moves:
            if self._has_neighbor(board, move[0], move[1]):
                attack_score = self.evaluator.evaluate_position(board, move[0], move[1], player)
                defend_score = self.evaluator.evaluate_position(board, move[0], move[1], opponent)
                total_score = attack_score * 1.1 + defend_score
                scored_moves.append((move, total_score))
            else:
                scored_moves.append((move, 0))

        scored_moves.sort(key=lambda x: x[1], reverse=True)
        top_moves = scored_moves[:min(5, len(scored_moves))]
        return random.choice(top_moves)[0]

    def _has_neighbor(self, board, row, col):
        """检查位置周围是否有棋子"""
        directions = [(-1, -1), (-1, 0), (-1, 1),
                      (0, -1), (0, 1),
                      (1, -1), (1, 0), (1, 1)]

        for dr, dc in directions:
            r, c = row + dr, col + dc
            if 0 <= r < self.board_size and 0 <= c < self.board_size:
                if board[r][c] != 0:
                    return True
        return False

    def _check_win_on_board(self, board, row, col):
        """在指定棋盘上检查是否获胜"""
        player = board[row][col]
        board_size = len(board)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r += dr
                c += dc

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r -= dr
                c -= dc

            if count >= 5:
                return True
        return False

    def _get_candidate_moves(self, board):
        """获取已有棋子周围2格内的空位"""
        board_size = len(board)
        has_stone = any(board[r][c] != 0 for r in range(board_size) for c in range(board_size))
        if not has_stone:
            center = board_size // 2
            return [(center, center)]

        moves = set()
        for row in range(board_size):
            for col in range(board_size):
                if board[row][col] != 0:
                    for dr in range(-2, 3):
                        for dc in range(-2, 3):
                            r, c = row + dr, col + dc
                            if 0 <= r < board_size and 0 <= c < board_size and board[r][c] == 0:
                                moves.add((r, c))
        return list(moves)

    def _creates_live_four(self, board, row, col, player):
        """检查落子后是否形成活四"""
        board_size = len(board)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            open_ends = 0

            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r += dr
                c += dc
            if 0 <= r < board_size and 0 <= c < board_size and board[r][c] == 0:
                open_ends += 1

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if 0 <= r < board_size and 0 <= c < board_size and board[r][c] == 0:
                open_ends += 1

            if count >= 4 and open_ends == 2:
                return True

        return False

    def _creates_four(self, board, row, col, player):
        """检查落子后是否形成冲四或活四"""
        board_size = len(board)
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

        for dr, dc in directions:
            count = 1
            open_ends = 0

            r, c = row + dr, col + dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r += dr
                c += dc
            if 0 <= r < board_size and 0 <= c < board_size and board[r][c] == 0:
                open_ends += 1

            r, c = row - dr, col - dc
            while 0 <= r < board_size and 0 <= c < board_size and board[r][c] == player:
                count += 1
                r -= dr
                c -= dc
            if 0 <= r < board_size and 0 <= c < board_size and board[r][c] == 0:
                open_ends += 1

            if count >= 4 and open_ends >= 1:
                return True

        return False

    def _backpropagate(self, node, result):
        """回溯阶段：更新节点统计信息"""
        while node is not None:
            node.visits += 1
            node.wins += result
            result = -result
            node = node.parent


class Gomoku:
    def __init__(self):
        self.board_size = 15
        self.cell_size = 35
        self.piece_radius = 15

        self.board = [[0 for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.current_player = 1
        self.game_over = False
        self.pvp_mode = True
        self.last_move = None  # 记录最近一步落子的位置

        # 人机模式下：人控制黑棋(先手)，AI控制白棋(后手)
        self.human_player = 1
        self.ai_player = 2

        self.root = tk.Tk()
        self.root.title("五子棋 - 14×14")
        self.root.resizable(False, False)

        canvas_size = self.board_size * self.cell_size + 40
        self.canvas = tk.Canvas(
            self.root,
            width=canvas_size,
            height=canvas_size,
            bg="#DEB887"
        )
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", self.on_click)

        self.status_var = tk.StringVar(value="黑棋回合")
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Arial", 14),
            pady=10
        )
        self.status_label.pack()

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        reset_btn = tk.Button(
            button_frame,
            text="重新开始",
            command=self.reset_game,
            font=("Arial", 12),
            padx=15
        )
        reset_btn.pack(side=tk.LEFT, padx=5)

        self.mode_btn = tk.Button(
            button_frame,
            text="切换人机模式",
            command=self.toggle_mode,
            font=("Arial", 12),
            padx=15
        )
        self.mode_btn.pack(side=tk.LEFT, padx=5)

        self.first_move_btn = tk.Button(
            button_frame,
            text="切换先后手",
            command=self.toggle_first_move,
            font=("Arial", 12),
            padx=15
        )
        self.first_move_btn.pack(side=tk.LEFT, padx=5)

        self.draw_board()

    def toggle_mode(self):
        """切换游戏模式"""
        self.pvp_mode = not self.pvp_mode
        mode_text = "人人对战" if self.pvp_mode else "人机对战"
        messagebox.showinfo("模式切换", f"已切换到：{mode_text}")
        self.reset_game()

    def toggle_first_move(self):
        """切换人机模式下的先后手"""
        if self.pvp_mode:
            messagebox.showinfo("提示", "请先切换到人机模式")
            return
        self.human_player = 2 if self.human_player == 1 else 1
        self.ai_player = 2 if self.human_player == 1 else 1
        first_text = "你先手(黑棋)" if self.human_player == 1 else "AI先手(黑棋)"
        messagebox.showinfo("先后手切换", f"已切换：{first_text}")
        self.reset_game()

    def draw_board(self):
        """绘制棋盘网格"""
        offset = 20
        for i in range(self.board_size):
            y = offset + i * self.cell_size
            self.canvas.create_line(
                offset, y,
                offset + (self.board_size - 1) * self.cell_size, y,
                fill="black", width=1
            )
            x = offset + i * self.cell_size
            self.canvas.create_line(
                x, offset,
                x, offset + (self.board_size - 1) * self.cell_size,
                fill="black", width=1
            )

        self.draw_all_pieces()

    def draw_all_pieces(self):
        """绘制所有棋子，并在最近落子位置标记红点"""
        offset = 20
        for row in range(self.board_size):
            for col in range(self.board_size):
                if self.board[row][col] != 0:
                    x = offset + col * self.cell_size
                    y = offset + row * self.cell_size
                    color = "black" if self.board[row][col] == 1 else "white"
                    self.canvas.create_oval(
                        x - self.piece_radius, y - self.piece_radius,
                        x + self.piece_radius, y + self.piece_radius,
                        fill=color, outline="black", width=2
                    )
                    # 如果是最近落子，在棋子中心画红点
                    if self.last_move and (row, col) == self.last_move:
                        dot_radius = 5
                        self.canvas.create_oval(
                            x - dot_radius, y - dot_radius,
                            x + dot_radius, y + dot_radius,
                            fill="red", outline=""
                        )

    def on_click(self, event):
        """处理鼠标点击事件"""
        if self.game_over:
            return

        # 如果是人机模式且当前不是人类回合，忽略点击
        if not self.pvp_mode and self.current_player != self.human_player:
            return

        offset = 20
        col = round((event.x - offset) / self.cell_size)
        row = round((event.y - offset) / self.cell_size)

        if row < 0 or row >= self.board_size or col < 0 or col >= self.board_size:
            return

        if self.board[row][col] != 0:
            return

        self.make_move(row, col)

    def make_move(self, row, col):
        """执行落子操作"""
        self.board[row][col] = self.current_player
        self.last_move = (row, col)  # 记录最近落子位置

        self.canvas.delete("all")
        self.draw_board()

        if self.check_win(row, col):
            winner = "黑棋" if self.current_player == 1 else "白棋"
            self.status_var.set(f"{winner}获胜！")
            self.game_over = True
            messagebox.showinfo("游戏结束", f"{winner}获胜！")
            return

        if self.check_draw():
            self.status_var.set("平局！")
            self.game_over = True
            messagebox.showinfo("游戏结束", "平局！")
            return

        self.current_player = 2 if self.current_player == 1 else 1
        player_name = "黑棋" if self.current_player == 1 else "白棋"
        self.status_var.set(f"{player_name}回合")

        # 如果是人机模式且当前是AI回合，触发AI落子
        if not self.pvp_mode and self.current_player == self.ai_player:
            self.root.after(100, self.ai_move)

    def ai_move(self):
        """AI落子（使用多进程并行MCTS）"""
        if self.game_over:
            return

        self.status_var.set("AI思考中...")
        self.root.update()

        mcts = MonteCarloTreeSearch(
            self.board_size,
            simulation_count=6000,
            use_heuristic=True
        )
        best_move = mcts.find_best_move(self.board, self.current_player)

        if best_move:
            row, col = best_move
            self.make_move(row, col)

    def check_win(self, row, col):
        """检查是否在(row, col)位置形成五连珠"""
        player = self.board[row][col]
        directions = [
            (0, 1),
            (1, 0),
            (1, 1),
            (1, -1)
        ]

        for dr, dc in directions:
            count = 1

            r, c = row + dr, col + dc
            while 0 <= r < self.board_size and 0 <= c < self.board_size and self.board[r][c] == player:
                count += 1
                r += dr
                c += dc

            r, c = row - dr, col - dc
            while 0 <= r < self.board_size and 0 <= c < self.board_size and self.board[r][c] == player:
                count += 1
                r -= dr
                c -= dc

            if count >= 5:
                return True

        return False

    def check_draw(self):
        """检查是否平局"""
        for row in range(self.board_size):
            for col in range(self.board_size):
                if self.board[row][col] == 0:
                    return False
        return True

    def reset_game(self):
        """重置游戏"""
        self.board = [[0 for _ in range(self.board_size)] for _ in range(self.board_size)]
        self.current_player = 1
        self.game_over = False
        self.last_move = None  # 重置时清除最近落子标记
        if self.pvp_mode:
            self.status_var.set("黑棋回合 (人人)")
        else:
            first = "你先手" if self.human_player == 1 else "AI先手"
            self.status_var.set(f"黑棋回合 ({first})")
        self.canvas.delete("all")
        self.draw_board()

        # 人机模式下AI先手，自动触发AI落子
        if not self.pvp_mode and self.current_player == self.ai_player:
            self.status_var.set("AI思考中...")
            self.root.after(100, self.ai_move)

    def run(self):
        """运行游戏"""
        self.root.mainloop()


if __name__ == "__main__":
    game = Gomoku()
    game.run()
