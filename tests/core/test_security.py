from app.core.security import hash_password, verify_password

def test_password_hashing_success() -> None:
    """Verify that a plaintext password can be successfully hashed and verified."""
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    
    # Verify hash is not plaintext
    assert hashed != password
    assert len(hashed) > 0
    
    # Verify correct password matches
    assert verify_password(password, hashed) is True

def test_password_verification_failure() -> None:
    """Verify that incorrect passwords fail verification against the hash."""
    password = "SuperSecurePassword123!"
    hashed = hash_password(password)
    
    # Verify incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False

def test_password_salting() -> None:
    """Verify that two hashes of the same password are not identical (salting is active)."""
    password = "SuperSecurePassword123!"
    hash1 = hash_password(password)
    hash2 = hash_password(password)
    
    assert hash1 != hash2
