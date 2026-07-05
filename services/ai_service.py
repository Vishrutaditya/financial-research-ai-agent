import google.generativeai as genai
from utils.config import GEMINI_API_KEY

# Configure the SDK with your secure API key
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_ai_market_insight(company_name, sector, industry):
    """
    Generates a brief 2-3 sentence strategic market overview for the company.
    """
    if not GEMINI_API_KEY:
        return "AI Insight unavailable: GEMINI_API_KEY is not configured in your .env file."
        
    try:
        # Utilizing the lightning-fast, cost-effective gemini-2.5-flash model
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        Provide a concise, professional 2-sentence market insight for {company_name}, 
        operating in the {sector} sector ({industry} industry). 
        Highlight its core industry position or a major current theme in this business sector.
        Keep it punchy, corporate, and tailored for investors. Tell whether to buy or sell, and why, in a single sentence. Avoid generic statements.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        return f"Could not generate AI insights at this time. (Error: {e})"