from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import threading
import json
import os
import time

app = Flask(__name__)
STORAGE_FILE = "uid_storage.json"
lock = threading.Lock()

def ensure_file():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "w") as f:
            json.dump({}, f)

def load_uids():
    ensure_file()
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def save_uids(uids):
    with open(STORAGE_FILE, "w") as f:
        json.dump(uids, f, default=str)

def cleanup_expired():
    while True:
        with lock:
            uids = load_uids()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            expired = [uid for uid, exp in uids.items() if exp != "permanent" and exp <= now]
            for uid in expired:
                del uids[uid]
                print(f"UID منتهي وتم حذفه: {uid}")
            save_uids(uids)
        time.sleep(5)

@app.route('/')
def index():
    return "Subscription Server is Running."

@app.route('/add_uid', methods=['GET'])
def add_uid_api():
    return jsonify(add_uid(
        uid=request.args.get('uid'),
        time_value=request.args.get('time'),
        time_type=request.args.get('type'),
        permanent=request.args.get('permanent', 'false').lower() == 'true'
    ))

@app.route('/get_time/<uid>', methods=['GET'])
def get_time(uid):
    with lock:
        uids = load_uids()
        expiration = uids.get(uid)

        if not expiration:
            return jsonify({
                'uid': uid,
                'remaining_time': {
                    'days': 999,
                    'hours': 23,
                    'minutes': 59,
                    'seconds': 59
                }
            })

        if expiration == "permanent":
            return jsonify({
                'uid': uid,
                'remaining_time': {
                    'days': 99999,
                    'hours': 23,
                    'minutes': 59,
                    'seconds': 59
                }
            })

        expiration_time = datetime.strptime(expiration, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()

        if now > expiration_time:
            return jsonify({
                'uid': uid,
                'remaining_time': {
                    'days': 0,
                    'hours': 0,
                    'minutes': 0,
                    'seconds': 0
                }
            })

        remaining = expiration_time - now
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return jsonify({
            'uid': uid,
            'remaining_time': {
                'days': days,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds
            }
        })

def add_uid(uid=None, time_value=None, time_type=None, permanent=False):
    if not uid:
        return {'error': 'Missing UID'}

    if permanent:
        expiration = "permanent"
    else:
        if not time_value or not time_type:
            return {'error': 'Missing time or type'}
        value = int(time_value)
        now = datetime.now()
        if time_type == "seconds":
            expiration = now + timedelta(seconds=value)
        elif time_type == "days":
            expiration = now + timedelta(days=value)
        elif time_type == "months":
            expiration = now + timedelta(days=value * 30)
        elif time_type == "years":
            expiration = now + timedelta(days=value * 365)
        else:
            return {'error': 'Invalid type'}
        expiration = expiration.strftime('%Y-%m-%d %H:%M:%S')

    with lock:
        uids = load_uids()
        uids[uid] = expiration
        save_uids(uids)

    return {'uid': uid, 'expires_at': expiration}

# ========== البداية الفعلية ==============
if __name__ == "__main__":
    ensure_file()
    threading.Thread(target=cleanup_expired, daemon=True).start()

    print("سيرفر الاشتراكات يعمل الآن على http://0.0.0.0:50022")
    uid = input("أدخل UID لتفعيله: ").strip()
    is_permanent = input("هل الاشتراك دائم؟ (yes/no): ").strip().lower()

    if is_permanent == 'yes':
        result = add_uid(uid=uid, permanent=True)
    else:
        time_value = input("أدخل قيمة الوقت (مثلاً 1 أو 30): ").strip()
        time_type = input("نوع الوقت (seconds, days, months, years): ").strip()
        result = add_uid(uid=uid, time_value=time_value, time_type=time_type, permanent=False)

    print("تم التفعيل بنجاح:")
    print(result)

    app.run(host="0.0.0.0", port=50022)