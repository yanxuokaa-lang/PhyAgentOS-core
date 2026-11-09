# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Minimal Labs
# Ported from vinnylarouge/jevlike @ 94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452
# Modified for LitJev: package imports; removed training/standalone entry points.
"""The chess controller: four arrows and one pick-up/put-down toggle.

Screen coordinates are (row, col) with row 0 at the top; the mover's pieces are
always at the bottom (the board is flipped when black is to move).
"""

from __future__ import annotations

import chess

from .rendering import square_at

KEYS = ("move up", "move down", "move left", "move right", "pick up / put down")
UP, DOWN, LEFT, RIGHT, TOGGLE = range(5)
STEP = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}


class Controller:
    """Applies keys to a board. `press` returns what happened; wasted presses are named."""

    def __init__(self, board: chess.Board, cursor: tuple[int, int] = (7, 4)) -> None:
        self.board = board
        self.cursor = cursor
        self.holding: int | None = None

    @property
    def flip(self) -> bool:
        return self.board.turn == chess.BLACK

    def press(self, key: int) -> tuple[str, chess.Move | None]:
        if key != TOGGLE:
            dr, dc = STEP[key]
            row, col = self.cursor[0] + dr, self.cursor[1] + dc
            if not (0 <= row < 8 and 0 <= col < 8):
                return "edge", None
            self.cursor = (row, col)
            return "moved", None
        square = square_at(*self.cursor, self.flip)
        if self.holding is None:
            piece = self.board.piece_at(square)
            if piece is None or piece.color != self.board.turn:
                return "empty", None
            self.holding = square
            return "lift", None
        if square == self.holding:
            self.holding = None
            return "drop", None
        move = chess.Move(self.holding, square)
        if self.board.piece_type_at(self.holding) == chess.PAWN and chess.square_rank(square) in (
            0,
            7,
        ):
            move = chess.Move(self.holding, square, promotion=chess.QUEEN)
        if move not in self.board.legal_moves:
            return "illegal", None
        self.board.push(move)
        self.holding = None
        return "put", move
