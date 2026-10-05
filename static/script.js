document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity .4s, transform .4s";
            el.style.opacity = "0";
            el.style.transform = "translateY(-5px)";
            setTimeout(() => el.remove(), 450);
        }, 4500);
    });

    document.querySelectorAll("form").forEach((form) => {
        form.addEventListener("submit", () => {
            const button = form.querySelector('button[type="submit"]');
            if (button && !button.dataset.noLock) {
                setTimeout(() => {
                    button.disabled = true;
                    button.style.opacity = ".7";
                }, 0);
            }
        });
    });

    // Animate dashboard progress bars after load.
    document.querySelectorAll(".progress span").forEach((bar) => {
        const width = bar.style.width;
        bar.style.width = "0";
        setTimeout(() => {
            bar.style.transition = "width 1s ease";
            bar.style.width = width;
        }, 120);
    });
});
