import json
import os
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Tuple
from app.config import settings, DATA_DIR
from app.models import MealLog

REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

def analyze_day_meals(meals: List[MealLog], budget: int = settings.DAILY_CALORIE_BUDGET) -> Dict[str, Any]:
    total_calories = sum(m.total_calories for m in meals)
    total_protein = sum(m.total_protein for m in meals)
    total_carbs = sum(m.total_carbs for m in meals)
    total_fat = sum(m.total_fat for m in meals)
    
    # Group by meal_type
    by_category: Dict[str, List[Dict[str, Any]]] = {
        "breakfast": [],
        "lunch": [],
        "snack": [],
        "dinner": [],
        "meanwhile": [],
        "other": []
    }
    
    all_items = []
    for m in meals:
        items = json.loads(m.items_json) if m.items_json else []
        cat = m.meal_type if m.meal_type in by_category else "other"
        by_category[cat].append({
            "log_id": m.id,
            "raw_text": m.raw_text,
            "items": items,
            "calories": m.total_calories,
            "time": m.created_at.strftime("%I:%M %p") if m.created_at else ""
        })
        for it in items:
            all_items.append({
                "meal": cat,
                "name": it.get("name", "Unknown"),
                "quantity": it.get("quantity", "1"),
                "unit": it.get("unit", ""),
                "calories": it.get("calories", 0),
                "protein_g": it.get("protein_g", 0.0),
                "carbs_g": it.get("carbs_g", 0.0),
                "fat_g": it.get("fat_g", 0.0)
            })

    # Sort all items by calorie density descending
    sorted_items = sorted(all_items, key=lambda x: x["calories"], reverse=True)
    top_heavy_items = [it for it in sorted_items if it["calories"] >= 200]
    
    is_excess = total_calories > budget
    excess_calories = max(0, total_calories - budget)
    remaining_calories = max(0, budget - total_calories)
    
    # Specific targeted advice based on items & intake
    control_points = []
    if is_excess:
        control_points.append(f"⚠️ You exceeded your daily budget by {excess_calories} kcal.")
        if top_heavy_items:
            culprits = ", ".join([f"{it['name']} ({it['calories']} kcal)" for it in top_heavy_items[:2]])
            control_points.append(f"🔍 Main calorie drivers today: {culprits}.")
        
        # Check meal categories
        snack_cals = sum(it["calories"] for it in by_category["snack"])
        meanwhile_cals = sum(it["calories"] for it in by_category["meanwhile"])
        if snack_cals + meanwhile_cals > 400:
            control_points.append(f"🍿 High snacking/meanwhile intake ({snack_cals + meanwhile_cals} kcal). Swap fried snacks/sweets with cucumber, green tea, or roasted chana.")
            
        dinner_cals = sum(it["calories"] for it in by_category["dinner"])
        if dinner_cals > 600:
            control_points.append("🌙 Dinner was heavy. Reduce dinner carbs (e.g. cut 1 roti or skip extra rice) since metabolism slows at night.")
    else:
        control_points.append(f"🎯 Outstanding discipline! You stayed within budget with {remaining_calories} kcal to spare.")
        control_points.append(f"🔥 At this calorie rate, you are on track to reach your 70 kg goal (-19 kg loss).")

    # Protein intake check
    protein_target = settings.DAILY_PROTEIN_TARGET_G
    if total_protein < protein_target:
        deficit_p = protein_target - int(total_protein)
        control_points.append(f"💪 Protein was {int(total_protein)}g (target {protein_target}g). Adding eggs, paneer, chicken breast, or soya chunks will preserve muscle while cutting fat.")
    else:
        control_points.append(f"💪 Excellent protein intake ({int(total_protein)}g)! This protects your lean muscle during this cut.")

    return {
        "total_calories": total_calories,
        "budget": budget,
        "excess_calories": excess_calories,
        "remaining_calories": remaining_calories,
        "is_excess": is_excess,
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fat": round(total_fat, 1),
        "by_category": by_category,
        "all_items": all_items,
        "top_heavy_items": top_heavy_items,
        "control_points": control_points,
    }

def format_telegram_eod_report(report_date: date, analysis: Dict[str, Any]) -> str:
    """Creates a beautifully formatted Telegram message for EOD."""
    cals = analysis["total_calories"]
    budget = analysis["budget"]
    p = analysis["total_protein"]
    c = analysis["total_carbs"]
    f = analysis["total_fat"]
    
    date_str = report_date.strftime("%d %b %Y")
    status_header = "🔴 OVER BUDGET" if analysis["is_excess"] else "🟢 ON TARGET"
    
    lines = [
        f"📊 *END OF DAY DIET REPORT* — {date_str}",
        f"Status: {status_header}\n",
        f"🎯 *Daily Calorie Target:* {budget} kcal",
        f"🔥 *Total Consumed:* {cals} kcal",
    ]
    
    if analysis["is_excess"]:
        lines.append(f"⚠️ *Excess Calorie Intake:* +{analysis['excess_calories']} kcal\n")
    else:
        lines.append(f"✨ *Deficit Saved:* -{analysis['remaining_calories']} kcal\n")

    lines.append(f"🥗 *Macronutrient Breakdown:*")
    lines.append(f"• Protein: `{p}g` / {settings.DAILY_PROTEIN_TARGET_G}g target")
    lines.append(f"• Carbs: `{c}g`")
    lines.append(f"• Fats: `{f}g`\n")
    
    lines.append("🍽️ *Meals Logged Today:*")
    cat_names = {
        "breakfast": "🌅 Breakfast / Tiffin",
        "lunch": "☀️ Lunch",
        "snack": "☕ Snacks",
        "dinner": "🌙 Dinner",
        "meanwhile": "🕒 Meanwhile / Munching",
        "other": "🍴 Other"
    }
    
    for cat_key, cat_title in cat_names.items():
        entries = analysis["by_category"].get(cat_key, [])
        if entries:
            cat_cals = sum(e["calories"] for e in entries)
            lines.append(f"\n*{cat_title}* (`{cat_cals} kcal`):")
            for e in entries:
                for item in e["items"]:
                    lines.append(f"  • {item.get('name')} x{item.get('quantity', 1)} — {item.get('calories', 0)} kcal")

    lines.append("\n📋 *What To Control & Fix Tomorrow:*")
    for pt in analysis["control_points"]:
        lines.append(f"• {pt}")
        
    lines.append(f"\n🎯 *Progress to Goal:* 89 kg ➔ 70 kg (-19 kg cut)")
    lines.append("📄 *PDF detailed report attached below!*")
    
    return "\n".join(lines)

def generate_pdf_report(report_date: date, analysis: Dict[str, Any]) -> str:
    """Generates a professional PDF report using ReportLab and returns the file path."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    pdf_filename = f"report_{report_date.strftime('%Y-%m-%d')}.pdf"
    pdf_path = REPORTS_DIR / pdf_filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
        fontName='Helvetica'
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        fontName='Helvetica'
    )
    bold_body = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    alert_style = ParagraphStyle(
        'AlertBody',
        parent=body_style,
        textColor=colors.HexColor('#B91C1C'),
        fontName='Helvetica-Bold'
    )
    success_style = ParagraphStyle(
        'SuccessBody',
        parent=body_style,
        textColor=colors.HexColor('#15803D'),
        fontName='Helvetica-Bold'
    )

    elements = []

    # Header
    elements.append(Paragraph("CALORIEBOT // DAILY NUTRITION AUDIT", title_style))
    elements.append(Paragraph(
        f"Date: <b>{report_date.strftime('%B %d, %Y')}</b> | User: <b>{settings.USER_NAME} (21 M, 168cm)</b> | Goal: <b>89 kg ➔ 70 kg (-19 kg)</b>",
        subtitle_style
    ))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#CBD5E1'), spaceAfter=14))

    # Summary KPI Cards Table
    status_text = f"EXCESS (+{analysis['excess_calories']} kcal)" if analysis["is_excess"] else f"DEFICIT (-{analysis['remaining_calories']} kcal)"
    status_bg = colors.HexColor('#FEE2E2') if analysis["is_excess"] else colors.HexColor('#DCFCE7')
    status_text_color = colors.HexColor('#991B1B') if analysis["is_excess"] else colors.HexColor('#166534')

    kpi_data = [
        [
            Paragraph("<b>Target Budget</b>", subtitle_style),
            Paragraph("<b>Total Consumed</b>", subtitle_style),
            Paragraph("<b>Net Status</b>", subtitle_style),
            Paragraph("<b>Protein Intake</b>", subtitle_style),
        ],
        [
            Paragraph(f"<font size=14><b>{analysis['budget']}</b> kcal</font>", bold_body),
            Paragraph(f"<font size=14><b>{analysis['total_calories']}</b> kcal</font>", bold_body),
            Paragraph(f"<font size=12 color='{status_text_color}'><b>{status_text}</b></font>", bold_body),
            Paragraph(f"<font size=14><b>{int(analysis['total_protein'])}g</b> / {settings.DAILY_PROTEIN_TARGET_G}g</font>", bold_body),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 130, 150, 130])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (2, 0), (2, -1), status_bg),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 14))

    # Macronutrients Table
    elements.append(Paragraph("Macronutrient Distribution", section_style))
    macro_data = [
        ["Nutrient", "Amount", "Calories Provided", "% of Total"],
        ["Protein", f"{analysis['total_protein']} g", f"{int(analysis['total_protein'] * 4)} kcal", f"{round((analysis['total_protein']*4 / max(1, analysis['total_calories']))*100, 1)}%"],
        ["Carbohydrates", f"{analysis['total_carbs']} g", f"{int(analysis['total_carbs'] * 4)} kcal", f"{round((analysis['total_carbs']*4 / max(1, analysis['total_calories']))*100, 1)}%"],
        ["Fats", f"{analysis['total_fat']} g", f"{int(analysis['total_fat'] * 9)} kcal", f"{round((analysis['total_fat']*9 / max(1, analysis['total_calories']))*100, 1)}%"],
    ]
    macro_table = Table(macro_data, colWidths=[135, 135, 135, 135])
    macro_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(macro_table)
    elements.append(Spacer(1, 14))

    # All Meals Logged Table
    elements.append(Paragraph("Itemized Food Intake Log", section_style))
    items_data = [["Meal Type", "Food Item", "Quantity / Unit", "Calories", "Macros (P / C / F)"]]
    for item in analysis["all_items"]:
        items_data.append([
            item["meal"].capitalize(),
            item["name"],
            f"{item['quantity']} {item['unit']}".strip(),
            f"{item['calories']} kcal",
            f"{item['protein_g']}g / {item['carbs_g']}g / {item['fat_g']}g"
        ])
    if len(items_data) == 1:
        items_data.append(["No meals logged today", "-", "-", "0 kcal", "-"])

    items_table = Table(items_data, colWidths=[90, 160, 100, 80, 110])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 14))

    # Analysis & What to control box
    elements.append(Paragraph("Dietitian Audit & What Should Be Controlled", section_style))
    control_box_content = []
    for pt in analysis["control_points"]:
        control_box_content.append(Paragraph(f"• {pt}", body_style))
        control_box_content.append(Spacer(1, 4))

    control_table = Table([[control_box_content]], colWidths=[540])
    control_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(control_table)

    # Footer note
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(
        "<i>Generated automatically by CalorieBot. Target 70 kg weight cut is steady and achievable with consistent 500 kcal daily deficit.</i>",
        subtitle_style
    ))

    doc.build(elements)
    return str(pdf_path)
