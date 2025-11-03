from flask import Flask, render_template, jsonify
import os
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save', methods=['POST'])
def save():
    data = {'status': 'success', 'message': 'File created successfully'}
    with open('merge_resolve.json', 'w') as f:
        json.dump(data, f)
    return jsonify(data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)