import bcrypt

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using the native bcrypt algorithm.
    
    Args:
        password: The plaintext password string to hash.
        
    Returns:
        The securely hashed password string (UTF-8 encoded).
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    
    Args:
        plain_password: The plaintext password to check.
        hashed_password: The stored bcrypt hash to compare against.
        
    Returns:
        True if the password matches the hash, False otherwise.
    """
    try:
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Catch any structural hash validation failures and return False
        return False
