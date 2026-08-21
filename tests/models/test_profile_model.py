from app.models.user import User
from app.models.profile import Profile

def test_profile_model_attributes() -> None:
    """Verify that Profile database model attributes and constraints are defined correctly."""
    assert Profile.__tablename__ == "profiles"
    
    # Verify expected columns are present
    assert hasattr(Profile, "id")
    assert hasattr(Profile, "user_id")
    assert hasattr(Profile, "bio")
    assert hasattr(Profile, "avatar_url")
    assert hasattr(Profile, "github_username")
    assert hasattr(Profile, "leetcode_username")
    assert hasattr(Profile, "created_at")
    assert hasattr(Profile, "updated_at")

    # Verify table unique index constraint
    indexes = Profile.__table__.indexes
    user_id_index = next((idx for idx in indexes if idx.name == "idx_profiles_user_id"), None)
    assert user_id_index is not None
    assert user_id_index.unique is True
    assert len(user_id_index.columns) == 1
    assert "user_id" in [col.name for col in user_id_index.columns]

def test_user_profile_relationship() -> None:
    """Verify SQLAlchemy 1:1 relationship attributes are configured correctly on both models."""
    assert hasattr(User, "profile")
    assert hasattr(Profile, "user")
    
    # Verify User side configuration
    user_rel = User.profile.property
    assert user_rel.uselist is False
    assert user_rel.back_populates == "user"
    assert "delete" in user_rel.cascade
    assert "delete-orphan" in user_rel.cascade

    # Verify Profile side configuration
    profile_rel = Profile.user.property
    assert profile_rel.uselist is False
    assert profile_rel.back_populates == "profile"
