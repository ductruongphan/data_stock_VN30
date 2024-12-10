
const themeToggle = document.querySelector('.theme-toggle');
const body = document.body;

if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark-mode');
}

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    if (body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
});

function updateClock() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const date = now.toLocaleDateString('vi-VN', options);
    const time = now.toLocaleTimeString('vi-VN');
    
    document.getElementById('clock').innerHTML = `${date} - ${time}`;
}

setInterval(updateClock, 1000);
updateClock();

function performSearch() {
    const query = document.getElementById('search-input').value;
    alert('Bạn đã tìm kiếm: ' + query.toUpperCase());
}

const menuToggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('.menu');

menuToggle.addEventListener('click', () => {
    menu.classList.toggle('show');
});


