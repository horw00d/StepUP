from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, create_engine, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Legacy/1.4 style for compatibility with your environment
from sqlalchemy.orm import declarative_base
Base = declarative_base()

class Participant(Base):
    __tablename__ = "participants"
    
    id: Mapped[str] = mapped_column(String(3), primary_key=True)
    sex: Mapped[Optional[str]] = mapped_column(String(10)) 
    age: Mapped[Optional[int]] = mapped_column(Integer)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    
    trials: Mapped[List["Trial"]] = relationship(back_populates="participant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Participant(id={self.id})>"

class Trial(Base):
    __tablename__ = "trials"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), nullable=False)
    footwear: Mapped[str] = mapped_column(String(5), nullable=False)
    speed: Mapped[str] = mapped_column(String(5), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=True)

    footsteps: Mapped[List["Footstep"]] = relationship(back_populates="trial", cascade="all, delete-orphan")
    participant: Mapped["Participant"] = relationship(back_populates="trials")

    __table_args__ = (UniqueConstraint('participant_id', 'footwear', 'speed', name='uix_trial_unique'),)

class Footstep(Base):
    __tablename__ = "footsteps"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), nullable=False, index=True)
    
    footstep_index: Mapped[int] = mapped_column(Integer)
    pass_id: Mapped[int] = mapped_column(Integer)
    
    start_frame: Mapped[int] = mapped_column(Integer)
    end_frame: Mapped[int] = mapped_column(Integer)
    
    side: Mapped[str] = mapped_column(String(5))
    orientation: Mapped[int] = mapped_column(Integer)

    r_score: Mapped[float] = mapped_column(Float)
    mean_grf: Mapped[float] = mapped_column(Float)
    
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)
    is_incomplete: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude: Mapped[bool] = mapped_column(Boolean, default=False)

    trial: Mapped["Trial"] = relationship(back_populates="footsteps")

    __table_args__ = (Index('idx_footstep_filter', 'is_outlier', 'exclude'),)