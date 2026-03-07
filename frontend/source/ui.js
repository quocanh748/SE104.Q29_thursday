// Hàm chuyển đổi giữa các màn hình lớn
function switchScreen(screenId) {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('user-screen').classList.add('hidden');
    document.getElementById(screenId).classList.remove('hidden');
}

// Hàm chuyển đổi giữa các form trong màn hình Đăng nhập/Đăng ký
function switchAuthView(viewId) {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-step-1').classList.add('hidden');
    document.getElementById('register-step-2').classList.add('hidden');

    document.getElementById(viewId).classList.remove('hidden');
}