from re import S
from piece import Piece

class Move_generator:
    # Orthogonal and diagonal offsets of board represented in one dimension
    dir_offsets = [-9, 1, 9, -1, -8, 10, 8, -10]
    def __init__(self, board) -> None:
        # Was too lazy counting the offsets by force, required to be in a specific order
        self.dir_offsets.extend(self.jumps_from_orthogonal_offsets())
        self.dist_to_edge = self.precompute_dists()

        self.moves = set()
        self.illegal_moves = set()

        self.horse_moves = self.precompute_horse_moves()
        self.advisor_moves = self.precompute_advisor_moves()
        self.elephant_moves = self.precompute_elephant_moves()
        self.pawn_moves = self.precompute_pawn_moves()
        self.board = board
        self.friendly = None
        self.target_squares = {}
        self.pinned_squares = []
        self.checkmate = False
        self.red_in_check = False
        self.white_in_check = False
        self.stalemate = False
        
    @staticmethod
    def precompute_dists() -> list:
        """
        :return: list of tuples containing the distances to the board's
        edges with orthogonal and diagonal movement for every square
        """
        distances = []
        for rank in range(10):
            for file in range(9):
                up = rank
                down = 9 - rank
                left = file
                right = 8 - file
                dist = [
                    up,
                    right,
                    down,
                    left,
                    min(up, right),
                    min(right, down),
                    min(down, left),
                    min(left, up)
                ]
                distances.append(dist)
        return distances

    @staticmethod
    def jumps_from_orthogonal_offsets() -> list:
        """
        :return: a list of integers representing the offsets of a horse jump,
        ordered in a way where precompute_horse_moves() can use them to exclude
        illegal moves blocked by a piece
        """
        horse_offsets = []
        dir_offsets = Move_generator.dir_offsets[:4] + [-9]

        for dir_index in range(4):
            second_dir_idx = dir_index + 1

            for steps in range(2):
                first_dir_steps = 2 - steps
                second_dir_steps = 1 + steps
                new_offset = dir_offsets[dir_index] * first_dir_steps + dir_offsets[second_dir_idx] * second_dir_steps
                horse_offsets.append(new_offset)
        return horse_offsets

    def precompute_horse_moves(self) -> list:
        """
        :return: a list of tuples containing the start and end indices of all possible horse moves
        """
        # (not accounting for move blocks, )

        horse_offsets = self.dir_offsets[8:16]
        horse_moves = []
        for square in range(89):
            horse_moves.append([])
            for dir_index in range(8):
                # board is a 1d array, so if jump is outside of file (illegal), it will just jump to new rank
                # fix to illegal jumps perceived as legal by computer 
                target_square = square + horse_offsets[dir_index]
                target_rank = target_square // 9
                target_file = target_square - target_rank * 9
                current_rank = square // 9
                current_file = square - current_rank * 9
                max_dist = max(abs(current_rank - target_rank), abs(current_file - target_file))
                if max_dist > 2 or not -1 < target_square < 90:
                    continue
                horse_moves[square].append((square, target_square))

        return horse_moves

    def precompute_advisor_moves(self) -> list:
        """
        :return: a list of two dictionaries containing all start indices as keys 
        and the possible targets of those positions as value of a particular color\n
        output form : [{-12: [-20, -2, -4, -22], -20: [-12], -2: ...}, {...}]
        """
        advisor_moves = []
        # _____
        #|\ | /|
        #|--+--| the + marks the middle
        #|/ | \| of the so-called palace
        # -----

        palace_middle_squares = [89 - 13, 13]
        for color in range(2):
            advisor_moves.append({})
            middle_square = palace_middle_squares[color]
            # seperate moves for each color
            for dir_index in range(4, 8):

                dir_offset = self.dir_offsets[dir_index]
                target_square = middle_square + dir_offset

                # All of the target squares' only move is back to the 
                # palace_middle_square, so add move to target_square and back
                advisor_moves[color][middle_square] = advisor_moves[color].get(middle_square, []) + [target_square]
                advisor_moves[color][target_square] = advisor_moves[color].get(target_square, []) + [middle_square]
        return advisor_moves

    def precompute_pawn_moves(self) -> list:
        """
        :return: a list of two dictionaries containing all start indices as keys 
        and the possible targets of those positions as value of a particular color\n
        output form : [{-12: [-20, -2, -4, -22], -20: [-12], -2: ...}, {...}]
        """
        pawn_moves = []
        offset_push_move = [-9, 9]

        # Used to determine whether pawn can push foward
        is_foward_move = (lambda rank: 0 < rank < 7, lambda rank: 9 > rank > 2)
        # Used to determine whether pawn can move sideways (after crossing river)
        is_river_crossed = (lambda rank: rank < 5, lambda rank: rank > 4)

        for color in range(2):
            pawn_moves.append({})
            for square in range(89):
                rank = square // 9
                river_crossed = is_river_crossed[color](rank)
                foward_move = is_foward_move[color](rank)
                if river_crossed:
                    for dir_idx in [1, 3]:
                        if self.dist_to_edge[square][dir_idx] < 1:
                            continue
                        offset = self.dir_offsets[dir_idx]
                        pawn_moves[color][square] = pawn_moves[color].get(square, []) + [square + offset]
                if is_foward_move:
                    offset = offset_push_move[color]
                    pawn_moves[color][square] = pawn_moves[color].get(square, []) + [square + offset]
        return pawn_moves
        
    def precompute_elephant_moves(self) -> list:
        """
        :return: a list of two dictionaries containing all start indices as keys 
        and the possible targets of those positions as value of a particular color\n
        output form : [{-12: [-20, -2, -4, -22], -20: [-12], -2: ...}, {...}]
        """
        elephant_moves = []
        offsets = self.dir_offsets[4:8]

        # if the normal range() function is used every time, is_river_crossed will be True 
        # in the first iteration of white color / color = 0, so go backwards from last rank
                                # Equivalent to "reversed(range(start + 1, stop + 1, step))"
        iteration_sequence = (lambda start, stop, step: range(stop - 1, start - 1, -step),
                            lambda start, stop, step: range(start, stop, step))
        # Used to determine whether move or current position crosses river (in which case it's illegal)
        is_river_crossed = (lambda rank: rank < 5, lambda rank: rank > 4)

        for color in range(2):
            elephant_moves.append({})
            for rank in iteration_sequence[color](0, 10, 2):
                # If current position crossed river, go to next color
                if is_river_crossed[color](rank):
                    break

                for file in range(0, 9, 2):
                    square = rank * 9 + file
                    for offset in offsets:
                        target_square = square + offset * 2
                        # Avoiding moves to negative squares
                        if not -1 < target_square < 90:
                            continue

                        target_rank = target_square // 9
                        move_crosses_river = is_river_crossed[color](target_rank)
                        if move_crosses_river:
                            continue
                        
                        target_file = target_square % 9
                        # Avoiding moves out of bounds, see "precompute_horse_moves()"
                        max_dist = max(abs(target_rank - rank), abs(target_file - file))
                        if max_dist > 2:
                            continue
                        elephant_moves[color][square] = elephant_moves[color].get(square, []) + [target_square]
        return elephant_moves

    def load_moves(self, color_to_move) -> list:
        """
        :return: a list of tuples containing the start and end indices of all possible moves
        color_to_move : int
        """
        # variable "color_to_move" can be used for indexing and determining the color of piece 
        # (see "piece.py > class Piece") here e.g. allows to only loop over friendly indices
        self.friendly = color_to_move

        self.moves = set()
        self.illegal_moves = set()
        self.target_squares = {}

        for square in self.board.piece_square[self.friendly]:
            piece_type = self.board.squares[square][1]
            
            if piece_type == Piece.rook:
                self.generate_rook_moves(square)
            if piece_type == Piece.cannon:
                self.generate_cannon_moves(square)
            if piece_type == Piece.horse:
                self.generate_horse_moves(square)
            if piece_type == Piece.advisor:
                self.generate_advisor_moves(square)
            if piece_type == Piece.pawn:
                self.generate_pawn_moves(square)
            if piece_type == Piece.elephant:
                self.generate_elephant_moves(square)
        
        return self.moves

    def generate_pawn_moves(self, current_square):
        """
        extends move_generator.moves with legal pawn moves
        """
        target_squares = self.pawn_moves[self.friendly][current_square]
        for target_square in target_squares:

            target_piece = self.board.squares[target_square]
            # Checking if target_piece is friendly while avoiding Errors 
            # (piece is equal to 0 when target_square is empty) so piece[0] would raise TypeError
            is_friendly = target_piece[0] == self.friendly if target_piece else False
            if is_friendly:
                continue

            self.moves.add((current_square, target_square))
            self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]

    def generate_elephant_moves(self, current_square):
        """
        extends move_generator.moves with legal elephant moves
        """
        target_squares = self.elephant_moves[self.friendly][current_square]
        illegal_squares = set()
        for dir_idx in range(4, 8):
            # Checking for blocks
            if self.dist_to_edge[current_square][dir_idx] < 1:
                continue

            offset = self.dir_offsets[dir_idx]
            blocking_square = current_square + offset

            if self.board.squares[blocking_square]:
                illegal_squares.add(current_square + offset * 2)

        # Removing illegal target squares
        target_squares = list(set(target_squares) - illegal_squares)
        
        for target_square in target_squares:
            target_piece = self.board.squares[target_square]
            is_friendly = target_piece[0] == self.friendly if target_piece else False
            if is_friendly:
                continue
            
            self.moves.add((current_square, target_square))
            self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]
    
    def generate_advisor_moves(self, current_square):
        """
        extends move_generator.moves with legal advisor moves
        """
        target_squares = self.advisor_moves[self.friendly][current_square]
        
        for target_square in target_squares:
            target_piece = self.board.squares[target_square]
            is_friendly = target_piece[0] == self.friendly if target_piece else False
            if is_friendly:
                continue

            self.moves.add((current_square, target_square))
            self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]
        
    def generate_horse_moves(self, current_square):
        """
        extends move_generator.moves with legal horse moves
        """
        horse_offsets = self.dir_offsets[8:16]
        legal_moves = self.horse_moves[current_square]
        illegal_moves = set()

        # removing moves blocked by other pieces
        for dir_idx in range(4):
            if self.dist_to_edge[current_square][dir_idx] < 1:
                continue

            blocking_square = current_square + self.dir_offsets[dir_idx]
            is_blocking_move = self.board.squares[blocking_square]
            if is_blocking_move:

                # make use of the order of horse_jumps
                # use the dir_idx for calculating the blocking square to also get the moves blocked by it
                blocked_squares = [current_square + horse_offsets[dir_idx * 2 - i] for i in range(2)]
                illegal_moves.add((current_square, blocked_squares[0]))
                illegal_moves.add((current_square, blocked_squares[1]))

        legal_moves = list(set(legal_moves) - illegal_moves)
        # legal_moves = list(filter(lambda move: move in illegal_moves, legal_moves))
        for move in legal_moves:
            target_square = move[1]
            target_piece = self.board.squares[target_square]
            is_friendly = target_piece[0] == self.friendly if target_piece else False
            if is_friendly:
                continue

            self.moves.add((current_square, target_square))
            self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]
                
    def generate_rook_moves(self, current_square) -> None:
        """
        extends move_generator.moves with legal rook moves
        """
        # Going through chosen direction indices
        for dir_index in range(4):
            target_piece = False
            # "Walking" in direction using direction offsets
            for step in range(self.dist_to_edge[current_square][dir_index]):
                target_square = current_square + self.dir_offsets[dir_index] * (step + 1)

                if self.board.squares[target_square]:
                    target_piece = self.board.squares[target_square]
                    if target_piece[0] == self.friendly:
                        break

                self.moves.add((current_square, target_square))
                self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]

                # If piece on target square and not friendly, go to next direction
                if target_piece:
                    break

    def generate_cannon_moves(self, current_square):
        """
        extends move_generator.moves with legal cannon moves
        """
        # Going through chosen direction indices
        for dir_index in range(4):
            in_attack_mode = False
            target_piece = False
            # "Walking" in direction using direction offsets
            for step in range(self.dist_to_edge[current_square][dir_index]):
                target_square = current_square + self.dir_offsets[dir_index] * (step + 1)

                if in_attack_mode:
                    if not self.board.squares[target_square]:
                        continue
                    target_piece = self.board.squares[target_square]
                    # If target_piece is friendly, go to next direction
                    if target_piece[0] == self.friendly:
                        break
                        
                elif self.board.squares[target_square]:
                    in_attack_mode = True
                    continue
                # If piece on target square and not friendly, add move and go to next direction
                self.moves.add((current_square, target_square))
                self.target_squares[current_square] = self.target_squares.get(current_square, []) + [target_square]
                if target_piece:
                    break