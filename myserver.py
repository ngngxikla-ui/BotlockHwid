import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Server is running!"

def run():
    # ดึงค่า Port จากระบบของ Render อัตโนมัติ (ถ้าไม่มีจะใช้ 8080 ตามเดิม)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def server_on():
    t = Thread(target=run)
    t.start()
