from __future__ import annotations

from flask import Flask, jsonify, render_template

from ai_service import AIService
from analytics import build_recommendation_context, build_cost_efficiency_comparison
from config import Config
from costvsefficiency import simulate_once

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
def health():
    return jsonify({'status': 'ok'}), 200


@app.route('/api/context')
def context():
    ctx = build_recommendation_context()
    return jsonify({
        'zone': ctx.zone,
        'status': ctx.status,
        'current_wait': round(ctx.current_wait, 1),
        'avg_wait': round(ctx.avg_wait, 1),
        'peak_specialization': ctx.peak_specialization,
        'peak_load': round(ctx.peak_load, 2),
        'available_beds': ctx.available_beds,
        'available_doctors': ctx.available_doctors,
        'available_nurses': ctx.available_nurses,
        'bed_occupancy': round(ctx.bed_occupancy * 100, 1),
        'today_appointments': ctx.today_appointments,
    }), 200


@app.route('/api/recommendations')
def recommendations():
    result = ai_service.generate_suggestions()
    return jsonify(result), 200


@app.route('/api/cost-efficiency')
def cost_efficiency():
    data = build_cost_efficiency_comparison()
    return jsonify(data), 200


@app.route('/api/simulate')
def simulate():
    data = simulate_once("normal")
    return jsonify({
        'cost_change':        data['cost_change'],
        'waiting_time_change': data['waiting_time_change'],
        'current_cost':       data['current_cost'],
        'current_waiting_time': data['current_waiting_time'],
        'patients_served':    data['patients_served'],
        'interpretation':     data['interpretation'],
        'insight':            data['insight'],
        'state':              data['state'],
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)