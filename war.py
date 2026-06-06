import sqlite3
import random
import argparse
from datetime import datetime

SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUE = {r: i for i, r in enumerate(RANKS, 2)}

# Safety valve — a War game can theoretically loop forever
MAX_ROUNDS = 10000

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    played_at     TEXT    NOT NULL,
    winner        TEXT    NOT NULL,
    total_rounds  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   INTEGER NOT NULL REFERENCES games(id),
    round_num INTEGER NOT NULL,
    p1_card   TEXT    NOT NULL,
    p2_card   TEXT    NOT NULL,
    winner    TEXT    NOT NULL,
    was_war   INTEGER NOT NULL DEFAULT 0
);
"""


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.value = RANK_VALUE[rank]

    def __str__(self):
        return f"{self.rank} of {self.suit}"


class Deck:
    def __init__(self):
        cards = [Card(r, s) for s in SUITS for r in RANKS]
        random.shuffle(cards)
        self.cards = cards

    def split(self):
        mid = len(self.cards) // 2
        return self.cards[:mid], self.cards[mid:]


class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []

    def draw(self):
        return self.hand.pop(0)

    def add(self, cards):
        self.hand.extend(cards)


class GameDB:
    def __init__(self, path='war.db'):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def save_game(self, winner, total_rounds):
        cur = self.conn.execute(
            "INSERT INTO games (played_at, winner, total_rounds) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), winner, total_rounds)
        )
        self.conn.commit()
        return cur.lastrowid

    def save_round(self, game_id, round_num, p1_card, p2_card, winner, was_war):
        self.conn.execute(
            "INSERT INTO rounds (game_id, round_num, p1_card, p2_card, winner, was_war)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (game_id, round_num, str(p1_card), str(p2_card), winner, 1 if was_war else 0)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


def war_draw(player):
    """
    Try to draw 3 face-down cards then 1 face-up. If a player runs
    dry during the face-down phase, their last drawn card becomes
    the face-up card (per the rules). Returns (face_down_list, face_up_card_or_None).
    """
    face_down = []
    for _ in range(3):
        if not player.hand:
            break
        face_down.append(player.draw())

    if player.hand:
        face_up = player.draw()
    elif face_down:
        face_up = face_down.pop()
    else:
        face_up = None  # player is completely out

    return face_down, face_up


def play_round(p1, p2):
    """
    Play one round (battle + any resulting wars). Returns a dict with
    the opening cards, the winner Player object, and whether a war occurred.
    Cards are redistributed to the winner's hand before returning.
    """
    table = []

    p1_card = p1.draw()
    p2_card = p2.draw()
    table.append(p1_card)
    table.append(p2_card)

    # remember the opening cards for the log
    opening_p1 = p1_card
    opening_p2 = p2_card
    was_war = False

    while p1_card.value == p2_card.value:
        was_war = True

        fd1, up1 = war_draw(p1)
        fd2, up2 = war_draw(p2)
        table.extend(fd1)
        table.extend(fd2)

        # check if either player ran out entirely
        if up1 is None and up2 is None:
            # edge case: both players exhaust their hands simultaneously during war
            # give cards to whoever had more to begin (arbitrary but deterministic)
            winner = p1 if len(p1.hand) >= len(p2.hand) else p2
            random.shuffle(table)
            winner.add(table)
            return {'p1_card': opening_p1, 'p2_card': opening_p2,
                    'winner': winner, 'was_war': True}

        if up1 is None:
            table.append(up2)
            random.shuffle(table)
            p2.add(table)
            return {'p1_card': opening_p1, 'p2_card': opening_p2,
                    'winner': p2, 'was_war': True}

        if up2 is None:
            table.append(up1)
            random.shuffle(table)
            p1.add(table)
            return {'p1_card': opening_p1, 'p2_card': opening_p2,
                    'winner': p1, 'was_war': True}

        table.append(up1)
        table.append(up2)
        p1_card = up1
        p2_card = up2

    if p1_card.value > p2_card.value:
        random.shuffle(table)
        p1.add(table)
        return {'p1_card': opening_p1, 'p2_card': opening_p2,
                'winner': p1, 'was_war': was_war}
    else:
        random.shuffle(table)
        p2.add(table)
        return {'p1_card': opening_p1, 'p2_card': opening_p2,
                'winner': p2, 'was_war': was_war}


def play_game(db, verbose=False):
    deck = Deck()
    h1, h2 = deck.split()

    p1 = Player("Player 1")
    p2 = Player("Player 2")
    p1.hand = h1
    p2.hand = h2

    round_log = []
    round_num = 0

    while p1.hand and p2.hand and round_num < MAX_ROUNDS:
        round_num += 1
        result = play_round(p1, p2)
        result['round_num'] = round_num
        round_log.append(result)

        if verbose:
            war_note = " (WAR)" if result['was_war'] else ""
            print(f"  Round {round_num:4d}{war_note}: "
                  f"P1 {result['p1_card']} vs P2 {result['p2_card']} "
                  f"-> {result['winner'].name} wins "
                  f"[P1: {len(p1.hand)} | P2: {len(p2.hand)}]")

    if p1.hand:
        winner = p1
    elif p2.hand:
        winner = p2
    else:
        # hit MAX_ROUNDS without a winner
        winner = p1 if len(p1.hand) >= len(p2.hand) else p2

    game_id = db.save_game(winner.name, round_num)
    for r in round_log:
        db.save_round(game_id, r['round_num'],
                      r['p1_card'], r['p2_card'],
                      r['winner'].name, r['was_war'])

    return game_id, winner.name, round_num


def print_summary(db):
    cur = db.conn.execute(
        "SELECT winner, COUNT(*) as wins FROM games GROUP BY winner ORDER BY wins DESC"
    )
    rows = cur.fetchall()
    print("\n--- Results summary ---")
    for winner, wins in rows:
        print(f"  {winner}: {wins} game(s) won")


def main():
    parser = argparse.ArgumentParser(description="War card game simulator")
    parser.add_argument('--games', type=int, default=1,
                        help='Number of games to simulate (default: 1)')
    parser.add_argument('--db', default='war.db',
                        help='SQLite database path (default: war.db)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print every round to stdout')
    args = parser.parse_args()

    db = GameDB(args.db)

    for i in range(args.games):
        print(f"\nGame {i + 1}...")
        game_id, winner, rounds = play_game(db, verbose=args.verbose)
        print(f"  -> {winner} wins after {rounds} rounds (game id: {game_id})")

    if args.games > 1:
        print_summary(db)

    db.close()


if __name__ == '__main__':
    main()
