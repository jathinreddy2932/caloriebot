import json
import logging
from datetime import date, timedelta, datetime
from typing import Optional
from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings, BASE_DIR
from app.database import get_db, init_db
from app.models import MealLog, DailyReport, WeightLog
from app.gemini_parser import parse_food_with_gemini, detect_meal_reference, extract_meal_type_heuristic
from app.report_generator import analyze_day_meals, generate_pdf_report

logger = logging.getLogger(__name__)

app = FastAPI(title="CalorieBot Web Dashboard", version="1.0.0")

# Setup static files & templates
static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates_dir = BASE_DIR / "app" / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    meals = db.query(MealLog).filter(MealLog.date == today).order_by(MealLog.created_at.desc()).all()
    analysis = analyze_day_meals(meals, budget=settings.DAILY_CALORIE_BUDGET)
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "settings": settings,
            "today_str": today.strftime("%A, %B %d, %Y"),
            "meals": [m.to_dict() for m in meals],
            "analysis": analysis,
            "target_deficit": 89.0 - 70.0,
        }
    )

class ManualMealInput(BaseModel):
    text: str

@app.post("/api/meals")
async def log_meal_api(data: ManualMealInput, db: Session = Depends(get_db)):
    text = data.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
        
    today = date.today()
    ref_meal_type = detect_meal_reference(text)

    if ref_meal_type:
        prev_meal = (
            db.query(MealLog)
            .filter(MealLog.date == today, MealLog.meal_type == ref_meal_type)
            .order_by(MealLog.id.desc())
            .first()
        )
        if not prev_meal:
            raise HTTPException(status_code=400, detail=f"No {ref_meal_type} logged today to copy from.")
        
        target_meal_type = extract_meal_type_heuristic(text)
        if target_meal_type == "other":
            target_meal_type = "dinner" if ref_meal_type == "lunch" else "lunch"

        meal_log = MealLog(
            date=today,
            meal_type=target_meal_type,
            raw_text=text,
            items_json=prev_meal.items_json,
            total_calories=prev_meal.total_calories,
            total_protein=prev_meal.total_protein,
            total_carbs=prev_meal.total_carbs,
            total_fat=prev_meal.total_fat,
        )
        tip = f"Repeated from your {ref_meal_type.capitalize()}."
    else:
        parsed = parse_food_with_gemini(text)
        meal_log = MealLog(
            date=today,
            meal_type=parsed.get("meal_type", "other"),
            raw_text=text,
            items_json=json.dumps(parsed.get("items", [])),
            total_calories=parsed.get("total_calories", 0),
            total_protein=parsed.get("total_protein", 0.0),
            total_carbs=parsed.get("total_carbs", 0.0),
            total_fat=parsed.get("total_fat", 0.0),
        )
        tip = parsed.get("short_tip", "")

    db.add(meal_log)
    db.commit()
    db.refresh(meal_log)
    
    return {"status": "success", "meal": meal_log.to_dict(), "tip": tip}

@app.delete("/api/meals/{meal_id}")
async def delete_meal_api(meal_id: int, db: Session = Depends(get_db)):
    meal = db.query(MealLog).filter(MealLog.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    db.delete(meal)
    db.commit()
    return {"status": "deleted", "id": meal_id}

@app.get("/api/today")
async def get_today_stats(db: Session = Depends(get_db)):
    today = date.today()
    meals = db.query(MealLog).filter(MealLog.date == today).all()
    analysis = analyze_day_meals(meals, budget=settings.DAILY_CALORIE_BUDGET)
    return {
        "date": today.isoformat(),
        "budget": settings.DAILY_CALORIE_BUDGET,
        "analysis": analysis,
        "meals": [m.to_dict() for m in meals]
    }

@app.get("/api/history")
async def get_history_stats(days: int = 7, db: Session = Depends(get_db)):
    start_date = date.today() - timedelta(days=days - 1)
    results = (
        db.query(
            MealLog.date,
            func.sum(MealLog.total_calories).label("calories"),
            func.sum(MealLog.total_protein).label("protein"),
        )
        .filter(MealLog.date >= start_date)
        .group_by(MealLog.date)
        .all()
    )
    
    data_by_date = {r.date.isoformat(): {"calories": r.calories, "protein": r.protein} for r in results}
    
    chart_data = []
    for i in range(days):
        cur_date = start_date + timedelta(days=i)
        iso = cur_date.isoformat()
        entry = data_by_date.get(iso, {"calories": 0, "protein": 0})
        chart_data.append({
            "date": cur_date.strftime("%a %d"),
            "iso": iso,
            "calories": entry["calories"],
            "protein": entry["protein"],
            "budget": settings.DAILY_CALORIE_BUDGET,
        })
        
    return chart_data

@app.get("/api/report/today/pdf")
async def download_today_pdf(db: Session = Depends(get_db)):
    today = date.today()
    meals = db.query(MealLog).filter(MealLog.date == today).all()
    if not meals:
        raise HTTPException(status_code=400, detail="No meals logged today yet.")
        
    analysis = analyze_day_meals(meals, budget=settings.DAILY_CALORIE_BUDGET)
    pdf_path = generate_pdf_report(today, analysis)
    
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"CalorieBot_Report_{today.strftime('%Y_%m_%d')}.pdf"
    )
