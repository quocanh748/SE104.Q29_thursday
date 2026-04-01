from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import enum
import uvicorn
import os

# ==========================================
# 1. CẤU HÌNH DATABASE
# ==========================================
NEON_URL = "postgresql://neondb_owner:npg_bjwfum1hcQB6@ep-shiny-hall-a182opu4-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Đọc link từ Server Render (nếu có), nếu không có thì dùng link Neon mặc định ở trên
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", NEON_URL)

# Logic khởi tạo Engine thông minh
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # Nếu dùng SQLite thì mới cần check_same_thread
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Render đôi khi cấp link bắt đầu bằng "postgres://", SQLAlchemy cần "postgresql://"
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Nếu dùng PostgreSQL (Neon/Render) thì KHÔNG CÓ check_same_thread
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class RoleEnum(enum.Enum):
    admin, user = "admin", "user"

class GenderEnum(enum.Enum):
    male, female, other = "male", "female", "other"

# ==========================================
# 2. DATABASE MODELS (ÁP DỤNG IDEAS "PAIR ID")
# ==========================================
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.user)
    full_name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(Enum(GenderEnum), default=GenderEnum.other)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# BẢNG THẦN THÁNH: PAIR (Thay thế cho Interaction và Match)
class PairDB(Base):
    __tablename__ = "pairs"
    id = Column(Integer, primary_key=True, index=True) # Vẫn giữ ID số nguyên để Frontend dễ xử lý
    
    # Cột "AB" theo ý tưởng của bạn (VD: "1_2")
    pair_key = Column(String(50), unique=True, index=True, nullable=False) 
    
    user1_id = Column(Integer, ForeignKey("users.id")) # Luôn lưu ID nhỏ hơn
    user2_id = Column(Integer, ForeignKey("users.id")) # Luôn lưu ID lớn hơn
    
    action_user1 = Column(String(20), nullable=True) # Hành động của người số 1 (like/pass)
    action_user2 = Column(String(20), nullable=True) # Hành động của người số 2 (like/pass)
    
    is_match = Column(Boolean, default=False) # Đã Match chưa?
    matched_at = Column(DateTime, nullable=True)

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("pairs.id")) # Trỏ thẳng về ID của bảng Pair
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ==========================================
# 3. PYDANTIC MODELS & KHỞI TẠO APP
# ==========================================
class UserCreate(BaseModel):
    email: str; password: str; full_name: str; age: int = 18; gender: str = "other"; role: str = "user"; bio: str = ""
class UserLogin(BaseModel):
    email: str; password: str
class UserResponse(BaseModel):
    id: int; email: str; full_name: str; age: int; bio: str | None; role: RoleEnum
    class Config: from_attributes = True
class SwipeCreate(BaseModel):
    swiper_id: int; swipee_id: int; action: str 
class MessageCreate(BaseModel):
    match_id: int; sender_id: int; content: str

app = FastAPI(title="Dating App API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# ==========================================
# 4. API ENDPOINTS
# ==========================================
@app.post("/users/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try: role_enum = RoleEnum(user.role.lower())
    except: role_enum = RoleEnum.user
    try: gender_enum = GenderEnum(user.gender.lower())
    except: gender_enum = GenderEnum.other

    new_user = UserDB(email=user.email, hashed_password=user.password, full_name=user.full_name, age=user.age, gender=gender_enum, role=role_enum, bio=user.bio)
    db.add(new_user)
    try:
        db.commit(); db.refresh(new_user); return new_user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email đã tồn tại!")

@app.post("/login", response_model=UserResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if not db_user or db_user.hashed_password != user.password: raise HTTPException(status_code=401)
    return db_user

# ------------------------------------------
# PHẦN LÕI: LOGIC QUẸT THẺ ÁP DỤNG "PAIR ID"
# ------------------------------------------
@app.post("/swipe")
def swipe_user(swipe: SwipeCreate, db: Session = Depends(get_db)):
    if swipe.swiper_id == swipe.swipee_id:
        raise HTTPException(status_code=400, detail="Không thể tự quẹt mình!")
    
    # 1. TẠO "CỘT AB" (Pair Key) - ID nhỏ đứng trước, ID lớn đứng sau
    u1, u2 = sorted([swipe.swiper_id, swipe.swipee_id])
    pair_key = f"{u1}_{u2}"

    # 2. TÌM KIẾM DỮ LIỆU CỦA CẶP NÀY (Chỉ O(1) thao tác)
    pair = db.query(PairDB).filter(PairDB.pair_key == pair_key).first()
    
    # Nếu hai người chưa từng tương tác bao giờ -> Tạo dòng mới
    if not pair:
        pair = PairDB(pair_key=pair_key, user1_id=u1, user2_id=u2)
        db.add(pair)

    # 3. CẬP NHẬT HÀNH ĐỘNG CỦA MÌNH VÀO CỘT TƯƠNG ỨNG
    if swipe.swiper_id == u1:
        pair.action_user1 = swipe.action.lower()
    else:
        pair.action_user2 = swipe.action.lower()

    # 4. KIỂM TRA MATCH: Chỉ việc xem 2 cột trên cùng 1 dòng
    is_match = False
    if pair.action_user1 in ['like', 'superlike'] and pair.action_user2 in ['like', 'superlike']:
        pair.is_match = True
        pair.matched_at = datetime.utcnow()
        is_match = True

    db.commit()
    return {"message": "It's a Match!" if is_match else "Đã ghi nhận", "is_match": is_match}

@app.get("/users/suggestions/{user_id}", response_model=list[UserResponse])
def get_suggestions(user_id: int, db: Session = Depends(get_db)):
    # Lấy tất cả các cặp có dính líu đến user_id
    pairs = db.query(PairDB).filter((PairDB.user1_id == user_id) | (PairDB.user2_id == user_id)).all()
    
    exclude_ids = [user_id]
    for p in pairs:
        # Nếu đã Match thì loại bỏ
        if p.is_match:
            exclude_ids.extend([p.user1_id, p.user2_id])
            continue
            
        # Nếu mình là user1 và ĐÃ hành động -> Không hiện người kia nữa
        if p.user1_id == user_id and p.action_user1 is not None:
            exclude_ids.append(p.user2_id)
        # Nếu mình là user2 và ĐÃ hành động -> Không hiện người kia nữa
        elif p.user2_id == user_id and p.action_user2 is not None:
            exclude_ids.append(p.user1_id)
            
        # Nếu người kia ĐÃ LIKE mình -> Đưa họ qua Tab Lượt Thích, xóa khỏi Khám phá
        if p.user1_id == user_id and p.action_user2 in ['like', 'superlike']:
            exclude_ids.append(p.user2_id)
        elif p.user2_id == user_id and p.action_user1 in ['like', 'superlike']:
            exclude_ids.append(p.user1_id)

    return db.query(UserDB).filter(UserDB.id.notin_(list(set(exclude_ids))), UserDB.role == RoleEnum.user).all()

@app.get("/users/likes-me/{user_id}", response_model=list[UserResponse])
def get_likes_me(user_id: int, db: Session = Depends(get_db)):
    pairs = db.query(PairDB).filter((PairDB.user1_id == user_id) | (PairDB.user2_id == user_id)).all()
    
    likes_me_ids = []
    for p in pairs:
        # TÌM NHỮNG NGƯỜI ĐÃ LIKE MÌNH VÀ MÌNH CHƯA PHẢN HỒI (Hành động của mình là None)
        if p.user1_id == user_id and p.action_user2 in ['like', 'superlike'] and p.action_user1 is None:
            likes_me_ids.append(p.user2_id)
        elif p.user2_id == user_id and p.action_user1 in ['like', 'superlike'] and p.action_user2 is None:
            likes_me_ids.append(p.user1_id)
            
    return db.query(UserDB).filter(UserDB.id.in_(likes_me_ids)).all()

@app.get("/matches/{user_id}")
def get_user_matches(user_id: int, db: Session = Depends(get_db)):
    # Tìm các cặp đã is_match = True
    pairs = db.query(PairDB).filter(((PairDB.user1_id == user_id) | (PairDB.user2_id == user_id)), PairDB.is_match == True).all()
    
    result = []
    for p in pairs:
        other_id = p.user2_id if p.user1_id == user_id else p.user1_id
        other_user = db.query(UserDB).filter(UserDB.id == other_id).first()
        if other_user: result.append({"match_id": p.id, "other_user_id": other_user.id, "other_user_name": other_user.full_name})
    return result

@app.delete("/matches/{match_id}")
def unmatch_user(match_id: int, db: Session = Depends(get_db)):
    pair = db.query(PairDB).filter(PairDB.id == match_id).first()
    if not pair: raise HTTPException(status_code=404)
    
    # Xóa tin nhắn
    db.query(MessageDB).filter(MessageDB.match_id == match_id).delete()
    
    # Hủy tương hợp: Xóa lịch sử quẹt của cả 2 để họ thành người dưng (reset dòng này)
    pair.action_user1 = None
    pair.action_user2 = None
    pair.is_match = False
    pair.matched_at = None
    db.commit()
    return {"message": "Hủy thành công"}

@app.post("/messages")
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    db.add(MessageDB(match_id=msg.match_id, sender_id=msg.sender_id, content=msg.content))
    db.commit()
    return {"message": "Đã gửi"}

@app.get("/messages/{match_id}")
def get_messages(match_id: int, db: Session = Depends(get_db)):
    msgs = db.query(MessageDB).filter(MessageDB.match_id == match_id).order_by(MessageDB.sent_at).all()
    return [{"sender_id": m.sender_id, "content": m.content} for m in msgs]

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)