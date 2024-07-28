from flask import Flask, render_template, request, make_response
import os
import sqlite3
import csv
import io
import time
import shutil
import tempfile

app = Flask(__name__)

def copy_database_to_temp(path):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, os.path.basename(path))
    shutil.copy2(path, temp_path)
    return temp_path

def get_history(browser):
    history = []
    path = None

    if browser == 'chrome':
        path = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data\Default\History'
    elif browser == 'edge':
        path = os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data\Default\History'
    elif browser == 'tor':
        path = r'C:\Users\prath\Desktop\Tor Browser\Browser\TorBrowser\Data\Browser\profile.default\places.sqlite'
    elif browser == 'opera':
        path = os.path.expanduser('~') + r'\AppData\Roaming\Opera Software\Opera Stable\Default\History'
    elif browser == 'brave':
        path = os.path.expanduser('~') + r'\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\History'
    elif browser == 'firefox':
        path = os.path.expanduser('~') + r'\AppData\Roaming\Mozilla\Firefox\Profiles\<your-profile-folder>\places.sqlite'  # Update with the actual profile folder

    if path and os.path.exists(path):
        retries = 5
        while retries > 0:
            try:
                # Copy the database file to a temporary location
                temp_path = copy_database_to_temp(path)

                conn = sqlite3.connect(f'file:{temp_path}?mode=ro', uri=True)
                cursor = conn.cursor()
                if browser == 'tor' or browser == 'firefox':
                    cursor.execute("SELECT url, title, visit_count, datetime(last_visit_date/1000000, 'unixepoch', 'localtime') as last_visit FROM moz_places")
                else:
                    cursor.execute("SELECT url, title, visit_count, datetime(last_visit_time/1000000-11644473600, 'unixepoch', 'localtime') as last_visit FROM urls")
                history = cursor.fetchall()
                conn.close()
                os.remove(temp_path)  # Remove the temporary file after use
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    retries -= 1
                    time.sleep(1)
                else:
                    raise
        if retries == 0:
            raise sqlite3.OperationalError("Database is locked after multiple attempts")
    
    return history

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/view_history', methods=['POST'])
def view_history():
    browser = request.form['browser']
    chrome_history = get_history('chrome') if browser == 'chrome' else []
    edge_history = get_history('edge') if browser == 'edge' else []
    tor_history = get_history('tor') if browser == 'tor' else []
    opera_history = get_history('opera') if browser == 'opera' else []
    brave_history = get_history('brave') if browser == 'brave' else []
    firefox_history = get_history('firefox') if browser == 'firefox' else []

    return render_template('view_history.html', 
                           chrome_history=chrome_history, 
                           edge_history=edge_history, 
                           tor_history=tor_history,
                           opera_history=opera_history,
                           brave_history=brave_history,
                           firefox_history=firefox_history)

@app.route('/download_history', methods=['POST'])
def download_history():
    browser = request.form['browser']
    history = get_history(browser)
    
    if not history:
        return "No history available for download", 404

    # Create a CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['URL', 'Title', 'Visit Count', 'Last Visit Time'])
    writer.writerows(history)

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={browser}_history.csv'
    response.headers['Content-type'] = 'text/csv'
    
    return response

if __name__ == '__main__':
    app.run(debug=True)
