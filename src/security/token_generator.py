import secrets


def generate_secure_token(length: int = 32):
    """
    Generate a secure random token.

    Returns:
        str: Securely generated token.
    """
    return secrets.token_urlsafe(length)
