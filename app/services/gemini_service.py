import google.generativeai as genai

from app.config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# Working model from your account
model = genai.GenerativeModel("gemini-2.5-flash")


def generate_email_reply(email_content):

    prompt = f"""
You are a professional business email assistant.

Generate a professional reply for the following email:

{email_content}

Keep the response:
- Professional
- Polite
- Concise
"""

    response = model.generate_content(prompt)

    return response.text


def generate_proposal(requirement):

    prompt = f"""
You are an expert proposal writer.

Create a professional business proposal.

Requirement:
{requirement}

Include:
1. Introduction
2. Proposed Solution
3. Benefits
4. Timeline
5. Conclusion
"""

    response = model.generate_content(prompt)

    return response.text