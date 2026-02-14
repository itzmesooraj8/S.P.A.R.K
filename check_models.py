import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

print("Finding all the 'magic books' your key can read...")
print("--------------------------------------------------")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)
