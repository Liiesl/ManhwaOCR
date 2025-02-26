# gemini_handler.py
import google.generativeai as genai
from PyQt5.QtWidgets import QMessageBox

def translate_with_gemini(api_key, text, model_name="gemini-2.0-flash", target_lang="English"):
    """Send text to Gemini API for translation."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""translate and change only the korean text to {target_lang}, keep everything else.

        {text}"""
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API Error: {str(e)}")