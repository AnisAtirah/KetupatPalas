from __future__ import annotations

from flask import Flask, jsonify, render_template

from ai_service import AIService
from analytics import build_recommendation_context
from config import Config


app = Flask(__name__)
app.config.from_object(Config)

ai_service = AIService(
    api_key=app.config['ILMU_API_KEY'],
    base_url=app.config['ILMU_BASE_URL'],
    model=app.config['ILMU_MODEL'],
)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/api/health')
def health() -> tuple:
    return jsonify({'status': 'ok'}), 200


@app.route('/api/context')
def context() -> tuple:
    ctx = build_recommendation_context()
    return (
        jsonify(
            {
                'zone': ctx.zone,
                'status': ctx.status,
                'current_wait': round(ctx.current_wait, 1),
                'avg_wait': round(ctx.avg_wait, 1),
                'peak_specialization': ctx.peak_specialization,
                'peak_load': round(ctx.peak_load, 2),
            }
        ),
        200,
    )


@app.route('/api/recommendations', methods=['GET'])
def recommendations() -> tuple:
    result = ai_service.generate_suggestions()
    return jsonify(result), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
