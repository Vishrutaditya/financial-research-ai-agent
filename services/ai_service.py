import google.generativeai as genai
from utils.config import GEMINI_API_KEY

# Configure the Gemini API key for the Google Generative AI service
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_ai_market_insight(company_name, sector, industry):
    """
    Generates a brief 2-3 sentence strategic market overview for the company.
    """
    if not GEMINI_API_KEY:
        return "AI Insight unavailable: GEMINI_API_KEY is not configured in your .env file."
        
    try:
        # Utilizing the gemini-2.5-flash model
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
        You are an expert financial analyst. Analyze the following company profile:
            Company: {company_name}
            Sector: {sector}
            Industry: {industry}

            CRITICAL VALIDATION STEP: 
            If the company name is a placeholder, a generic ticker symbol, or if the sector/industry values are missing or "N/A", do not generate a fake analysis. Instead, output exactly this message: "Market insights are unavailable because a valid company profile could not be identified. Please verify the stock ticker and try again."

            IF THE COMPANY IS VALID:
            1. Provide a concise, professional 2-sentence strategic market insight highlighting its core industry positioning or a major macroeconomic theme impacting its business sector. 
            2. Conclude with a single, distinct sentence evaluating whether current structural trends lean toward a technical 'Buy' or 'Sell/Hold' posture based purely on sector tailwinds, explicitly stating the core justification. Avoid generic filler language; keep it punchy, corporate, and tailored for investors.            
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        return f"Could not generate AI insights at this time. (Error: {e})"