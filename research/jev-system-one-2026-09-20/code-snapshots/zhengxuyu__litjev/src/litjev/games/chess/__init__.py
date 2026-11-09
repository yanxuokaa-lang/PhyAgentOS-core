"""Five-key chess Gymnasium adapter; no legal-move or FEN input to the policy."""

import chess

from litjev.games.base import PixelEnv

from .controller import KEYS, Controller
from .rendering import render_board

CHESS_INSTRUCTIONS = (
    "Play chess using one controller key per decision, based only on the screenshot. "
    "Your pieces are at the bottom. Gold square border is the cursor; orange means holding. "
    "Move the cursor to a piece, toggle to pick it up, move to a destination, toggle to put down. "
    "Blue squares mark allowed destinations for the held piece. "
    "Pieces are geometric: pawn small circle, rook square, knight triangle, bishop diamond, "
    "queen large ring, king cross. Choose keys that lead to good legal chess moves."
)


class ChessKeysEnv(PixelEnv):
    instructions = CHESS_INSTRUCTIONS

    def __init__(self, max_steps=240, render_mode="rgb_array", player="white"):
        super().__init__(KEYS, (480, 640, 3), max_steps, render_mode)
        if player not in {"white", "black"}:
            raise ValueError("player must be white or black")
        self.colour = chess.WHITE if player == "white" else chess.BLACK
        self.board = chess.Board()
        self.controller = Controller(self.board)

    def _draw(self):
        self.frame.fill(0)
        self.frame[:, 80:560] = render_board(
            self.board,
            self.controller.cursor,
            self.colour == chess.BLACK,
            self.controller.holding,
            size=480,
        )

    def _opponent(self):
        moves = list(self.board.legal_moves)
        if moves:
            self.board.push(moves[int(self.np_random.integers(len(moves)))])

    def reset(self, *, seed=None, options=None):
        if options:
            raise ValueError("Custom chess positions are not supported by this visual demo")
        super().reset(seed=seed)
        self.board = chess.Board()
        self.controller = Controller(self.board, cursor=(7, 4))
        if self.colour == chess.BLACK:
            self._opponent()
        self._draw()
        return self.frame.copy(), {"opponent": "random"}

    def step(self, action):
        self._check_action(action)
        event, move = self.controller.press(int(action))
        outcome = self.board.outcome(claim_draw=True)
        if move is not None and outcome is None:
            self._opponent()
            outcome = self.board.outcome(claim_draw=True)
        reward = 0.0
        if outcome and outcome.winner is not None:
            reward = 1.0 if outcome.winner == self.colour else -1.0
        self._draw()
        return self._transition(
            reward,
            outcome is not None,
            {
                "event": event,
                "move": move.uci() if move else None,
                "result": outcome.result() if outcome else None,
            },
        )
