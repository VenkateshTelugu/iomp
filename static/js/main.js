// main.js

document.addEventListener('DOMContentLoaded', () => {
    // Handle login button click
    document.getElementById('loginBtn')?.addEventListener('click', async () => {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (response.ok) {
            // Redirect to home page on successful login
            window.location.href = 'home.html';
        } else {
            // Display error message
            alert('You do not have an account. Please sign up first.');
        }
    });
});




// main.js

document.addEventListener('DOMContentLoaded', () => {
    // Handle registration button click
    document.getElementById('registerBtn')?.addEventListener('click', async () => {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        const response = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const messageDiv = document.getElementById('message');
        if (response.ok) {
            // Redirect to login page on successful registration
            messageDiv.textContent = "Registration successful! Please login.";
            messageDiv.style.color = "green";
            setTimeout(() => {
                window.location.href = '/login';  // Redirect to login page
            }, 2000);
        } else {
            const data = await response.json();
            messageDiv.textContent = data.message;  // Display error message
        }
    });
});

