# War Simulator

## Project structure

```
war.py          # core simulator and DB logic
app.py          # Flask web app
schema.sql      # standalone DDL reference
templates/
  index.html
static/
  css/main.css
  js/main.js
```

## How to run

### Web app (recommended)

Requires Python 3+ and Flask.

```bash
pip install flask
python3 app.py
```

Then open `http://127.0.0.1:5000`. Enter a number of games and click **Run** — results stream in live and the chart updates as each game finishes.

### CLI

No dependencies beyond the standard library.

```bash
# Single game
python3 war.py

# Run 10 games, print every round
python3 war.py --games 10 --verbose

# Use a custom database path
python3 war.py --games 50 --db results.db
```

The database file (`war.db` by default) is created automatically on first run.

## Design decisions

### Classes

| Class | Responsibility |
|---|---|
| `Card` | Value object — rank, suit, and numeric value for comparison |
| `Deck` | Builds a shuffled 52-card deck and splits it in half |
| `Player` | Owns a hand (a `deque`-style list) and exposes `draw` / `add` |
| `GameDB` | Thin SQLite wrapper; creates the schema and exposes two write methods |

Game logic lives in two module-level functions (`play_round`, `play_game`) rather than a `Game` class. The state is just the two players and their hands, which doesn't benefit from being wrapped in an object.

### War phase

When a tie occurs `play_round` enters a loop:
1. Each player draws up to 3 face-down cards.
2. If a player runs dry during step 1, their last drawn card becomes the face-up card (matching the rule that lets you "still have a chance to stay in the game").
3. If a player has no cards at all, the opponent wins everything on the table.
4. The new face-up cards are compared; repeat if still tied.

### Randomizing the won pile

Cards won each round are shuffled before being added to the bottom of the winner's hand. This prevents deterministic cycling where the same card order loops forever.

### Safety limit

`MAX_ROUNDS = 10000` guards against infinite games (which are theoretically possible). In practice games end well before a few thousand rounds.

### Database schema

```sql
games (id, played_at, winner, total_rounds)
rounds (id, game_id, round_num, p1_card, p2_card, winner, was_war)
```

- `winner` in both tables stores the player name string directly. A players table would be over-engineered for a two-player game.
- `was_war` is a boolean flag (0/1). The face-down cards are not persisted because they're irrelevant to the outcome and would bloat the log considerably.
- `p1_card` / `p2_card` store the *opening* cards each player put down at the start of the round, not the final face-up cards from a war. This gives a clear per-round record without ambiguity.
- Cards are stored as full human-readable strings (e.g. `"K of Hearts"`) rather than a compact code or integer. The rounds table is a log first and foremost, so being able to read it with a plain `SELECT` outweighs the minor storage cost. If volume were a concern each card could be encoded as a single byte (0–51 covers the whole deck), but for a game simulator the difference is negligible.

### How winners are stored

- **Round winner**: the `winner` column in `rounds` is set to the player name that won that battle (including any wars it contained).
- **Game winner**: the `winner` column in `games` is set to the player name after their opponent runs out of cards.

## Web app design

The Flask app (`app.py`) streams game results to the browser using **Server-Sent Events** (SSE). When you click Run, the browser opens an `EventSource` to `/stream?count=N`. The server runs games one at a time and yields a JSON event after each one — no polling required. The frontend updates the Chart.js line chart and stats panel incrementally as events arrive.

For large runs (200+ games) the chart samples points rather than plotting every game, keeping rendering fast without losing the overall shape of the data.

Static assets live in `static/css/` and `static/js/` and are referenced via Flask's `url_for` helper. The UI is built with Bootstrap 5.3 dark theme with a small amount of custom CSS for things Bootstrap doesn't cover (chart container height, player colors, log entry layout).

## What I'd improve with more time

- **Player names as input** — currently hardcoded to "Player 1" / "Player 2".
- **Round-level war detail** — log each individual war exchange within a round as its own row (a `wars` table) for richer replay.
- **Concurrent games** — the DB writes are synchronous; connection pooling or async writes would matter at scale.
- **Tests** — unit tests for `play_round` edge cases (both players go dry simultaneously, single-card war, etc.).
- **Game history page** — a second route that queries the DB and shows past results in a table.
- **Compact card encoding** — at scale, storing cards as a single byte (0–51) instead of a full string like `"K of Hearts"` would meaningfully reduce the size of the `rounds` table. With ~300 rounds per game, a high-volume deployment logging millions of games would see significant storage savings with no loss of information, just a decode step on read.
