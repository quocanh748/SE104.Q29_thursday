from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from pydantic import BaseModel
from datetime import datetime
import enum
import uvicorn

# 2. CẤU HÌNH DATABASE
SQLALCHEMY_DATABASE_URL = "sqlite:///./database/dating_app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. ĐỊNH NGHĨA ENUMS
class RoleEnum(enum.Enum):
    admin, user = "admin", "user"

class GenderEnum(enum.Enum):
    male, female, other = "male", "female", "other"

class ActionEnum(enum.Enum):
    like, pass_, superlike = "like", "pass", "superlike"

# 4. DATABASE MODELS (BẢNG TRONG CSDL)
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

class InteractionDB(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True, index=True)
    swiper_id = Column(Integer, ForeignKey("users.id"))
    swipee_id = Column(Integer, ForeignKey("users.id"))
    action = Column(Enum(ActionEnum), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class MatchDB(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"))
    user2_id = Column(Integer, ForeignKey("users.id"))
    matched_at = Column(DateTime, default=datetime.utcnow)

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)

# Tạo các bảng
Base.metadata.create_all(bind=engine)

# 5. PYDANTIC MODELS (KIỂM TRA DỮ LIỆU)
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    age: int = 18
    gender: str = "other"
    role: str = "user"
    bio: str = ""

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    age: int
    bio: str | None
    role: RoleEnum
    class Config: from_attributes = True

class SwipeCreate(BaseModel):
    swiper_id: int
    swipee_id: int
    action: str 

class MessageCreate(BaseModel):
    match_id: int
    sender_id: int
    content: str

# 6. KHỞI TẠO ỨNG DỤNG & MIDDLEWARE
app = FastAPI(title="Dating App API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# 7. ROUTERS (API ENDPOINTS)
@app.get("/")
def home(): return {"status": "API is running cleanly!"}

# --- AUTH & USERS ---
@app.post("/users/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    try: role_enum = RoleEnum(user.role.lower())
    except: role_enum = RoleEnum.user
    try: gender_enum = GenderEnum(user.gender.lower())
    except: gender_enum = GenderEnum.other

    new_user = UserDB(
        email=user.email, hashed_password=user.password, full_name=user.full_name, 
        age=user.age, gender=gender_enum, role=role_enum, bio=user.bio
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email đã tồn tại!")

@app.post("/login", response_model=UserResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if not db_user or db_user.hashed_password != user.password:
        raise HTTPException(status_code=401, detail="Sai thông tin đăng nhập!")
    return db_user

@app.get("/users/suggestions/{user_id}", response_model=list[UserResponse])
def get_suggestions(user_id: int, db: Session = Depends(get_db)):
    # 1. Những người mình ĐÃ quẹt (dù like hay pass)
    swiped_by_me = db.query(InteractionDB.swipee_id).filter(InteractionDB.swiper_id == user_id).all()
    swiped_ids = [r[0] for r in swiped_by_me]

    # 2. Những người ĐÃ Like/SuperLike mình (chuyển họ sang tab Lượt Thích)
    liked_me = db.query(InteractionDB.swiper_id).filter(
        InteractionDB.swipee_id == user_id,
        InteractionDB.action.in_([ActionEnum.like, ActionEnum.superlike])
    ).all()
    liked_me_ids = [r[0] for r in liked_me]

    # Gộp 2 danh sách lại và thêm chính mình vào để loại trừ
    exclude_ids = list(set(swiped_ids + liked_me_ids + [user_id]))

    return db.query(UserDB).filter(UserDB.id.notin_(exclude_ids), UserDB.role == RoleEnum.user).all()

# THÊM MỚI API Lượt Thích: Danh sách những người đang "thầm thương trộm nhớ" mình
@app.get("/users/likes-me/{user_id}", response_model=list[UserResponse])
def get_likes_me(user_id: int, db: Session = Depends(get_db)):
    # Tìm những ID đã Like/SuperLike mình
    liked_me = db.query(InteractionDB.swiper_id).filter(
        InteractionDB.swipee_id == user_id,
        InteractionDB.action.in_([ActionEnum.like, ActionEnum.superlike])
    ).all()
    liked_me_ids = [r[0] for r in liked_me]

    # Nhưng phải loại trừ những người mà mình đã quẹt rồi (vì nếu mình quẹt rồi thì 1 là Match, 2 là Miss)
    swiped_by_me = db.query(InteractionDB.swipee_id).filter(InteractionDB.swiper_id == user_id).all()
    swiped_ids = [r[0] for r in swiped_by_me]

    # Lọc ra những ID hợp lệ (Đã like mình VÀ mình chưa quẹt họ)
    valid_ids = [uid for uid in liked_me_ids if uid not in swiped_ids]

    return db.query(UserDB).filter(UserDB.id.in_(valid_ids)).all()

# --- SWIPE & MATCHES ---
@app.post("/swipe")
def swipe_user(swipe: SwipeCreate, db: Session = Depends(get_db)):
    if swipe.swiper_id == swipe.swipee_id:
        raise HTTPException(status_code=400, detail="Không thể tự quẹt mình!")
    try: action_enum = ActionEnum(swipe.action.lower())
    except: raise HTTPException(status_code=400, detail="Hành động không hợp lệ")

    db.add(InteractionDB(swiper_id=swipe.swiper_id, swipee_id=swipe.swipee_id, action=action_enum))
    db.commit()

    if action_enum in [ActionEnum.like, ActionEnum.superlike]:
        reverse = db.query(InteractionDB).filter(
            InteractionDB.swiper_id == swipe.swipee_id, InteractionDB.swipee_id == swipe.swiper_id,
            InteractionDB.action.in_([ActionEnum.like, ActionEnum.superlike])
        ).first()
        if reverse:
            db.add(MatchDB(user1_id=swipe.swiper_id, user2_id=swipe.swipee_id))
            db.commit()
            return {"message": "It's a Match!", "is_match": True}
    return {"message": "Đã ghi nhận", "is_match": False}

@app.get("/matches/{user_id}")
def get_user_matches(user_id: int, db: Session = Depends(get_db)):
    matches = db.query(MatchDB).filter((MatchDB.user1_id == user_id) | (MatchDB.user2_id == user_id)).all()
    result = []
    for m in matches:
        other_id = m.user2_id if m.user1_id == user_id else m.user1_id
        other_user = db.query(UserDB).filter(UserDB.id == other_id).first()
        if other_user: result.append({"match_id": m.id, "other_user_id": other_user.id, "other_user_name": other_user.full_name})
    return result

@app.delete("/matches/{match_id}")
def unmatch_user(match_id: int, db: Session = Depends(get_db)):
    match = db.query(MatchDB).filter(MatchDB.id == match_id).first()
    if not match: raise HTTPException(status_code=404)
    db.query(MessageDB).filter(MessageDB.match_id == match_id).delete()
    db.query(InteractionDB).filter(
        ((InteractionDB.swiper_id == match.user1_id) & (InteractionDB.swipee_id == match.user2_id)) |
        ((InteractionDB.swiper_id == match.user2_id) & (InteractionDB.swipee_id == match.user1_id))
    ).delete()
    db.delete(match)
    db.commit()
    return {"message": "Hủy thành công"}

# --- MESSAGING ---
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