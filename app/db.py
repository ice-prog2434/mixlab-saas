from datetime import datetime, timezone
from sqlalchemy import create_engine, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from .config import settings

def now():
    return datetime.now(timezone.utc)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="user")
    suspended: Mapped[bool] = mapped_column(default=False)
    trial_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sub_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    paypal_subscription_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sub_provider: Mapped[str | None] = mapped_column(String(10), nullable=True)  # stripe | paypal
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    style: Mapped[str] = mapped_column(String(30))
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|done|error
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_path: Mapped[str] = mapped_column(String(500))
    instru_path: Mapped[str] = mapped_column(String(500))
    output_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user = relationship("User", back_populates="projects")

class StripeEvent(Base):
    __tablename__ = "stripe_events"  # anti double traitement
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(default=False)

class PaypalEvent(Base):
    __tablename__ = "paypal_events"  # anti double traitement
    id: Mapped[str] = mapped_column(String(100), primary_key=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
