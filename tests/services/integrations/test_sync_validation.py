import pytest
from app.schemas.sync import (
    validate_platform_data,
    GitHubProfileSyncSchema,
    GitHubRepoSyncSchema,
)
from app.utils.exceptions import PlatformValidationException

def test_valid_github_profile_validation() -> None:
    """Verify that a valid GitHub profile payload validates successfully."""
    payload = {"id": 12345, "login": "octocat"}
    validated = validate_platform_data(
        schema=GitHubProfileSyncSchema,
        data=payload,
        platform="github",
    )
    # Check that generic helper correctly returns an instance of the schema passed to it
    assert isinstance(validated, GitHubProfileSyncSchema)
    assert validated.id == 12345
    assert validated.login == "octocat"

def test_valid_github_repo_validation() -> None:
    """Verify that a valid GitHub repository payload validates successfully."""
    payload = {"id": 67890, "name": "hello-world"}
    validated = validate_platform_data(
        schema=GitHubRepoSyncSchema,
        data=payload,
        platform="github",
    )
    assert isinstance(validated, GitHubRepoSyncSchema)
    assert validated.id == 67890
    assert validated.name == "hello-world"

def test_payload_missing_required_field_raises_exception() -> None:
    """Verify that a payload missing a required field raises PlatformValidationException."""
    # Missing login
    payload = {"id": 12345}
    with pytest.raises(PlatformValidationException) as excinfo:
        validate_platform_data(
            schema=GitHubProfileSyncSchema,
            data=payload,
            platform="github",
        )
    # Verify exception code and details structure
    assert excinfo.value.code == "PLATFORM_VALIDATION_FAILED"
    assert "login: Field required" in excinfo.value.message
    # Check that the exception does not leak the complete raw payload
    assert "octocat" not in excinfo.value.message

def test_invalid_identifier_type_raises_exception() -> None:
    """Verify that an invalid identifier type (e.g. string for StrictInt id) raises PlatformValidationException."""
    # id is string, but expected StrictInt
    payload = {"id": "not-an-integer", "login": "octocat"}
    with pytest.raises(PlatformValidationException) as excinfo:
        validate_platform_data(
            schema=GitHubProfileSyncSchema,
            data=payload,
            platform="github",
        )
    assert excinfo.value.code == "PLATFORM_VALIDATION_FAILED"
    assert "id: Input should be a valid integer" in excinfo.value.message

def test_exception_context_contains_platform_and_failure_details() -> None:
    """Verify exception contains useful platform/error context without leaking raw payload."""
    payload = {"id": "12345", "login": "octocat"} # string for id instead of StrictInt
    with pytest.raises(PlatformValidationException) as excinfo:
        validate_platform_data(
            schema=GitHubProfileSyncSchema,
            data=payload,
            platform="custom_platform",
        )
    # Check platform is in the message
    assert "custom_platform" in excinfo.value.message
    # Check error details in the message
    assert "id: Input should be a valid integer" in excinfo.value.message
