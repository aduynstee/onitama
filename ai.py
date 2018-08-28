import onitama as oni
from collections import namedtuple

RED = 0
BLUE = 1

EMPTY = 0
REDPAWN = 1
REDKING = 2
BLUEPAWN = -1
BLUEKING = -2

# Goal square for kings (Reach goal and win game)
REDGOAL = 22
BLUEGOAL = 2

'''
A board is a length 25 array of ints, each index i representing
the coordinate (x, y) = (i % 5, i // 5)

The values in the array represent what is contained at each square
See above for integer meanings (EMPTY = 0, REDPAWN = 1, etc)

Moves have start and end squares as integers (same convention) with
the player performing the move identified by RED = 0, BLUE = 1

Card.moves is an array of arrays where obj.moves[i] contains all legal destination
squares for a move starting on square i
'''

def create_ai(version='unmove', game=None):
    if version == 'unmove':
        return MoveUnmoveAI(game)
    elif version == 'copy':
        return CopyMoveAI(game)

class CopyMoveAI:
    class Node:
        __slots__ = ['board', 'prev_move', 'cards', 'children', 'parent', 'end', 'eval']

        def __init__(self, board, prev_move, cards, children, parent, end):
            self.board = board
            self.prev_move = prev_move
            self.cards = cards
            self.children = children
            self.parent = parent
            self.end = end

    class Move:
        __slots__ = ['start', 'end', 'player', 'card']

        def __init__(self, start, end, player, card):
            self.start = start
            self.end = end
            self.player = player
            self.card = card

    def __init__(self, game=None):
        if game != None:
            self.set_game_as_root(game)

    def set_game_as_root(self, game):
        self.game = game
        self.card_data = tuple(create_card(oni.CARD_TO_NAME[card]) for card in game.start_cards)
        cards = [
            game.start_cards.index(card)
            for card in game.cards[oni.Player.RED]+game.cards[oni.Player.BLUE]+[game.neutral_card]
        ]
        self.root = self.Node(
            board=convert_board(self.game.board.array),
            prev_move=None,
            cards=cards,
            children=[],
            parent=None,
            end=False if game.check_victory() is None else True,
        )

    def do_move(self, move, node):
        new_board = node.board[:]
        if move.player == BLUE:
            if (new_board[move.end] == REDKING
                or (new_board[move.start] == BLUEKING and move.end == BLUEGOAL)):
                gameover = True
            else:
                gameover = False
        else:
            if (new_board[move.end] == BLUEKING
                or (new_board[move.start] == REDKING and move.end == REDGOAL)):
                gameover = True
            else:
                gameover = False
        new_board[move.end] = new_board[move.start]
        new_board[move.start] = EMPTY
        new_cards = node.cards[:]
        # Swap index(move.card) with index 4
        new_cards[new_cards.index(move.card)] = new_cards[4]
        new_cards[4] = move.card
        return self.Node(
            board=new_board,
            prev_move=move,
            cards=new_cards,
            children=[],
            parent=node,
            end=gameover,
        )

    def mock_search(self, depth, mode='d'):
        if mode == 'b':
            self._breadth_first(depth)
        elif mode == 'd':
            self._depth_first(depth)
        else:
            raise Exception('Invalid search mode')

    def _breadth_first(self, depth):
        def generate_children(node):
            if not node.end:
                node.children = [
                    self.do_move(move, node) for move in self.next_moves(node)
                ]
        frontier = [self.root]
        for _ in range(depth):
            for node in frontier:
                generate_children(node)
            frontier = [child for node in frontier for child in node.children]

    def _depth_first(self, depth):
        def search_children(start_node, depth):
            if depth <= 0 or start_node.end:
                return
            moves = self.next_moves(start_node)
            start_node.children = [0 for _ in range(len(moves))]
            for i, move in enumerate(moves):
                start_node.children[i] = self.do_move(move, start_node)
                search_children(start_node.children[i], depth-1)
        search_children(self.root, depth)

    def next_moves(self, node):
        if node.prev_move is None:
            player = self.card_data[4].start_player
        else:
            player = (node.prev_move.player+1) % 2
        pieces = [REDPAWN, REDKING] if player == RED else [BLUEPAWN, BLUEKING]
        start_squares = [i for i in range(25) if node.board[i] in pieces]
        player_cards = node.cards[player*2:player*2+2]
        return [
            self.Move(start=start, end=end, player=player, card=card)
            for start in start_squares
            for card in player_cards
            for end in self.card_data[card].moves[player][start]
            if end not in start_squares
        ]

    def get_nodes(self, depth):
        frontier = [self.root]
        for _ in range(depth):
            frontier = [child for node in frontier for child in node.children]
        return frontier

class MoveUnmoveAI:
    class Node:
        __slots__ = ['prev_move', 'children', 'parent', 'end', 'eval']

        def __init__(self, prev_move, children, parent, end, eval):
            self.prev_move = prev_move
            self.children = children
            self.parent = parent
            self.end = end
            self.eval = eval

    class Move:
        __slots__ = ['start', 'end', 'target', 'player', 'card', 'neutral_card']

        def __init__(self, start, end, target, player, card, neutral_card):
            self.start = start
            self.end = end
            self.target = target
            self.player = player
            self.card = card
            self.neutral_card = neutral_card

    def __init__(self, game=None):
        if game != None:
            self.set_game_as_root(game)

    def set_game_as_root(self, game):
        self.game = game
        self.card_data = tuple(create_card(oni.CARD_TO_NAME[card]) for card in game.start_cards)
        self.board = convert_board(self.game.board.array)
        self.cards = [
            game.start_cards.index(card)
            for card in game.cards[oni.Player.RED]+game.cards[oni.Player.BLUE]+[game.neutral_card]
        ]
        self.active_player = RED if game.active_player.color() == 'red' else BLUE
        self.root = self.Node(
            prev_move=None,
            children=[],
            parent=None,
            end=True if game.check_victory() is not None else False,
            eval=0,
        )

    def next_moves(self):
        pieces = [REDPAWN, REDKING] if self.active_player == RED else [BLUEPAWN, BLUEKING]
        start_squares = [i for i in range(25) if self.board[i] in pieces]
        player_cards = self.cards[self.active_player*2:self.active_player*2+2]
        return [
            self.Move(start=start, end=end, target=self.board[end], player=self.active_player, card=card, neutral_card=self.cards[4])
            for start in start_squares
            for card in player_cards
            for end in self.card_data[card].moves[self.active_player][start]
            if end not in start_squares
        ]

    def evaluate_current(self):
        # stub method

        return 0

    def do_move(self, move, node):
        source = self.board[move.start]
        if source == REDKING and move.end == REDGOAL:
            gameover = True
        elif source == BLUEKING and move.end == BLUEGOAL:
            gameover = True
        elif move.target == REDKING or move.target == BLUEKING:
            gameover = True
        else:
            gameover = False
        self.board[move.end] = self.board[move.start]
        self.board[move.start] = EMPTY
        self.cards[self.cards.index(move.card)] = self.cards[4]
        self.cards[4] = move.card
        self.active_player = (self.active_player+1)%2
        return self.Node(
            prev_move = move,
            children=[],
            parent=node,
            end=gameover,
            eval=0,
        )

    def undo_move(self, move):
        self.board[move.start] = self.board[move.end]
        self.board[move.end] = move.target
        self.cards[self.cards.index(move.neutral_card)] = move.card
        self.cards[4] = move.neutral_card
        self.active_player = (self.active_player+1)%2

    def mock_search(self, depth):
        def search_children(start_node, depth):
            if depth <= 0 or start_node.end:
                return
            moves = self.next_moves()
            start_node.children = [0 for _ in range(len(moves))]
            for i, move in enumerate(moves):
                start_node.children[i] = self.do_move(move, start_node)
                search_children(start_node.children[i], depth-1)
                self.undo_move(move)
        search_children(self.root, depth)

    def get_nodes(self, depth):
        nodes = [self.root]
        for _ in range(depth):
            nodes = [child for node in nodes for child in node.children]
        return nodes

class Card:
    __slots__ = ['moves', 'start_player', 'name']

    def __init__(self, moves, start_player, name):
        self.moves = moves
        self.start_player = start_player
        self.name = name

def create_card(card_name):
    card = oni.NAME_TO_CARD[card_name]
    red_disps = [c[0]+c[1]*5 for c in card.moves[oni.Player.RED]]
    blue_disps = [c[0]+c[1]*5 for c in card.moves[oni.Player.BLUE]]
    red_moves = tuple(
        tuple(i+d for d in red_disps if i+d in range(25)) for i in range(25)
    )
    blue_moves = tuple(
        tuple(i+d for d in blue_disps if i+d in range(25)) for i in range(25)
    )
    return Card(
        moves=(red_moves, blue_moves),
        start_player=RED if card.start_player.color() == 'red' else BLUE,
        name=card_name,
    )

def convert_board(board):
    pieces = {
        oni.Piece.EMPTY: EMPTY,
        oni.Piece.R_PAWN: REDPAWN,
        oni.Piece.R_KING: REDKING,
        oni.Piece.B_PAWN: BLUEPAWN,
        oni.Piece.B_KING: BLUEKING,
    }
    return [pieces[p] for p in board]
