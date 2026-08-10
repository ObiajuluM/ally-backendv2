from pydantic import BaseModel

from ally.timeit import time_it
from instructor import from_genai, Mode
from google import genai
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL_,
)

_SYSTEM_PROMPT = (
    "You are a public safety assistant. Given a user's description of an incident, "
    "extract a concise title (max 150 characters) and a clear, factual description suitable "
    "for a public alert."
)


class AlertContent(BaseModel):
    title: str
    description: str


@time_it
def ally_alert_from_text(text: str) -> AlertContent | None:
    try:
        raw_client = genai.Client(api_key=GEMINI_API_KEY)
        client = from_genai(raw_client, mode=Mode.TOOLS)
        return client.chat.completions.create(
            model=GEMINI_MODEL_,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_model=AlertContent,
        )
    except Exception as e:
        print(f"Error in ally_alert_from_text: {e}")
        return None
