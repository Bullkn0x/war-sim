-- War Card Game Schema
-- Each row in `games` is one full game (deal to finish).
-- Each row in `rounds` is one battle (which may have included a war).
-- The opening cards each player played are stored so the round history
-- is self-contained without needing to replay the game log.

CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    played_at     TEXT    NOT NULL,   -- ISO-8601 timestamp
    winner        TEXT    NOT NULL,   -- "Player 1" or "Player 2"
    total_rounds  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rounds (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id   INTEGER NOT NULL REFERENCES games(id),
    round_num INTEGER NOT NULL,
    p1_card   TEXT    NOT NULL,   -- e.g. "A of Spades"
    p2_card   TEXT    NOT NULL,
    winner    TEXT    NOT NULL,   -- "Player 1" or "Player 2"
    was_war   INTEGER NOT NULL DEFAULT 0   -- 1 if round involved at least one war
);
