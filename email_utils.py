import os
import requests


def send_email(to_address, subject, body):
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("EMAIL_FROM") or "onboarding@resend.dev"

    if not api_key:
        print(f"RESEND_API_KEY missing. Skipping email to {to_address}.")
        return

    # If sender is the default, Resend only allows sending to the email registered in the account.
    # For a real domain, you'd verify it in Resend.
    
    payload = {
        "from": f"ANEF Tracker <{sender}>",
        "to": to_address,
        "subject": subject,
        "text": body,
    }

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10
        )
        
        if response.status_code not in [200, 201, 202]:
            print(f"Resend API failed ({response.status_code}): {response.text}")
        else:
            print(f"Email sent successfully to {to_address}")
            
    except Exception as exc:
        print(f"Error calling Resend API: {exc}")
