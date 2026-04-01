// Biến hỗ trợ kiểm tra định dạng Email (Regular Expression)
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ==========================================
// Xử lý nút "Tiếp tục" ở form Đăng ký bước 1
// ==========================================
function goToRegStep2() {
    // Thêm .trim() để cắt bỏ khoảng trắng ở 2 đầu nếu người dùng cố tình nhập toàn dấu cách
    const email = document.getElementById('regEmail').value.trim();
    const pass = document.getElementById('regPass').value;
    const name = document.getElementById('regName').value.trim();

    // 1. Ràng buộc bỏ trống
    if (!email || !pass || !name) {
        alert("⚠️ Vui lòng điền đủ thông tin bước 1!");
        return;
    }

    // 2. Ràng buộc định dạng Email
    if (!emailRegex.test(email)) {
        alert("⚠️ Định dạng email không hợp lệ (Ví dụ đúng: ten@gmail.com)!");
        return;
    }

    // 3. Ràng buộc độ dài Mật khẩu
    if (pass.length < 6) {
        alert("⚠️ Mật khẩu phải có ít nhất 6 ký tự để đảm bảo an toàn!");
        return;
    }

    // Lưu tạm vào biến global
    tempRegData = { email: email, password: pass, full_name: name };

    // Chuyển sang form bước 2
    switchAuthView('register-step-2');
}

// ==========================================
// Xử lý gửi toàn bộ dữ liệu lên Backend
// ==========================================
async function handleRegister() {
    const ageInput = document.getElementById('regAge').value;
    const age = parseInt(ageInput);

    // 4. Ràng buộc độ Tuổi (Rất quan trọng cho App hẹn hò)
    if (!ageInput || isNaN(age) || age < 18 || age > 100) {
        alert("⚠️ Bạn phải từ 18 tuổi trở lên để tham gia ứng dụng này (18 - 100)!");
        return;
    }

    // Gom dữ liệu từ Bước 1 và Bước 2
    const finalData = {
        email: tempRegData.email,
        password: tempRegData.password,
        full_name: tempRegData.full_name,
        age: age,
        gender: document.getElementById('regGender').value,
        bio: document.getElementById('regBio').value.trim(),
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
            // Reset form
            document.getElementById('regEmail').value = '';
            document.getElementById('regPass').value = '';
            document.getElementById('regName').value = '';
            document.getElementById('regAge').value = '';
            document.getElementById('regBio').value = '';
            switchAuthView('login-form');
        } else {
            const errorData = await res.json();
            alert(`❌ Lỗi: ${errorData.detail || "Email này đã tồn tại!"}`);
        }
    } catch (error) {
        alert("📡 Lỗi kết nối đến Server!");
    }
}

// ==========================================
// Xử lý Đăng nhập
// ==========================================
async function handleLogin() {
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPass').value;

    if (!email || !password) {
        alert("⚠️ Vui lòng nhập email và mật khẩu!");
        return;
    }

    const data = { email: email, password: password };

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (!res.ok) {
            alert("❌ Sai email hoặc mật khẩu!");
            return;
        }

        const user = await res.json();
        currentUserId = user.id;

        // Đăng nhập thành công -> Vào màn hình chính
        switchScreen('user-screen');
        switchAppTab('swipe');

    } catch (err) {
        alert("📡 Không thể kết nối đến Server!");
    }
}

// Xử lý Đăng xuất
function logout() {
    currentUserId = null;
    document.getElementById('loginEmail').value = '';
    document.getElementById('loginPass').value = '';
    switchScreen('auth-screen');
    switchAuthView('login-form');
}