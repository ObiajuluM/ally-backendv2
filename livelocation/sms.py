import requests

from ally.models import User
from config.settings import SMS_USERNAME, SMS_PASSWORD
import uuid
import base64


def shorten_uuid(uid: str) -> str:
    u = uid if isinstance(uid, uuid.UUID) else uuid.UUID(uid)
    encoded = base64.urlsafe_b64encode(u.bytes).decode().rstrip("=")
    print(encoded)
    return encoded


def expand_uuid(encoded: str) -> str:
    padding = "=" * (-len(encoded) % 4)
    decoded = uuid.UUID(bytes=base64.urlsafe_b64decode(encoded + padding))
    print(decoded)
    return str(decoded)


def get_matching_trusted_contacts(user: User, numbers: list[str]) -> list[str]:
    """
    Returns up to 5 phone numbers that are both in the user's
    trusted contacts and the provided numbers list.
    """

    # if not user.my_information:
    #     return []

    # trusted_contacts = user.my_information.trusted_contacts or []

    # # Fast lookup
    # provided_numbers = set(numbers)

    # matches = [
    #     contact["phone"]
    #     for contact in trusted_contacts
    #     if contact.get("phone") in provided_numbers
    # ]

    # return matches[:5]
    return (
        [
            contact["phone"]
            for contact in user.my_information.trusted_contacts
            # if contact.get("phone") in numbers
        ][:5]
        if user.my_information
        else []
    )


def send_sms(user: User, phone_numbers: list[str]) -> bool:

    try:
        # Generate the message text
        first_name = user.username.split()[0]
        msg = f"""{first_name[:3]}.. is sharing their live location with you: https://safetyally.app/l/{shorten_uuid(user.id)}"""

        # send sms
        response = requests.post(
            "https://api.sms-gate.app/3rdparty/v1/messages",
            auth=(SMS_USERNAME, SMS_PASSWORD),
            json={
                "textMessage": {"text": msg},
                "phoneNumbers": get_matching_trusted_contacts(user, phone_numbers),
            },
        )
        print(f"SMS API response: {response.status_code == 202}")
        return response.status_code == 202
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False
