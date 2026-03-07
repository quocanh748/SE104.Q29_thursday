// Xử lý nút "Tiếp tục" ở form Đăng ký bước 1
function goToRegStep2() {
    const email = document.getElementById('regEmail').value;
    const pass = document.getElementById('regPass').value;
    const name = document.getElementById('regName').value;

    if (!email || !pass || !name) {
        alert("Vui lòng điền đủ thông tin bước 1!");
        return;
    }

    // Lưu tạm vào biến global
    tempRegData = { email: email, password: pass, full_name: name };

    // Chuyển sang form bước 2
    switchAuthView('register-step-2');
}

// Xử lý gửi toàn bộ dữ liệu lên Backend
async function handleRegister() {
    // Gom dữ liệu từ Bước 1 và Bước 2
    const finalData = {
        email: tempRegData.email,
        password: tempRegData.password,
        full_name: tempRegData.full_name,
        age: parseInt(document.getElementById('regAge').value) || 18,
        gender: document.getElementById('regGender').value,
        bio: document.getElementById('regBio').value,
        role: "user"
    };

    try {
        const res = await fetch(`${API_URL}/users/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(finalData)
        });

        if (res.ok) {
            alert("🎉 Đăng ký thành công! Hãy đăng nhập nhé.");
            // Reset form và quay về màn hình Đăng nhập
            document.getElementById('regEmail').value = '';
            document.getElementById('regPass').value = '';
            switchAuthView('login-form');
        } else {
            alert("Email này đã tồn tại hoặc có lỗi xảy ra!");
        }
    } catch (error) {
        alert("Lỗi kết nối đến Server!");
    }
}

// Xử lý Đăng nhập
async function handleLogin() {
    const data = {
        email: document.getElementById('loginEmail').value,
        password: document.getElementById('loginPass').value
    };

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!res.ok) {
            alert("Sai email hoặc mật khẩu!");
            return;
        }

        const user = await res.json();
        currentUserId = user.id;

        // Đăng nhập thành công -> Vào màn hình chính
        switchScreen('user-screen');

        // (Sau này gọi hàm loadSwipeUsers() ở file app.js tại đây)
        switchScreen('user-screen');
        switchAppTab('swipe');
    } catch (err) {
        alert("Không thể kết nối đến Server!");
    }
}

// Xử lý Đăng xuất
function logout() {
    currentUserId = null;
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPass').value = '';
    switchScreen('auth-screen');
    switchAuthView('login-form'); // Đảm bảo luôn hiện form login khi ra ngoài
}