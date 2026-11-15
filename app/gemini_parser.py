import json
import re
from typing import Dict, Any, List, Optional
from app.config import settings

def detect_meal_reference(text: str) -> Optional[str]:
    """Detects if user is referencing another meal (e.g. 'same as lunch', 'repeat breakfast')."""
    lower = text.lower()
    match = re.search(r"(?:same\s+(?:as|like)|repeat|ditto|copy\s+of)\s+(breakfast|lunch|tiffin|morning|snack|snacks|dinner)", lower)
    if match:
        ref = match.group(1)
        if ref in ["breakfast", "tiffin", "morning"]:
            return "breakfast"
        if ref in ["lunch"]:
            return "lunch"
        if ref in ["snack", "snacks"]:
            return "snack"
        if ref in ["dinner"]:
            return "dinner"
    return None

def extract_meal_type_heuristic(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["morning", "breakfast", "tiffin", "nashta", "bfast", "break fast"]):
        return "breakfast"
    if any(k in lower for k in ["lunch", "afternoon", "midday"]):
        return "lunch"
    if any(k in lower for k in ["snack", "snacks", "evening", "chai time", "tea time", "tea", "coffee"]):
        return "snack"
    if any(k in lower for k in ["dinner", "night", "supper", "rat"]):
        return "dinner"
    if any(k in lower for k in ["meanwhile", "in between", "mid-morning", "munching", "munch"]):
        return "meanwhile"
    return "other"

SYSTEM_PROMPT = """You are an expert clinical sports nutritionist specializing in Indian and global diets for fat loss.
Your client is a 21-year-old male, height 168 cm, current weight 89 kg, on a fat-loss cut targeting 70 kg (daily budget ~1750 kcal).

Analyze what the user ate from their message.
Identify:
1. meal_type: One of ["breakfast", "lunch", "snack", "dinner", "meanwhile", "other"]
2. items: list of food items with:
   - name (clean readable name)
   - quantity (e.g. "2", "1", "1/2")
   - unit (e.g. "plate", "bowl", "cup", "pieces", "serving", "glass")
   - calories (realistic estimation, integer kcal)
   - protein_g (float)
   - carbs_g (float)
   - fat_g (float)
3. total_calories (sum of all items calories)
4. total_protein (sum)
5. total_carbs (sum)
6. total_fat (sum)
7. short_tip: A single brief 1-sentence tip relevant to fat loss & weight drop from 89kg -> 70kg.

Accurate Indian Food Estimations baseline:
- 1 standard wheat chapati/roti (no ghee): ~100 kcal, 3g protein
- 1 bowl cooked white rice (150g): ~195 kcal
- 1 bowl yellow dal (150g): ~150 kcal, 8g protein
- 1 plain idli: ~65 kcal, 2g protein
- 1 plain dosa: ~135 kcal, 1 masala dosa: ~250-300 kcal
- 1 cup milk tea/chai with sugar: ~90-110 kcal
- 1 boiled egg: ~75 kcal, 6g protein
- 1 plate chicken biryani: ~650-750 kcal
- 1 bowl chicken curry: ~250-300 kcal

Return STRICT JSON only matching this format with no markdown quotes or extra words:
{
  "meal_type": "lunch",
  "items": [
    {"name": "White Rice", "quantity": "1", "unit": "bowl", "calories": 195, "protein_g": 4.0, "carbs_g": 42.0, "fat_g": 0.5},
    {"name": "Yellow Dal", "quantity": "1", "unit": "bowl", "calories": 150, "protein_g": 8.0, "carbs_g": 22.0, "fat_g": 3.0}
  ],
  "total_calories": 345,
  "total_protein": 12.0,
  "total_carbs": 64.0,
  "total_fat": 3.5,
  "short_tip": "Good meal. Boost protein with egg whites or paneer to protect muscle mass during cut."
}
"""

CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
    "gemini-2.5-flash-lite",
]

def parse_food_with_gemini(message_text: str) -> Dict[str, Any]:
    """
    Parses food message using Google Gemini SDK (google-genai) with multi-model fallback.
    Falls back to offline heuristic parser if API key is missing or all models offline.
    """
    if not settings.GEMINI_API_KEY:
        return fallback_food_parser(message_text)

    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        last_error = None
        for model_name in CANDIDATE_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[SYSTEM_PROMPT, f"User ate: {message_text}"],
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                    }
                )
                
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                
                data = json.loads(raw_text)
                if not data.get("meal_type") or data.get("meal_type") == "other":
                    data["meal_type"] = extract_meal_type_heuristic(message_text)
                return data
            except Exception as model_err:
                last_error = model_err
                continue

        print(f"All Gemini models failed: {last_error}, falling back to heuristic parser")
        return fallback_food_parser(message_text)

    except Exception as e:
        print(f"Gemini API parse error: {e}, falling back to heuristic parser")
        return fallback_food_parser(message_text)

def fallback_food_parser(text: str) -> Dict[str, Any]:
    """Offline heuristic parser with a database of common Indian/Western foods."""
    meal_type = extract_meal_type_heuristic(text)
    lower = text.lower()
    
    # Common foods database (calories, protein, carbs, fat)
    food_db = {
        "chapati": (100, 3.0, 20.0, 1.0, "piece"),
        "roti": (100, 3.0, 20.0, 1.0, "piece"),
        "phulka": (85, 2.5, 18.0, 0.5, "piece"),
        "rice": (200, 4.0, 44.0, 0.5, "bowl"),
        "dal": (150, 8.0, 22.0, 3.0, "bowl"),
        "sambar": (130, 4.0, 20.0, 3.5, "bowl"),
        "curd": (100, 4.0, 5.0, 4.0, "bowl"),
        "yogurt": (100, 5.0, 6.0, 3.0, "cup"),
        "idli": (65, 2.0, 13.0, 0.3, "piece"),
        "dosa": (140, 3.0, 24.0, 3.5, "piece"),
        "egg": (75, 6.0, 0.5, 5.0, "piece"),
        "eggs": (75, 6.0, 0.5, 5.0, "piece"),
        "omelette": (160, 12.0, 2.0, 12.0, "piece"),
        "chicken": (220, 26.0, 0.0, 12.0, "serving"),
        "fish": (180, 22.0, 0.0, 8.0, "serving"),
        "paneer": (265, 18.0, 4.0, 20.0, "100g"),
        "chai": (90, 2.0, 14.0, 3.0, "cup"),
        "tea": (90, 2.0, 14.0, 3.0, "cup"),
        "coffee": (95, 2.5, 13.0, 3.5, "cup"),
        "samosa": (250, 4.0, 30.0, 13.0, "piece"),
        "biscuit": (50, 0.7, 7.5, 2.0, "piece"),
        "apple": (95, 0.5, 25.0, 0.3, "piece"),
        "banana": (105, 1.3, 27.0, 0.3, "piece"),
        "oats": (160, 5.5, 28.0, 3.0, "bowl"),
        "bread": (75, 2.5, 14.0, 1.0, "slice"),
        "salad": (80, 2.0, 12.0, 2.0, "bowl"),
    }
    
    items = []
    total_cals = 0
    total_p = 0.0
    total_c = 0.0
    total_f = 0.0
    
    # Try to find matches
    words = re.findall(r"\w+", lower)
    found_any = False
    
    for i, word in enumerate(words):
        base_word = word
        if base_word not in food_db and base_word.endswith("s") and base_word[:-1] in food_db:
            base_word = base_word[:-1]
        elif base_word not in food_db and base_word.endswith("es") and base_word[:-2] in food_db:
            base_word = base_word[:-2]

        if base_word in food_db:
            cal, p, c, f, unit = food_db[base_word]
            qty = "1"
            # check previous word for quantity (e.g. "2 chapatis")
            if i > 0 and words[i - 1].isdigit():
                multiplier = int(words[i - 1])
                qty = str(multiplier)
                cal *= multiplier
                p *= multiplier
                c *= multiplier
                f *= multiplier
            
            items.append({
                "name": base_word.capitalize(),
                "quantity": qty,
                "unit": unit,
                "calories": int(cal),
                "protein_g": round(p, 1),
                "carbs_g": round(c, 1),
                "fat_g": round(f, 1)
            })
            total_cals += int(cal)
            total_p += p
            total_c += c
            total_f += f
            found_any = True
            
    if not found_any:
        # Generic fallback
        total_cals = 350
        items.append({
            "name": text[:40],
            "quantity": "1",
            "unit": "serving",
            "calories": 350,
            "protein_g": 10.0,
            "carbs_g": 45.0,
            "fat_g": 12.0
        })
        total_p = 10.0
        total_c = 45.0
        total_f = 12.0
        
    return {
        "meal_type": meal_type,
        "items": items,
        "total_calories": total_cals,
        "total_protein": round(total_p, 1),
        "total_carbs": round(total_c, 1),
        "total_fat": round(total_f, 1),
        "short_tip": "Tracked successfully. Stay hydrated and prioritize lean protein."
    }
