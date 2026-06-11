from flask import Flask, render_template, request, redirect, url_for, session
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
    
    # 這裡保留你原本的強制重置邏輯，確保結構更新
    cursor.execute("DROP TABLE IF EXISTS users")
    cursor.execute("DROP TABLE IF EXISTS posts")
    cursor.execute("DROP TABLE IF EXISTS comments")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute("SELECT id FROM users WHERE password = '037'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (password, username, is_admin) VALUES ('037', '系統管理員', 1)")
    
    # 【改動點】：在 posts 表中加入 location 欄位
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT NOT NULL,
            image_path TEXT,
            location TEXT,
            likes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
# 2. 帳號與密碼系統路由 (保持不變)
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
# 3. 🌤️ 天氣與新聞功能 (保持不變)
# ==========================================
def get_weather_by_location(location_name):
    try:
        geolocator = Nominatim(user_agent="my_taiwan_school_project_2026")
        location = geolocator.geocode(location_name)
        if not location:
            return {"error": "找不到這個地名，請輸入更具體的地點。"}
        lat, lon = location.latitude, location.longitude
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(weather_url, timeout=5).json()
        if "current_weather" in response:
            current = response["current_weather"]
            weather_dict = {0: "☀️ 晴朗無雲", 1: "🌤️ 晴到多雲", 2: "⛅ 多雲時晴", 3: "☁️ 陰天", 45: "🌫️ 有霧", 61: "🌧️ 小雨", 63: "🌧️ 陣雨", 65: "🌧️ 大雨", 80: "🌦️ 短暫陣雨", 95: "⛈️ 雷陣雨"}
            return {
                "success": True, "place": location.address.split(',')[0], "lat": round(lat, 4), "lon": round(lon, 4),
                "temp": current["temperature"], "weather": weather_dict.get(current["weathercode"], "☁️ 多雲陰天"), "wind": current["windspeed"]
            }
    except:
        return {"error": "氣象系統連線忙碌中。"}
    return {"error": "無法取得天氣資訊。"}

def get_today_news():
    news_list = []
    try:
        rss_url = "https://tw.news.yahoo.com/rss/realtime"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(rss_url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        root = ET.fromstring(response.text)
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            link = item.find('link').text
            description = item.find('description').text if item.find('description') is not None else "點擊進入查看詳細內容說明。"
            if "<" in description:
                description = description.split('<')[0]
            news_list.append({"title": title, "link": link, "description": description.strip()})
    except Exception as e:
        news_list = [{"title": "新聞系統載入中...", "link": "#", "description": "請重新整理網頁以嘗試重新載入最新重大新聞。"}]
    return news_list

# ==========================================
# 5. 留言板主要功能 (整合打卡)
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
        # 【改動點】：取得 location
        location = request.form.get('location')
        
        file = request.files.get('image')
        image_path = None
        if file and file.filename != '':
            filename = f"{random.randint(1000,9999)}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"/static/uploads/{filename}"
        
        if message or image_path:
            # 【改動點】：SQL INSERT 加入 location
            cursor.execute("INSERT INTO posts (name, message, image_path, location, likes) VALUES (?, ?, ?, ?, 0)", 
                           (name, message, image_path, location))
            conn.commit()
            return redirect(url_for('index'))

    weather_info = None
    search_location = request.args.get('location')
    if search_location:
        weather_info = get_weather_by_location(search_location)

    current_news = get_today_news()

    # 【改動點】：讀取貼文 SQL 加入 location
    cursor.execute("SELECT id, name, message, image_path, location, likes, created_at FROM posts ORDER BY id DESC")
    raw_posts = cursor.fetchall()
    
    posts = []
    for post in raw_posts:
        post_id = post[0]
        cursor.execute("SELECT name, content, created_at, id FROM comments WHERE post_id = ? ORDER BY id ASC", (post_id,))
        comments = cursor.fetchall()
        
        posts.append({
            'id': post[0], 'name': post[1], 'message': post[2], 'image_path': post[3], 'location': post[4], 'likes': post[5], 'created_at': post[6], 'comments': comments
        })
        
    users_list = []
    if session.get('is_admin') == 1:
        cursor.execute("SELECT id, password, username FROM users WHERE is_admin = 0 ORDER BY id DESC")
        users_list = cursor.fetchall()
        
    conn.close()
    return render_template('index.html', posts=posts, users=users_list, weather=weather_info, news=current_news, current_user=session.get('username'))

# ==========================================
# 6. 管理員與按讚刪除功能路由 (保持不變)
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

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if session.get('is_admin') != 1: return redirect(url_for('welcome'))
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
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