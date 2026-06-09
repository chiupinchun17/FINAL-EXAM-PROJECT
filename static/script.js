// 導航連結平滑滾動
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute("href"));
        if (target) {
            target.scrollIntoView({
                behavior: "smooth",
                block: "start",
            });
        }
    });
});

// Hero 按鈕點擊事件
document.querySelector(".hero .btn")?.addEventListener("click", () => {
    document.querySelector("#about").scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
});

// 聯絡表單提交
document.querySelector(".contact-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = e.target.querySelector('input[type="text"]').value;
    const email = e.target.querySelector('input[type="email"]').value;
    const message = e.target.querySelector("textarea").value;

    if (name && email && message) {
        alert(`謝謝 ${name}！我們已收到您的訊息，將盡快回覆您。`);
        e.target.reset();
    }
});

// 頁面加載時的初始化
document.addEventListener("DOMContentLoaded", () => {
    console.log("網站已加載");
});
