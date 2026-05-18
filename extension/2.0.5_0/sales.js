// FAQ
document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
        const item = btn.parentElement;
        const isOpen = item.classList.contains('active');
        document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
        if (!isOpen) item.classList.add('active');
    });
});

// Pricing toggle (mensal/anual)
const toggleBtns = document.querySelectorAll('.toggle-btn');
toggleBtns.forEach((btn, i) => {
    btn.addEventListener('click', () => {
        toggleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const monthly = document.querySelectorAll('.plan-monthly');
        const annual  = document.querySelectorAll('.plan-annual');
        if (i === 0) {
            monthly.forEach(el => el.style.display = '');
            annual.forEach(el => el.style.display = 'none');
        } else {
            monthly.forEach(el => el.style.display = 'none');
            annual.forEach(el => el.style.display = '');
        }
    });
});

// Esconder planos anuais inicialmente
document.querySelectorAll('.plan-annual').forEach(el => el.style.display = 'none');

// Animate on scroll
const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animationPlayState = 'running';
            observer.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.animate-in').forEach(el => {
    el.style.animationPlayState = 'paused';
    observer.observe(el);
});
