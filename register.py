import json
import os
import re
import sys

from anef_client import fetch_date_statut
from crypto_utils import decrypt_payload, encrypt_rsa
from email_utils import send_email
from users_store import load_users, save_users, upsert_user, find_user, utc_now_iso


REG_MARKER = "<!-- ANEF_TRACKER_REGISTRATION -->"
UPD_MARKER = "<!-- ANEF_TRACKER_PASSWORD_UPDATE -->"


def _extract_ciphertext(body):
    if not body:
        return None
    match = re.search(r"```\s*([A-Za-z0-9+/=\n]+)\s*```", body)
    if not match:
        return None
    return "".join(match.group(1).split())


def _load_request_from_issue():
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        return None

    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    issue = event.get("issue")
    if not issue:
        return None

    body = issue.get("body", "")
    if REG_MARKER in body:
        marker = "registration"
    elif UPD_MARKER in body:
        marker = "password-update"
    else:
        return None

    ciphertext = _extract_ciphertext(body)
    if not ciphertext:
        raise RuntimeError("Encrypted payload not found in issue body")

    payload = decrypt_payload(ciphertext, os.getenv("RSA_PRIVATE_KEY"))
    if not isinstance(payload, dict):
        raise RuntimeError("Invalid decrypted payload")

    if payload.get("type") and payload["type"] != marker:
        raise RuntimeError("Payload type does not match marker")

    payload["type"] = marker
    return payload


def _load_request_from_env():
    reg_email = os.getenv("REG_EMAIL")
    reg_user = os.getenv("REG_USERNAME")
    reg_pass = os.getenv("REG_PASSWORD")

    if reg_email and reg_user and reg_pass:
        return {"type": "registration", "e": reg_email, "u": reg_user, "p": reg_pass}

    upd_email = os.getenv("UPD_EMAIL")
    upd_old = os.getenv("UPD_OLD_PASSWORD")
    upd_new = os.getenv("UPD_NEW_PASSWORD")

    if upd_email and upd_old and upd_new:
        return {"type": "password-update", "e": upd_email, "op": upd_old, "np": upd_new}

    return None


def _send_failure(email, subject_prefix, error_message):
    subject = f"ANEF Tracker: {subject_prefix} echouee"
    body = (
        "Bonjour,\n\n"
        "Votre demande n'a pas pu etre finalisee.\n"
        f"Raison: {error_message}\n\n"
        "Verifiez vos identifiants ANEF et reessayez.\n"
    )
    send_email(email, subject, body)


def _handle_registration(payload, users_path):
    email = payload.get("e")
    username = payload.get("u")
    password = payload.get("p")
    rsa_key = os.getenv("RSA_PRIVATE_KEY")

    if not email or not username or not password:
        raise RuntimeError("Missing registration fields")

    date_statut = fetch_date_statut(username, password)

    # Double layer: encrypt password field with RSA before storing
    encrypted_pass = encrypt_rsa(password, rsa_key)

    users = load_users(users_path)
    user, created = upsert_user(users, email, username, encrypted_pass, date_statut)
    user["last_checked_at"] = utc_now_iso()
    save_users(users, users_path)

    subject = "ANEF Tracker: inscription reussie"
    body = (
        "Bonjour,\n\n"
        "Votre inscription est confirmee.\n"
        f"Statut actuel (date_statut): {date_statut}\n\n"
        "Vous recevrez un email a chaque changement de statut.\n"
    )
    send_email(email, subject, body)

    action = "created" if created else "updated"
    print(f"Registration {action} for {email}")


def _handle_password_update(payload, users_path):
    email = payload.get("e")
    old_password = payload.get("op")
    new_password = payload.get("np")
    rsa_key = os.getenv("RSA_PRIVATE_KEY")

    if not email or not old_password or not new_password:
        raise RuntimeError("Missing password update fields")

    users = load_users(users_path)
    user = find_user(users, email)
    if not user:
        raise RuntimeError("Email not registered")

    username = user.get("username")
    if not username:
        raise RuntimeError("Username missing in users.json")

    date_statut = fetch_date_statut(username, old_password)

    # Double layer: encrypt new password field with RSA before storing
    encrypted_new_pass = encrypt_rsa(new_password, rsa_key)

    user["password"] = encrypted_new_pass
    user["current_status"] = date_statut
    user["updated_at"] = utc_now_iso()
    user["last_checked_at"] = utc_now_iso()
    save_users(users, users_path)

    subject = "ANEF Tracker: mot de passe mis a jour"
    body = (
        "Bonjour,\n\n"
        "Votre mot de passe a bien ete mis a jour.\n"
        f"Statut actuel (date_statut): {date_statut}\n\n"
        "Vous continuerez a recevoir les alertes automatiquement.\n"
    )
    send_email(email, subject, body)

    print(f"Password updated for {email}")


def main():
    users_path = os.getenv("USERS_PATH", "users.json")

    try:
        payload = _load_request_from_issue() or _load_request_from_env()
        if not payload:
            print("No registration/update payload found; exiting.")
            return 0

        req_type = payload.get("type")
        if req_type == "registration":
            _handle_registration(payload, users_path)
        elif req_type == "password-update":
            _handle_password_update(payload, users_path)
        else:
            raise RuntimeError(f"Unknown request type: {req_type}")

    except Exception as exc:
        email = None
        if "payload" in locals() and isinstance(payload, dict):
            email = payload.get("e")

        error_message = str(exc)
        print(f"Request failed: {error_message}")

        if email:
            try:
                if payload.get("type") == "password-update":
                    _send_failure(email, "mise a jour mot de passe", error_message)
                else:
                    _send_failure(email, "inscription", error_message)
            except Exception as email_exc:
                print(f"Failed to send error email: {email_exc}")

        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
