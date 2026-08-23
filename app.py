import os
import json
import csv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from ai.llm_engine import LLMEngine
from review.human_review import log_review

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json or {}
        messages = data.get('messages', [])
        
        prompt_path = os.path.join(os.path.dirname(__file__), 'prompts', 'diagnose_prompt.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            system_prompt = f.read()

        # Format chat history into a single string for LLMEngine
        chat_text = f"[SYSTEM INSTRUCTIONS]\n{system_prompt}\n\n[CONVERSATION HISTORY]\n"
        for msg in messages:
            role = msg.get('role', 'user').upper()
            content = msg.get('content', '')
            chat_text += f"{role}: {content}\n"
            
        chat_text += "ASSISTANT: "

        # Call LLM
        ai_output = LLMEngine.generate_diagnosis(chat_text)

        return jsonify({
            'status': 'success',
            'ai_diagnosis': ai_output
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/review', methods=['POST'])
def review():
    try:
        data = request.json or {}
        decision = data.get('decision', 'ACCEPTED')
        feedback = data.get('feedback', '')
        ai_diagnosis = data.get('ai_diagnosis', {})

        log_review("chat", ai_diagnosis, decision, feedback)
        
        return jsonify({
            'status': 'success',
            'message': f'Human review recorded: {decision}',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def stats():
    log_file = os.path.join(os.path.dirname(__file__), 'logs', 'responsible_ai_log.csv')
    logs = []
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logs = list(reader)
            
    decisions = {'ACCEPTED': 0, 'EDITED': 0, 'REJECTED': 0}
    for l in logs:
        d = l.get('human_decision', '')
        if d in decisions:
            decisions[d] += 1
            
    return jsonify({
        'total_reviews': len(logs),
        'decisions': decisions
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
