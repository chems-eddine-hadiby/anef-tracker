import argparse
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.fernet import Fernet


def generate_rsa():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    print("# RSA Private Key (GitHub Secret: RSA_PRIVATE_KEY)")
    print(private_pem)
    print("\n# RSA Public Key (Copy to index.html: RSA_PUBLIC_KEY_PEM)")
    print(public_pem)


def generate_storage_key():
    key = Fernet.generate_key().decode("utf-8")
    print("# Storage Key (GitHub Secret: STORAGE_KEY)")
    print(key)


def main():
    parser = argparse.ArgumentParser(description="Generate keys for ANEF Tracker")
    parser.add_argument("--rsa", action="store_true", help="Generate RSA key pair for password encryption")
    parser.add_argument("--storage", action="store_true", help="Generate Fernet key for database encryption")
    args = parser.parse_args()

    if args.rsa:
        generate_rsa()
    elif args.storage:
        generate_storage_key()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
