
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
    print("Client initialized.")
    
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Hello, S.P.A.R.K.!",
        config=None
    )
    print("Response received:", response.text)
    
except Exception as e:
    print(f"Error: {e}")
