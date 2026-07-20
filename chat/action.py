# PROMPTS TO get first respomder search term from a string e.g:"i cant breathe" or "i have chest pain"


from typing import Union

from instructor import from_genai, Mode

from ally.timeit import time_it
from google import genai

from chat.prompt import (
    CHAT_MODEL_ROLE_PROMPT,
    FIRST_RESPONDER_SEARCH_TERM_FROM_STRING_MODEL_ROLE_PROMPT,
)
from config.settings import (
    GEMINI_API_KEY,
    GEMINI_CHAT_MODEL,
    GEMINI_FIRST_RESPONDER_SEARCH_TERM_FROM_STRING_MODEL,
)


@time_it
def first_responder_search_term_from_string(string: str) -> Union[str, None]:
    "get first responder search term from a string e.g: i cant breathe or i have chest pain"
    try:
        # init gen ai client
        raw_client = genai.Client(api_key=GEMINI_API_KEY)
        # init instructor client
        client = from_genai(raw_client, mode=Mode.TOOLS)
        # runt he prompt to get the first responder search term from the string
        result = client.chat.completions.create(
            model=GEMINI_FIRST_RESPONDER_SEARCH_TERM_FROM_STRING_MODEL,
            # messages=[{"role": ROLE, "content": string}],
            messages=[
                {
                    "role": "system",
                    "content": FIRST_RESPONDER_SEARCH_TERM_FROM_STRING_MODEL_ROLE_PROMPT,
                },
                {
                    "role": "user",
                    "content": string,
                },
            ],
            response_model=str,
        )
        return result
    except Exception as e:
        print(f"Error in first_responder_search_term_from_string: {e}")
        return None


@time_it
def appropriate_response_from_text(text: str) -> Union[str, None]:
    "get first responder search term from a string e.g: i cant breathe or i have chest pain"
    try:
        # init gen ai client
        raw_client = genai.Client(api_key=GEMINI_API_KEY)
        # init instructor client
        client = from_genai(raw_client, mode=Mode.TOOLS)
        # runt he prompt to get the first responder search term from the string
        result = client.chat.completions.create(
            model=GEMINI_CHAT_MODEL,
            # messages=[{"role": ROLE, "content": string}],
            messages=[
                {
                    "role": "system",
                    "content": CHAT_MODEL_ROLE_PROMPT,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            response_model=str,
            generation_config={
                "temperature": 0.2  # Forces low creativity and higher predictability
            },
        )
        return result
    except Exception as e:
        print(f"Error in appropriate_response_from_text: {e}")
        return None
