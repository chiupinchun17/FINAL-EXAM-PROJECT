// Smooth scrolling for navigation links
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

// Contact form submission
const contactForm = document.querySelector(".contact-form");
if (contactForm) {
    contactForm.addEventListener("submit", function (e) {
        e.preventDefault();
        alert("感謝您的訊息！我們會盡快回覆您。");
        this.reset();
    });
}

// Button click handler
const buttons = document.querySelectorAll('.btn:not([type="submit"])');
buttons.forEach((btn) => {
    btn.addEventListener("click", function () {
        console.log("按鈕被點擊");
    });
});
