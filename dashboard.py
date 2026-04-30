import os
from flask import Flask, render_template, send_from_directory, abort, redirect, url_for

app = Flask(__name__)
RESULTS_DIR = os.path.join(os.getcwd(), 'results')

def get_sessions():
    """List all test session folders in results/"""
    if not os.path.exists(RESULTS_DIR):
        return []
    sessions = [d for d in os.listdir(RESULTS_DIR) if os.path.isdir(os.path.join(RESULTS_DIR, d)) and d.startswith('test_')]
    return sorted(sessions, reverse=True)

@app.route('/')
def index():
    sessions = get_sessions()
    if sessions:
        return redirect(url_for('view_session', session_name=sessions[0]))
    return render_template('dashboard.html', sessions=[], current_session=None, data={'charts':[], 'reports':[], 'logs':[]})

@app.route('/session/<session_name>')
def view_session(session_name):
    sessions = get_sessions()
    if session_name not in sessions:
        abort(404)
    
    session_path = os.path.join(RESULTS_DIR, session_name)
    files = os.listdir(session_path)
    
    # Categorize files
    data = {
        'charts': [f for f in files if f.endswith('.png')],
        'reports': [f for f in files if f.endswith('.xlsx')],
        'logs': [f for f in files if f.endswith('.json') or f.endswith('.txt')],
    }
    
    return render_template('dashboard.html', 
                           sessions=sessions, 
                           current_session=session_name,
                           data=data)

@app.route('/files/<session_name>/<filename>')
def get_file(session_name, filename):
    return send_from_directory(os.path.join(RESULTS_DIR, session_name), filename)

if __name__ == '__main__':
    print("Dashboard is running on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
