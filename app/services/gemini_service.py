"""Optional Gemini helpers; no import-time network calls."""
import os
import requests
from app.config import GEMINI_API_KEY

def _generate(prompt):
    if not GEMINI_API_KEY:
        raise RuntimeError('Configure GEMINI_API_KEY')
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    response = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        headers={'x-goog-api-key': GEMINI_API_KEY},
        json={'contents': [{'parts': [{'text': prompt}]}]}, timeout=45)
    if not response.ok:
        raise RuntimeError('Gemini request failed')
    return ''.join(part.get('text', '') for part in response.json()['candidates'][0]['content']['parts'])

def generate_email_reply(email_content):
    return _generate('Write a professional, polite, concise reply to this email:\n' + email_content)

def generate_proposal(requirement):
    return _generate('Write a business proposal with introduction, solution, benefits, timeline, and conclusion:\n' + requirement)
