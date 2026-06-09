from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import random
import os
import requests
import xml.etree.ElementTree as ET
from geopy.geocoders import Nominatim

app = Flask(__name__)
app.secret_key = "your_super_secret_key"

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ==========================================
# 1. 資料庫初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # 🔥 強制轟掉舊資料表，確保資料庫欄位與全新架構完美對齊
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS posts")
    cursor.execute("DROP TABLE IF EXISTS comments")
    
    # 使用者資料表 (密碼制)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    # 自動內建管理員，密碼固定為：037
    cursor.execute("SELECT id FROM users WHERE password = '037'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (password, username, is_admin) VALUES ('037', '系統管理員', 1)")
    
    # 動態貼文資料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            image_path TEXT,
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 貼文留言資料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id)
        )
    ''')
    
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

# ==========================================
# 2. 帳號與密碼系統路由 (登入、註冊、登出)
# ==========================================

@app.route('/welcome')
def welcome():
    if 'password' in session:
        return redirect(url_for('index'))
    return render_template('welcome.html')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    if username:
        if username == "系統管理員":
            return render_template('welcome.html', error="不能使用此暱稱，請換一個。")
            
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        while True:
            new_password = str(random.randint(100, 999))
            cursor.execute("SELECT id FROM users WHERE password = ?", (new_password,))
            if not cursor.fetchone():
                break
                
        cursor.execute("INSERT INTO users (password, username, is_admin) VALUES (?, ?, 0)", (new_password, username))
        conn.commit()
        conn.close()
        
        session['password'] = new_password
        session['username'] = username
        session['is_admin'] = 0
        
        return render_template('welcome.html', new_password=new_password, username=username)
    return redirect(url_for('welcome'))

@app.route('/login', methods=['POST'])
def login():
    input_password = request.form.get('password')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, is_admin FROM users WHERE password = ?", (input_password,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['password'] = input_password
        session['username'] = user[0]
        session['is_admin'] = user[1]
        return redirect(url_for('index'))
    else:
        return render_template('welcome.html', error="找不到這組密碼，請確認是否輸入錯誤。")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('welcome'))

# ==========================================
# 3. 免 API 實時氣象與焦點新聞功能 (爬蟲/RSS)
# ==========================================
def get_weather_by_location(location_name):
    try:
        geolocator = Nominatim(user_agent="my_taiwan_school_project_2026")
        location = geolocator.geocode(location_name)
        if not location: return {"error": "找不到這個地名。"}
        lat, lon = location.latitude, location.longitude
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(weather_url, timeout=5).json()
        if "current_weather" in response:
            current = response["current_weather"]
            weather_dict = {0: "☀️ 晴朗無雲", 1: "🌤️ 晴到多雲", 2: "⛅ 多雲時晴", 3: "☁️ 陰天", 45: "🌫️ 有霧", 61: "🌧️ 小雨", 63: "🌧️ 陣雨", 95: "⛈️ 雷陣雨"}
            return {"success": True, "place": location.address.split(',')[0], "temp": current["temperature"], "weather": weather_dict.get(current["weathercode"], "☁️ 多雲陰天")}
    except: return {"error": "氣象系統連線忙碌中。"}

def get_today_news():
    news_list = []
    try:
        rss_url = "https://tw.news.yahoo.com/rss/realtime"
        response = requests.get(rss_url, timeout=5)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text
            link = item.find('link').text
            description = item.find('description').text if item.find('description') is not None else "點擊查看詳情。"
            if "<" in description: description = description.split('<')[0]
            news_list.append({"title": title, "link": link, "description": description.strip()})
    except:
        news_list = [{"title": "最新重大新聞加載中...", "link": "#", "description": "請重新整理網頁嘗試重新載入新聞。"}]
    return news_list

# ==========================================
# 4. 🤖 核心修改：系統專屬「關鍵字智慧語言包」問答路由
# ==========================================
@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    if 'password' not in session:
        return jsonify({"error": "請先登入系統"})
        
    user_prompt = request.json.get('prompt', '').strip()
    if not user_prompt:
        return jsonify({"reply": "你想問我什麼呢？"})
        
    # 🎯 專案導覽問答語言包核心 (零資源消耗、秒回、絕不當機)
    LANGUAGE_PACK = {
        "功能": "🤖 本網站功能非常全方位！包含：\n1. 3位數隨機密碼登入機制\n2. 動態圖片發布系統\n3. 文章即時點讚功能\n4. 灰色調留言回覆區\n5. 管理員專屬刪除後台\n6. 免 API 實時天氣定位\n7. 免 API Yahoo 焦點新聞摺疊特區",
        "功用": "🤖 本網站設計初衷是為了提供班級一個兼具隱私、社交與生活實用性的『全方位門戶網站』。除了基本的交流，還能隨時掌握天氣與時事！",
        "特色": "🤖 本專案最大的特色就是『100% 免外部付費 API 金鑰』！我們純粹利用後台的網頁地理分析與 XML RSS 爬蟲技術，完美實現了零成本的即時天氣與重大新聞功能。",
        "密碼": "🤖 為了便利同學，系統採用『3位數隨機隨發密碼』。第一次來的同學只需輸入暱稱即可配發密碼；下次登入只需輸入該 3 位數即可自動進到留言板，既安全又好記！",
        "天氣": "🤖 想查詢天氣，請利用右側綠色的『地名轉座標氣象站』！直接輸入台灣地名（例如：中壢、墾丁），後台會自動將地名轉為地理座標，並撈回當下的氣溫與氣候狀況喔！",
        "新聞": "🤖 畫面上方的橘黃色區塊是『今日重大焦點新聞特區』。預設只顯示吸引人的標題，點擊標題後會像抽屜一樣展開，詳細說明這則重大焦點發生了什麼事情！",
        "管理員": "🤖 系統內建了隱藏的超級管理金鑰『037』。在歡迎頁面輸入 037 登入後，畫面上方會開啟紅色的帳號管理面板，並且每條動態、留言旁邊都會出現刪除按鈕，具備最高管理權限！",
        "帳號": "🤖 本網站的管理員（密碼 037）擁有專屬控制台，可以即時查看全班註冊的暱稱與對應密碼，並且可以一鍵『註銷帳號』，強制將違規使用者移除系統！",
        "作者": "🤖 這款功能超強大、版面精美的全方位動態班級留言板系統是由你親手開發的期末大作！拿去繳交絕對是滿分水準！",
        "你好": f"🤖 你好呀，{session.get('username', '同學')}！我是常駐在留言板的課業小助手，今天過得如何？輸入『功能』或『特色』可以了解我能幫你做什麼喔！",
        "哈囉": f"🤖 嗨！你好，{session.get('username', '同學')}！很高興為你服務。有什麼關於這個專題系統的問題想問我嗎？"
    }
    
    # 進行關鍵字比對
    user_input_lower = user_prompt.lower()
    matched_reply = None
    
    for keyword, response_content in LANGUAGE_PACK.items():
        if keyword in user_input_lower:
            matched_reply = response_content
            break
            
    # 如果沒命中任何關鍵字，給予智慧引導
    if not matched_reply:
        matched_reply = "🤖 收到你的提問了！我是留言板專屬的語言包小助手。你可以試著輸入：『功能』、『特色』、『密碼』、『天氣』、『新聞』或『管理員』，我會為你詳細說明相關的系統架構喔！"
        
    return jsonify({"reply": matched_reply})

# ==========================================
# 5. 主要首頁與社群路由
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'password' not in session:
        return redirect(url_for('welcome'))
        
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = session.get('username')
        message = request.form.get('message')
        file = request.files.get('image')
        image_path = None
        if file and file.filename != '':
            filename = f"{random.randint(1000,9999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"/static/uploads/{filename}"
        if message or image_path:
            cursor.execute("INSERT INTO posts (name, message, image_path, likes) VALUES (?, ?, ?, 0)", (name, message, image_path))
            conn.commit()
            return redirect(url_for('index'))

    weather_info = None
    search_location = request.args.get('location')
    if search_location: weather_info = get_weather_by_location(search_location)

    current_news = get_today_news()

    cursor.execute("SELECT id, name, message, image_path, likes, created_at FROM posts ORDER BY id DESC")
    raw_posts = cursor.fetchall()
    posts = []
    for post in raw_posts:
        post_id = post[0]
        cursor.execute("SELECT name, content, created_at, id FROM comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
        posts.append({'id': post[0], 'name': post[1], 'message': post[2], 'image_path': post[3], 'likes': post[4], 'created_at': post[5], 'comments': cursor.fetchall()})
        
    users_list = []
    if session.get('is_admin') == 1:
        cursor.execute("SELECT id, password, username FROM users WHERE is_admin = 0 ORDER BY id DESC")
        users_list = cursor.fetchall()
        
    conn.close()
    return render_template('index.html', posts=posts, users=users_list, weather=weather_info, news=current_news, current_user=session.get('username'))

# ==========================================
# 6. 管理員專屬與互動功能路由
# ==========================================
@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if 'password' not in session: return redirect(url_for('welcome'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'password' not in session: return redirect(url_for('welcome'))
    name = session.get('username')
    content = request.form.get('content')
    if content:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO comments (post_id, name, content) VALUES (?, ?, ?)", (post_id, name, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete_post/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if session.get('is_admin') != 1: return redirect(url_for('welcome'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('is_admin') != 1: return redirect(url_for('welcome'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)