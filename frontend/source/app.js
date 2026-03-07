let potentialMatches = [];
let currentMatchIndex = 0;
let activeMatchId = null;
let chatInterval = null;

// Điều hướng trong App (Đã thêm tab 'likes')
function switchAppTab(tabName) {
    document.getElementById('tab-swipe').classList.add('hidden');
    document.getElementById('tab-likes').classList.add('hidden');
    document.getElementById('tab-matches').classList.add('hidden');
    document.getElementById('tab-chat').classList.add('hidden');

    document.getElementById('nav-swipe').classList.remove('active');
    document.getElementById('nav-likes').classList.remove('active');
    document.getElementById('nav-matches').classList.remove('active');

    clearInterval(chatInterval);

    if (tabName === 'swipe') {
        document.getElementById('tab-swipe').classList.remove('hidden');
        document.getElementById('nav-swipe').classList.add('active');
        loadSwipeUsers();
    } else if (tabName === 'likes') {
        document.getElementById('tab-likes').classList.remove('hidden');
        document.getElementById('nav-likes').classList.add('active');
        loadLikesMe(); // Gọi hàm load danh sách người thích mình
    } else if (tabName === 'matches') {
        document.getElementById('tab-matches').classList.remove('hidden');
        document.getElementById('nav-matches').classList.add('active');
        loadMatchList();
    } else if (tabName === 'chat') {
        document.getElementById('tab-chat').classList.remove('hidden');
        document.getElementById('tab-chat').style.display = 'flex';
        chatInterval = setInterval(loadMessages, 2000);
    }
}

// =====================================
// 1. NGHIỆP VỤ QUẸT THẺ (Khám phá)
// =====================================
async function loadSwipeUsers() {
    try {
        const res = await fetch(`${API_URL}/users/suggestions/${currentUserId}`);
        potentialMatches = await res.json();
        currentMatchIndex = 0;
        renderCard();
    } catch (error) { console.error("Lỗi tải user"); }
}

function renderCard() {
    if (currentMatchIndex >= potentialMatches.length) {
        document.getElementById('swipe-card').classList.add('hidden');
        document.getElementById('no-more-users').classList.remove('hidden');
        return;
    }
    document.getElementById('swipe-card').classList.remove('hidden');
    document.getElementById('no-more-users').classList.add('hidden');
    const user = potentialMatches[currentMatchIndex];
    document.getElementById('card-name').innerText = user.full_name + ", " + user.age;
    document.getElementById('card-bio').innerText = `"${user.bio}"`;
}

async function handleSwipe(action) {
    const swipeeUser = potentialMatches[currentMatchIndex];
    const data = { swiper_id: currentUserId, swipee_id: swipeeUser.id, action: action };
    try {
        const res = await fetch(`${API_URL}/swipe`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.is_match) alert(`🎉 IT'S A MATCH với ${swipeeUser.full_name}!`);
        currentMatchIndex++;
        renderCard();
    } catch (e) { alert("Lỗi hệ thống quẹt!"); }
}

// =====================================
// 2. NGHIỆP VỤ "LƯỢT THÍCH" (Mới thêm)
// =====================================
async function loadLikesMe() {
    try {
        const res = await fetch(`${API_URL}/users/likes-me/${currentUserId}`);
        const users = await res.json();
        const listDiv = document.getElementById('likes-list');
        listDiv.innerHTML = '';

        if (users.length === 0) {
            listDiv.innerHTML = '<p style="text-align:center; color:#888;">Chưa có ai thích bạn 😢</p>';
            return;
        }

        // Tạo thẻ cho từng người đã thích mình
        users.forEach(u => {
            listDiv.innerHTML += `
                <div style="border: 1px solid #eee; border-radius: 10px; padding: 15px; display: flex; justify-content: space-between; align-items: center; background: #fff;">
                    <div>
                        <b style="font-size:16px;">${u.full_name}, ${u.age}</b><br>
                        <i style="color:#666; font-size:13px;">"${u.bio}"</i>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="handleLikeMeAction(${u.id}, 'pass')" style="width:40px;height:40px;border-radius:50%;background:#fff;border:2px solid #fd5068;color:#fd5068;padding:0;font-size:16px; margin:0;" title="Bỏ qua">❌</button>
                        <button onclick="handleLikeMeAction(${u.id}, 'like')" style="width:40px;height:40px;border-radius:50%;background:#fff;border:2px solid #2ecc71;color:#2ecc71;padding:0;font-size:16px; margin:0;" title="Thích lại">💖</button>
                    </div>
                </div>
            `;
        });
    } catch (e) { console.error(e); }
}

// Hàm xử lý khi mình quyết định Like/Pass những người đã thích mình
async function handleLikeMeAction(targetId, action) {
    const data = { swiper_id: currentUserId, swipee_id: targetId, action: action };
    try {
        const res = await fetch(`${API_URL}/swipe`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
        const result = await res.json();
        if (result.is_match) alert(`🎉 BÙM! Bạn và người ấy đã Match! Hãy vào phần Tin Nhắn để trò chuyện nhé.`);

        // Tải lại danh sách sau khi thao tác
        loadLikesMe();
    } catch (e) { alert("Lỗi khi phản hồi!"); }
}

// =====================================
// 3. NGHIỆP VỤ DANH SÁCH MATCH & CHAT
// =====================================
async function loadMatchList() {
    const res = await fetch(`${API_URL}/matches/${currentUserId}`);
    const matches = await res.json();
    const listDiv = document.getElementById('match-list');
    listDiv.innerHTML = '';
    if (matches.length === 0) { listDiv.innerHTML = '<p style="text-align:center; color:#888; margin-top:20px;">Chưa có match nào 😢</p>'; return; }
    matches.forEach(m => {
        const initial = m.other_user_name.charAt(0).toUpperCase();
        listDiv.innerHTML += `<div class="match-item" onclick="openChat(${m.match_id}, '${m.other_user_name}')"><div class="match-avatar">${initial}</div><div><b>${m.other_user_name}</b><br><span style="font-size:12px;color:#888;">Bấm để nhắn tin</span></div></div>`;
    });
}

function openChat(matchId, partnerName) {
    activeMatchId = matchId;
    document.getElementById('chat-partner-name').innerText = partnerName;
    document.getElementById('chat-box').innerHTML = '';
    switchAppTab('chat');
    loadMessages();
}

async function loadMessages() {
    if (!activeMatchId) return;
    const res = await fetch(`${API_URL}/messages/${activeMatchId}`);
    const msgs = await res.json();
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';
    msgs.forEach(m => {
        const isMe = m.sender_id === currentUserId;
        const msgClass = isMe ? 'msg-me' : 'msg-them';
        chatBox.innerHTML += `<div class="msg ${msgClass}">${m.content}</div>`;
    });
    chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    await fetch(`${API_URL}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ match_id: activeMatchId, sender_id: currentUserId, content: text }) });
    loadMessages();
}

async function unmatch() {
    if (!confirm("Hủy match và xóa toàn bộ tin nhắn?")) return;
    try {
        const res = await fetch(`${API_URL}/matches/${activeMatchId}`, { method: 'DELETE' });
        if (res.ok) { alert("Đã hủy tương hợp!"); activeMatchId = null; switchAppTab('matches'); }
    } catch (error) { alert("Lỗi khi hủy tương hợp!"); }
}