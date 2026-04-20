"""
Custom encrypted field for storing sensitive text.

How it works:
- When saving to the database: plaintext → encrypted → stored as base64 string
- When reading from the database: base64 string → decrypted → returned as plaintext
- The encryption key lives in environment variables, never in the database
- If someone steals the database file, they get gibberish
- If someone has both the database AND the key, they can read the data

Uses Fernet symmetric encryption from the cryptography library.
Fernet guarantees that data encrypted with it cannot be read or tampered
with without the key. It also includes a timestamp so you can tell when
something was encrypted.

Why a custom field instead of a third-party package?
Because this is a safety-critical product. We want to understand exactly
what the encryption does, not depend on a package we have not read.
The code is simple enough to verify by hand.
"""
import base64

from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _get_fernet():
    """
    Get the Fernet encryption instance using the key from settings.

    The key must be a URL-safe base64-encoded 32-byte key.
    Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    key = settings.FIELD_ENCRYPTION_KEY.encode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """
    A TextField that encrypts its content before saving to the database
    and decrypts it when reading from the database.

    In the database, the content looks like:
    gAAAAABl... (a long base64 string)

    In Python, it looks like normal text.
    """

    def get_prep_value(self, value):
        """Called when saving to the database. Encrypts the value."""
        if value is None:
            return value
        f = _get_fernet()
        encrypted = f.encrypt(value.encode("utf-8"))
        return encrypted.decode("utf-8")

    def from_db_value(self, value, expression, connection):
        """Called when reading from the database. Decrypts the value."""
        if value is None:
            return value
        try:
            f = _get_fernet()
            decrypted = f.decrypt(value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except Exception:
            # If decryption fails, the data might be old unencrypted text.
            # Return it as-is so existing data still works during migration.
            return value
