# from pydantic import BaseModel

# from ally.timeit import time_it
# from instructor import from_genai, Mode
# from google import genai
# from config.settings import (
#     GEMINI_API_KEY,
#     GEMINI_MODEL_,
# )

# _SYSTEM_PROMPT = (
#     "You are a public safety assistant. Given a user's description of an incident, "
#     "extract a concise title (max 150 characters) and a clear, factual description suitable "
#     "for a public alert."
# )


# class AlertContent(BaseModel):
#     title: str
#     description: str


# @time_it
# def ally_alert_from_text(text: str) -> AlertContent | None:
#     try:
#         raw_client = genai.Client(api_key=GEMINI_API_KEY)
#         client = from_genai(raw_client, mode=Mode.TOOLS)
#         return client.chat.completions.create(
#             model=GEMINI_MODEL_,
#             messages=[
#                 {"role": "system", "content": _SYSTEM_PROMPT},
#                 {"role": "user", "content": text},
#             ],
#             response_model=AlertContent,
#             config={
#                 "temperature": 1,
#             },
#         )
#     except Exception as e:
#         print(f"Error in ally_alert_from_text: {e}")
#         return None


from pydantic import BaseModel, Field
from ally.timeit import time_it
from instructor import from_genai, Mode
from google import genai
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL_,
)

_SYSTEM_PROMPT = """You are an expert public safety dispatcher operating in Nigeria. 
Your job is to rapidly analyze a user's potentially frantic, shorthand, or colloquial description of an incident, and convert it into a clear, actionable public safety alert.

CRITICAL INSTRUCTIONS:
1. Translate Local Context: Seamlessly interpret Nigerian Pidgin and street slang (e.g., "One chance" -> kidnapping/robbery in a commercial vehicle, "agbero/area boys" -> armed thugs/hoodlums, "keke" -> tricycle). 
2. Be Objective & Factual: Strip away panic words, profanity, and first-person perspectives ("Help me", "I am running"). Focus entirely on WHAT is happening and WHERE.
3. No Hallucinations: If a detail (like location or weapons) is not explicitly mentioned, do not invent it.
4. Tone: Urgent, professional, and universally understood.
"""


class AlertContent(BaseModel):
    title: str = Field(
        ...,
        max_length=150,
        description="A concise, urgent title for the alert. e.g., 'Armed Robbery on Aba Road' or 'Suspected Kidnapping in Transit'.",
    )
    description: str = Field(
        ...,
        description="A factual, clear description of the incident, stripped of panic and translated from local slang into standard English.",
    )
    # Optional: You can easily add tags/categories here in the future
    # category: str = Field(..., description="Categorize as: Violence, Medical, Accident, or Suspicious Activity")


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
            config={
                # Lowered from 1.0. Safety alerts need high determinism, not creativity.
                "temperature": 0.2,
            },
        )
    except Exception as e:
        print(f"Error generating Ally alert: {e}")
        # Consider logging this to Sentry/Datadog in production
        return None
