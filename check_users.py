import os
from anef_client import fetch_date_statut
from crypto_utils import decrypt_rsa
from email_utils import send_email
from users_store import load_users, save_users, utc_now_iso


def _notify_change(email, old_status, new_status):
    subject = "ANEF Tracker: changement detecte"
    body = (
        "Bonjour,\n\n"
        "Un changement de statut a ete detecte sur votre dossier.\n"
        f"Ancien date_statut: {old_status}\n"
        f"Nouveau date_statut: {new_status}\n\n"
        "Vous pouvez vous connecter a ANEF pour voir les details.\n"
    )
    send_email(email, subject, body)


def _notify_login_failure(email, error_message):
    subject = "ANEF Tracker: echec de connexion"
    body = (
        "Bonjour,\n\n"
        "La verification automatique n'a pas pu se connecter a votre compte ANEF.\n"
        f"Raison: {error_message}\n\n"
        "Si vous avez change votre mot de passe, mettez-le a jour dans le service.\n"
    )
    send_email(email, subject, body)


def main():
    users_path = os.getenv("USERS_PATH", "users.json")
    rsa_key = os.getenv("RSA_PRIVATE_KEY")
    users = load_users(users_path)
    if not users:
        print("No users to check.")
        return 0

    now = utc_now_iso()
    changed = False
    notify_on_failure = os.getenv("NOTIFY_ON_FAILURE", "").strip().lower() in {"1", "true", "yes", "on"}

    for user in users:
        email = user.get("email")
        username = user.get("username")
        password_encrypted = user.get("password")
        if not email or not username or not password_encrypted:
            print(f"Skipping user with missing fields: {email or 'unknown'}")
            continue

        # Decrypt password for this check session
        try:
            # Check if it looks like base64 RSA, otherwise assume plain (backward compat)
            if len(password_encrypted) > 100: 
                password = decrypt_rsa(password_encrypted, rsa_key)
            else:
                password = password_encrypted
        except Exception as exc:
            print(f"Failed to decrypt password for {email}: {exc}")
            continue

        try:
            new_status = fetch_date_statut(username, password)
        except Exception as exc:
            print(f"Login failed for {email}: {exc}")
            if notify_on_failure:
                try:
                    _notify_login_failure(email, str(exc))
                except Exception as mail_exc:
                    print(f"Failed to send failure email to {email}: {mail_exc}")
            continue

        old_status = user.get("current_status")
        user["last_checked_at"] = now

        if old_status != new_status:
            user["current_status"] = new_status
            user["updated_at"] = now
            changed = True
            print(f"Status changed for {email}")
            try:
                _notify_change(email, old_status, new_status)
            except Exception as mail_exc:
                print(f"Failed to send change email to {email}: {mail_exc}")

    if changed:
        save_users(users, users_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
