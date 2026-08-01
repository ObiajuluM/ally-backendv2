import requests

from ally.models import User
from config.settings import SMS_USERNAME, SMS_PASSWORD


def shortenurl(url: str) -> str:
    return url


def get_matching_trusted_contacts(user: User, numbers: list[str]) -> list[str]:
    """
    Returns up to 5 phone numbers that are both in the user's
    trusted contacts and the provided numbers list.
    """

    if not user.my_information:
        return []

    trusted_contacts = user.my_information.trusted_contacts or []

    # Fast lookup
    provided_numbers = set(numbers)

    matches = [
        contact["phone"]
        for contact in trusted_contacts
        if contact.get("phone") in provided_numbers
    ]

    return matches[:5]


def send_sms(user: User, phone_numbers: list[str]) -> bool:
    try:
        # Generate the message text
        first_name = user.username.split()[0]
        msg = f"""
            {first_name} is sharing their live location with you.
            View: {shortenurl(f"https://safetyally.app/l/{user.id}")}
            """

        # send sms
        response = requests.post(
            "https://api.sms-gate.app/3rdparty/v1/messages",
            auth=(SMS_USERNAME, SMS_PASSWORD),
            json={
                "textMessage": {"text": msg},
                "phoneNumbers": get_matching_trusted_contacts(user, phone_numbers),
            },
        )
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False
