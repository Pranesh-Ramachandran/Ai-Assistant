document.addEventListener('DOMContentLoaded', function() {
    const loginTab = document.getElementById('loginTab');
    const registerTab = document.getElementById('registerTab');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const authMessage = document.getElementById('authMessage');
    const loginEmail = document.getElementById('loginEmail');

    // Tab switching
    loginTab.addEventListener('click', function() {
        switchTab('login');
    });

    registerTab.addEventListener('click', function() {
        switchTab('register');
    });

    function switchTab(tab) {
        setMessage('', '');
        if (tab === 'login') {
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
            loginForm.classList.add('active');
            registerForm.classList.remove('active');
            if (loginEmail) loginEmail.focus();
        } else {
            registerTab.classList.add('active');
            loginTab.classList.remove('active');
            registerForm.classList.add('active');
            loginForm.classList.remove('active');
            const registerName = document.getElementById('registerName');
            if (registerName) registerName.focus();
        }
    }

    if (loginEmail) {
        loginEmail.focus();
    }

    function setMessage(type, text) {
        if (!authMessage) return;
        authMessage.classList.remove('error', 'success');
        if (type) {
            authMessage.classList.add(type);
        }
        authMessage.textContent = text || '';
    }

    async function submitAuth(action, payload, submitButton) {
        setMessage('', '');
        const originalText = submitButton ? submitButton.textContent : '';
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = action === 'login' ? 'Logging in...' : 'Registering...';
        }

        try {
            const response = await fetch('/auth', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();
            if (data.success) {
                setMessage('success', data.message || 'Success');
                const redirect = data.redirect || '/';
                window.location.href = redirect;
            } else {
                setMessage('error', data.message || 'Authentication failed');
            }
        } catch (err) {
            setMessage('error', 'Unable to reach server. Please try again.');
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            }
        }
    }

    // Login form submission
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value.trim();
        const password = document.getElementById('loginPassword').value;

        if (!email || !password) {
            setMessage('error', 'Email and password are required.');
            return;
        }

        const payload = {
            action: 'login',
            email,
            username: email,
            password
        };

        const submitButton = loginForm.querySelector('button[type="submit"]');
        submitAuth('login', payload, submitButton);
    });

    // Register form submission
    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const name = document.getElementById('registerName').value.trim();
        const email = document.getElementById('registerEmail').value.trim();
        const password = document.getElementById('registerPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (password !== confirmPassword) {
            setMessage('error', 'Passwords do not match.');
            return;
        }
        
        if (!name || !email || !password) {
            setMessage('error', 'All fields are required.');
            return;
        }

        const payload = {
            action: 'register',
            name,
            email,
            username: email,
            password
        };

        const submitButton = registerForm.querySelector('button[type="submit"]');
        submitAuth('register', payload, submitButton);
    });
});
