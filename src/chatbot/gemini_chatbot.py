"""
Free AI Chatbot using Google Gemini API
✅ Completely FREE - 60 requests/minute
✅ No credit card required
✅ Very good quality responses
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Try importing Google Generative AI
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    print("[WARN] Google Generative AI not installed")
    print("Run: pip install google-generativeai")
    HAS_GEMINI = False


class GeminiChatbot:
    """Free AI chatbot using Google Gemini"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini chatbot
        
        Args:
            api_key: Google API key (get free at https://makersuite.google.com/app/apikey)
        """
        if not HAS_GEMINI:
            raise ImportError("google-generativeai not installed")
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found.\n"
                "Get free key at: https://makersuite.google.com/app/apikey\n"
                "Add to .env: GEMINI_API_KEY=your_key_here"
            )
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 1.5 Flash (fastest, free)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # System prompt for air quality
        self.system_prompt = """You are an air quality expert assistant helping people understand air pollution in India.

Key information to share:

**Pollutants:**
- PM2.5: Fine particles <2.5 microns. Main health concern. Safe: <50 µg/m³
- PM10: Coarse particles <10 microns. Safe: <100 µg/m³
- NO₂: Nitrogen dioxide from vehicles. Safe: <40 µg/m³
- SO₂: Sulfur dioxide from industry. Safe: <20 µg/m³
- CO: Carbon monoxide from combustion. Safe: <1 mg/m³
- O₃: Ground-level ozone. Safe: <60 µg/m³

**AQI Categories:**
- 0-50: Good (Green) - Air quality is satisfactory
- 51-100: Moderate (Yellow) - Acceptable for most people
- 101-150: Unhealthy for Sensitive Groups (Orange)
- 151-200: Unhealthy (Red)
- 201-300: Very Unhealthy (Purple)
- 301+: Hazardous (Maroon)

**Protection Tips:**
- Stay indoors when AQI > 150
- Use N95/N99 masks outdoors
- Air purifiers with HEPA filters indoors
- Avoid outdoor exercise during high pollution
- Keep windows closed during peak pollution hours

**Health Effects:**
- Short-term: Coughing, throat irritation, breathing difficulty
- Long-term: Lung disease, heart problems, reduced lung function

Be concise, friendly, and helpful. Use simple language. Focus on practical advice."""
    
    def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Get response from Gemini
        
        Args:
            message: User question
            context: Additional context (pollution data, etc.)
        
        Returns:
            AI response
        """
        
        # Add context if provided
        full_prompt = self.system_prompt
        
        if context:
            if context.get("current_pollution"):
                full_prompt += f"\n\nCurrent pollution levels in India:\n{context['current_pollution']}"
        
        full_prompt += f"\n\nUser question: {message}\n\nProvide a helpful, concise answer:"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}\n\nPlease try rephrasing your question."


# For backward compatibility with existing API
def get_chatbot_response(message: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Simple function to get chatbot response
    
    Args:
        message: User question
        context: Additional context
    
    Returns:
        AI response
    """
    try:
        chatbot = GeminiChatbot()
        return chatbot.chat(message, context)
    except Exception as e:
        return f"Chatbot unavailable: {str(e)}"


# Test function
def test_chatbot():
    """Test the Gemini chatbot"""
    print("\n" + "=" * 70)
    print("TESTING GOOGLE GEMINI CHATBOT (FREE)")
    print("=" * 70)
    
    if not HAS_GEMINI:
        print("\n❌ google-generativeai not installed")
        print("Run: pip install google-generativeai")
        return
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ GEMINI_API_KEY not found in .env")
        print("\n📝 To get a FREE API key:")
        print("1. Go to: https://makersuite.google.com/app/apikey")
        print("2. Sign in with Google account")
        print("3. Click 'Create API Key'")
        print("4. Add to .env: GEMINI_API_KEY=your_key_here")
        return
    
    print(f"\n✅ API Key found: {api_key[:10]}...")
    
    try:
        chatbot = GeminiChatbot()
        
        # Test questions
        questions = [
            "What is PM2.5?",
            "Is Delhi's air quality dangerous?",
            "How can I protect myself from air pollution?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'-' * 70}")
            print(f"Q{i}: {question}")
            print(f"{'-' * 70}")
            
            response = chatbot.chat(question)
            print(f"A: {response}")
        
        print("\n" + "=" * 70)
        print("✅ CHATBOT WORKING!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    test_chatbot()