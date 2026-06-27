import os
from typing import List, Dict, Optional
from google import genai
from google.genai import types

SYSTEM_INSTRUCTION = """You are "Chef Assist", a premium personal chef and smart cooking assistant. 
Your goal is to help the user generate a structured cooking to-do list and meal plan based on their day, budget, schedule, and preferences.

Always output your response in clean, beautiful Markdown. Each response must contain the following sections:
1. **🍳 Today's Meal Plan** (Structured Breakfast, Lunch, and Dinner with quick prep time estimates)
2. **🛒 Smart Grocery List** (Categorized list of ingredients with quantities)
3. **🔄 Ingredient Substitutions** (Alternatives for common dietary restrictions or missing items)
4. **💰 Budget Feasibility Analysis** (Estimated cost breakdown, price-saving tips, and feasibility assessment)

Ensure the output uses formatting like tables, headers, and bullet points to look highly professional.
"""

MOCK_RESPONSE_TEMPLATES = {
    "default": """### 🍳 Today's Meal Plan

| Meal | Dish | Prep Time | Difficulty | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Breakfast** | Avocado Toast with Poached Egg | 10 mins | Easy | Smashed fresh avocado on toasted sourdough, topped with a soft poached egg and red pepper flakes. |
| **Lunch** | Mediterranean Chickpea Salad | 15 mins | Easy | Canned chickpeas tossed with cucumber, cherry tomatoes, olives, feta cheese, and lemon-herb dressing. |
| **Dinner** | One-Pan Garlic Herb Chicken & Veggies | 30 mins | Medium | Roasted chicken breast strips with broccoli, bell peppers, and baby potatoes in olive oil and garlic. |

---

### 🛒 Smart Grocery List

*   **Produce:**
    *   2 Ripe Avocados
    *   1 English Cucumber
    *   1 Pint Cherry Tomatoes
    *   1 Head of Broccoli
    *   1 Red Bell Pepper
    *   Baby Potatoes (500g)
    *   Fresh Lemon (2)
*   **Dairy & Proteins:**
    *   1 Dozen Eggs
    *   Chicken Breast (500g)
    *   Feta Cheese (100g)
*   **Pantry & Bakery:**
    *   Sourdough Bread (1 loaf)
    *   1 Can Chickpeas (Garbanzo beans)
    *   Black Olives (1 can)
    *   Olive Oil & Dried Herbs (Oregano, Thyme)

---

### 🔄 Ingredient Substitutions

*   **Avocado Toast (Gluten-Free):** Substitute sourdough bread with gluten-free bread or sweet potato slices.
*   **Feta Cheese (Vegan/Dairy-Free):** Substitute feta with dairy-free almond-based feta or seasoned tofu cubes.
*   **Chicken Breast (Vegetarian/Vegan):** Substitute chicken with firm tofu blocks or canned jackfruit seasoned similarly.

---

### 💰 Budget Feasibility Analysis

*   **Estimated Cost:** $22.50 total ($7.50 per meal).
*   **Feasibility Rating:** **High**. Utilizing canned chickpeas and basic pantry staples lowers the cost significantly.
*   **Money-Saving Tip:** Buy whole potatoes instead of pre-washed baby potatoes, and opt for dry chickpeas if you have time to soak them overnight to cut lunch costs by half.
""",
    "quick": """### 🍳 Today's Meal Plan (Express Speed)

| Meal | Dish | Prep Time | Difficulty | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Breakfast** | Overnight Berry Chia Oats | 5 mins | Easy | Rolled oats mixed with almond milk, chia seeds, maple syrup, and topped with fresh berries. |
| **Lunch** | Caprese Wrap / Sandwich | 10 mins | Easy | Fresh sliced mozzarella, tomatoes, and basil pesto wrapped in a soft tortilla or sliced bread. |
| **Dinner** | Quick Veggie Stir-Fry with Rice Noodles | 15 mins | Easy | Mixed stir-fry vegetables sautéed with soy-ginger sauce and tossed with quick-soaking rice noodles. |

---

### 🛒 Smart Grocery List

*   **Produce:**
    *   Fresh Berries (Strawberries or Blueberries)
    *   1 Large Tomato
    *   Fresh Basil Leaves
    *   Stir-fry Veggie Mix (Carrots, Snap Peas, Bell Peppers)
*   **Dairy & Proteins:**
    *   Fresh Mozzarella Cheese (1 ball)
    *   Almond Milk (1 carton)
*   **Pantry & Bakery:**
    *   Rolled Oats
    *   Chia Seeds
    *   Basil Pesto (1 jar)
    *   Tortilla Wraps
    *   Rice Noodles
    *   Soy Sauce & Ginger paste

---

### 🔄 Ingredient Substitutions

*   **Mozzarella (Dairy-Free):** Use vegan cheese shreds or sliced avocado for creaminess.
*   **Almond Milk (Nut-free):** Substitute with oat milk, soy milk, or standard cow's milk.
*   **Rice Noodles (Low-carb):** Use spiralized zucchini noodles (zoodles) or konjac noodles.

---

### 💰 Budget Feasibility Analysis

*   **Estimated Cost:** $18.00 total ($6.00 per meal).
*   **Feasibility Rating:** **Excellent**. Oats and noodles are highly budget-friendly base ingredients.
*   **Money-Saving Tip:** Buy frozen mixed berries instead of fresh berries, which are cheaper and have a much longer shelf-life.
"""
}

def generate_cooking_plan(
    user_message: str,
    history: List[Dict[str, str]],
    custom_api_key: Optional[str] = None
) -> str:
    # Try using Gemini client if an API key is available
    api_key = custom_api_key or os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        try:
            # Initialize client with specified api key
            client = genai.Client(api_key=api_key)
            
            # Format history for the Gemini API
            contents = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])]
                    )
                )
            
            # Append new user message
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=user_message)]
                )
            )
            
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7,
            )
            
            # Call Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config
            )
            
            if response.text:
                return response.text
        except Exception as e:
            print(f"Error calling Gemini API: {e}. Falling back to mock generator.")
            
    # Mock AI fallback based on keywords in user_message
    msg_lower = user_message.lower()
    if any(keyword in msg_lower for keyword in ["quick", "fast", "busy", "easy", "hurry", "minute"]):
        return MOCK_RESPONSE_TEMPLATES["quick"]
        
    return MOCK_RESPONSE_TEMPLATES["default"]
