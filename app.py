from flask import Flask, render_template, request, Response, stream_with_context
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from war import play_game, GameDB

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/stream')
def stream():
    count = int(request.args.get('count', 50))
    count = max(1, min(count, 1000))

    def generate():
        db = GameDB()
        p1_wins = 0
        p2_wins = 0
        total_rounds = 0

        for i in range(count):
            game_id, winner, rounds = play_game(db)
            if winner == 'Player 1':
                p1_wins += 1
            else:
                p2_wins += 1
            total_rounds += rounds

            payload = json.dumps({
                'game': i + 1,
                'total': count,
                'winner': winner,
                'rounds': rounds,
                'p1_wins': p1_wins,
                'p2_wins': p2_wins,
                'avg_rounds': round(total_rounds / (i + 1)),
            })
            yield f'data: {payload}\n\n'
            time.sleep(0.03)

        yield 'data: {"done":true}\n\n'
        db.close()

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers=headers,
    )


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
