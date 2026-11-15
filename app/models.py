from datetime import datetime, date
from sqlalchemy import Column, Integer, Float, String, Text, Date, DateTime
from app.database import Base

class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, index=True)
    meal_type = Column(String(50), index=True)  # breakfast, lunch, snack, dinner, meanwhile
    raw_text = Column(Text, nullable=False)
    items_json = Column(Text, nullable=False)    # JSON string: [{"name": "...", "qty": "...", "calories": 120, ...}]
    total_calories = Column(Integer, default=0)
    total_protein = Column(Float, default=0.0)
    total_carbs = Column(Float, default=0.0)
    total_fat = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "meal_type": self.meal_type,
            "raw_text": self.raw_text,
            "food_items": json.loads(self.items_json) if self.items_json else [],
            "total_calories": self.total_calories,
            "total_protein": round(self.total_protein, 1),
            "total_carbs": round(self.total_carbs, 1),
            "total_fat": round(self.total_fat, 1),
            "created_at": self.created_at.strftime("%H:%M:%S") if self.created_at else None,
        }

class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=date.today, index=True)
    weight_kg = Column(Float, nullable=False)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    total_calories = Column(Integer, default=0)
    budget = Column(Integer, default=1750)
    excess_calories = Column(Integer, default=0)
    analysis_text = Column(Text, nullable=True)
    pdf_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
