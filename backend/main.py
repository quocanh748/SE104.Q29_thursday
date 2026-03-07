from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, create_engine
from pydantic import BaseModel
import enum
from datetime import datetime
import uvicorn

# 1. Cấu hình Database SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./database/dating_app_fastapi.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ĐỊNH NGHĨA ENUM ---
class RoleEnum(enum.Enum):
    admin = "admin"
    user = "user"

class GenderEnum(enum.Enum):
    male = "male"
    female = "female"
    other = "other"

class ActionEnum(enum.Enum):
    like = "like"
    pass_ = "pass"
    superlike = "superlike"

# --- ĐỊNH NGHĨA BẢNG (DATABASE MODELS) ---
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
    bio_embedding = Column(Text, nullable=True) 

    preferences = relationship("PreferenceDB", back_populates="user", uselist=False)

class PreferenceDB(Base):
    __tablename__ = "preferences"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    looking_for_gender = Column(Enum(GenderEnum), nullable=True)
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=99)
    
    user = relationship("UserDB", back_populates="preferences")

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
    
    messages = relationship("MessageDB", back_populates="match")

class MessageDB(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    match = relationship("MatchDB", back_populates="messages")

# Tạo bảng trong Database
Base.metadata.create_all(bind=engine)

# --- PYDANTIC MODELS (ĐỂ KIỂM TRA DỮ LIỆU ĐẦU VÀO/RA) ---
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    age: int = 18
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
    
    class Config:
        from_attributes = True

class SwipeCreate(BaseModel):
    swiper_id: int
    swipee_id: int
    action: str 

# --- KHỞI TẠO FASTAPI ---
app = FastAPI(title="Dating App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- CÁC ĐƯỜNG DẪN API ---
@app.get("/")
def home():
    return {"message": "API Đã Sạch Lỗi và Sẵn Sàng!"}

@app.post("/users/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # Đã sửa lại logic đăng ký: dùng email/password thật và thêm role
    try:
        role_enum = RoleEnum(user.role.lower())
    except ValueError:
        role_enum = RoleEnum.user

    new_user = UserDB(
        email=user.email,
        hashed_password=user.password, # Note: Đồ án có thể lưu text thường, thực tế phải hash!
        full_name=user.full_name, 
        age=user.age, 
        role=role_enum,
        bio=user.bio
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email này đã tồn tại!")

@app.post("/login", response_model=UserResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    # Đã bổ sung API Login
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if not db_user or db_user.hashed_password != user.password:
        raise HTTPException(status_code=401, detail="Sai email hoặc mật khẩu!")
    return db_user

@app.get("/users", response_model=list[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(UserDB).all()

@app.post("/swipe")
def swipe_user(swipe: SwipeCreate, db: Session = Depends(get_db)):
    if swipe.swiper_id == swipe.swipee_id:
        raise HTTPException(status_code=400, detail="Không thể tự quẹt chính mình!")
    
    try:
        action_enum = ActionEnum(swipe.action.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Hành động chỉ được là like, pass, hoặc superlike")

    new_interaction = InteractionDB(
        swiper_id=swipe.swiper_id,
        swipee_id=swipe.swipee_id,
        action=action_enum
    )
    db.add(new_interaction)
    db.commit()

    if action_enum in [ActionEnum.like, ActionEnum.superlike]:
        reverse_swipe = db.query(InteractionDB).filter(
            InteractionDB.swiper_id == swipe.swipee_id,
            InteractionDB.swipee_id == swipe.swiper_id,
            InteractionDB.action.in_([ActionEnum.like, ActionEnum.superlike])
        ).first()

        if reverse_swipe:
            new_match = MatchDB(user1_id=swipe.swiper_id, user2_id=swipe.swipee_id)
            db.add(new_match)
            db.commit()
            return {
                "message": "It's a Match! Hai bạn đã tương hợp.", 
                "is_match": True,
                "match_details": {"user1": swipe.swiper_id, "user2": swipe.swipee_id}
            }

    return {"message": "Đã ghi nhận lượt quẹt thành công.", "is_match": False}

# --- CHẠY SERVER ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)