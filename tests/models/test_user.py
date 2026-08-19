from app.models.user import User

def test_user_model_attributes() -> None:
    """Verify that User database model attributes and constraints are defined correctly."""
    assert User.__tablename__ == "users"
    
    # Verify expected columns are present
    assert hasattr(User, "id")
    assert hasattr(User, "email")
    assert hasattr(User, "hashed_password")
    assert hasattr(User, "created_at")
    assert hasattr(User, "updated_at")

    # Verify table unique index constraint
    indexes = User.__table__.indexes
    email_index = next((idx for idx in indexes if idx.name == "idx_users_email"), None)
    assert email_index is not None
    assert email_index.unique is True
    assert len(email_index.columns) == 1
    assert "email" in [col.name for col in email_index.columns]
