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
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


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
        # Fernet tokens always start with this prefix. If the stored value
        # does not look like a token, it is legacy plaintext from before
        # encryption was added. Return it unchanged (migration compatibility).
        if not value.startswith("gAAAAA"):
            return value
        try:
            f = _get_fernet()
            decrypted = f.decrypt(value.encode("utf-8"))
            return decrypted.decode("utf-8")
        except InvalidToken:
            # The value looks like an encrypted token but could not be
            # decrypted. This is the dangerous case: a wrong or rotated
            # FIELD_ENCRYPTION_KEY, or tampered/corrupted data. Do NOT
            # silently return the stored ciphertext. Make the failure loud
            # so it is caught, not hidden behind seemingly-normal reads.
            logger.error(
                "EncryptedTextField: value looks encrypted but could not be "
                "decrypted. Check FIELD_ENCRYPTION_KEY (wrong/rotated key) or "
                "possible data corruption."
            )
            raise
