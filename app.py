from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)


# 初始化資料庫：如果沒有資料表，就建立一個
def init_db():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                image_url TEXT,
                created_at TEXT NOT NULL,
                likes INTEGER DEFAULT 0
            )
        """)
        conn.commit()


# 每次啟動程式時，確保資料庫已經準備好
init_db()


@app.route("/")
def home():
    # 從 SQLite 資料庫讀取所有貼文 (依時間倒序排列)
    with sqlite3.connect("database.db") as conn:
        # 讓讀出來的資料可以像字典一樣透過欄位名稱取值
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM posts ORDER BY id DESC")
        posts = cursor.fetchall()

    return render_template("index.html", posts=posts)


@app.route("/submit_post", methods=["POST"])
def submit_post():
    user = request.form.get("username")
    text = request.form.get("content")
    img_url = request.form.get("image_url")

    # 取得現在的時間，並格式化為 年-月-日 時:分
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 將資料寫入 SQLite 真實資料庫
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO posts (username, content, image_url, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (user, text, img_url, current_time),
        )
        conn.commit()

    return redirect(url_for("home", _anchor="board"))


# 新增的按讚功能 API
@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        # 將指定 ID 的貼文按讚數 + 1
        cursor.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        conn.commit()

    return redirect(url_for("home", _anchor="board"))


if __name__ == "__main__":
    app.run(debug=True)
