import base64
import json
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key


def decrypt_payload(ciphertext_b64, private_key_pem):
    """Decrypts the initial registration/update payload from the browser."""
    if not private_key_pem:
        raise RuntimeError("RSA private key missing (RSA_PRIVATE_KEY)")

    key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    ciphertext = base64.b64decode(ciphertext_b64)

    plaintext = key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return json.loads(plaintext.decode("utf-8"))


def encrypt_rsa(plaintext, private_key_pem):
    """Encrypts a string using the public key derived from the private key."""
    key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    public_key = key.public_key()
    
    ciphertext = public_key.encrypt(
        plaintext.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )
    )
    return base64.b64encode(ciphertext).decode("utf-8")


def decrypt_rsa(ciphertext_b64, private_key_pem):
    """Decrypts a string using the private key."""
    key = load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    ciphertext = base64.b64decode(ciphertext_b64)
    
    plaintext = key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        )
    )
    return plaintext.decode("utf-8")
