from typing import Any, List, Optional
from pydantic import BaseModel, Field

from app.schemas.sync import (
    LeetCodeResponseSchema,
    validate_platform_data,
)
from app.utils.exceptions import PlatformValidationException

class ParsedLeetCodeTagSolved(BaseModel):
    """Parsed model representing a validated LeetCode tag solved count."""
    tag_name: str
    tag_slug: str
    solved_count: int

class ParsedLeetCodeTagGroups(BaseModel):
    """Parsed model representing fundamental, intermediate, and advanced LeetCode tag listings."""
    fundamental: List[ParsedLeetCodeTagSolved] = Field(default_factory=list)
    intermediate: List[ParsedLeetCodeTagSolved] = Field(default_factory=list)
    advanced: List[ParsedLeetCodeTagSolved] = Field(default_factory=list)

class ParsedLeetCodeProblems(BaseModel):
    """Parsed model representing LeetCode problems solved and submissions statistics by difficulty."""
    easy_solved: int = 0
    easy_submissions: int = 0
    medium_solved: int = 0
    medium_submissions: int = 0
    hard_solved: int = 0
    hard_submissions: int = 0
    total_solved: int = 0
    total_submissions: int = 0

class ParsedLeetCodeData(BaseModel):
    """Aggregate model representing complete parsed LeetCode profile, problems, and tag statistics."""
    username: str
    real_name: Optional[str] = None
    about_me: Optional[str] = None
    user_avatar: Optional[str] = None
    
    problems: ParsedLeetCodeProblems
    tags: ParsedLeetCodeTagGroups

class LeetCodeDataParser:
    """Parser for validating and converting raw LeetCode GraphQL payloads into structured DevTrack formats."""

    @staticmethod
    def parse(raw_payload: Any) -> ParsedLeetCodeData:
        """
        Accept, validate, and parse raw LeetCode GraphQL payload.
        Raises PlatformValidationException for malformed payloads.
        """
        if not isinstance(raw_payload, dict):
            raise PlatformValidationException(
                platform="LeetCode",
                details="Raw payload must be a dictionary."
            )

        # 1. Validate full structure against LeetCodeResponseSchema
        response_schema = validate_platform_data(
            LeetCodeResponseSchema,
            raw_payload,
            platform="LeetCode"
        )
        
        matched_user = response_schema.data.matchedUser
        if not matched_user:
            raise PlatformValidationException(
                platform="LeetCode",
                details="matchedUser data is missing."
            )

        # 2. Extract profile details
        real_name = None
        about_me = None
        user_avatar = None
        if matched_user.profile:
            real_name = matched_user.profile.realName
            about_me = matched_user.profile.aboutMe
            user_avatar = matched_user.profile.userAvatar

        # 3. Extract and map difficulty stats explicitly by difficulty string
        easy_solved = 0
        easy_submissions = 0
        medium_solved = 0
        medium_submissions = 0
        hard_solved = 0
        hard_submissions = 0
        total_solved = 0
        total_submissions = 0
        
        has_all_key = False
        
        for item in matched_user.submitStats.acSubmissionNum:
            diff = item.difficulty
            if diff == "Easy":
                easy_solved = item.count
                easy_submissions = item.submissions
            elif diff == "Medium":
                medium_solved = item.count
                medium_submissions = item.submissions
            elif diff == "Hard":
                hard_solved = item.count
                hard_submissions = item.submissions
            elif diff == "All":
                total_solved = item.count
                total_submissions = item.submissions
                has_all_key = True

        # Fallback calculation if "All" is missing
        if not has_all_key:
            total_solved = easy_solved + medium_solved + hard_solved
            total_submissions = easy_submissions + medium_submissions + hard_submissions

        problems = ParsedLeetCodeProblems(
            easy_solved=easy_solved,
            easy_submissions=easy_submissions,
            medium_solved=medium_solved,
            medium_submissions=medium_submissions,
            hard_solved=hard_solved,
            hard_submissions=hard_submissions,
            total_solved=total_solved,
            total_submissions=total_submissions,
        )

        # 4. Extract and map tag stats
        fundamental_tags = []
        intermediate_tags = []
        advanced_tags = []
        
        if matched_user.tagProblemsSolved:
            for item in matched_user.tagProblemsSolved.fundamental:
                fundamental_tags.append(
                    ParsedLeetCodeTagSolved(
                        tag_name=item.tagName,
                        tag_slug=item.tagSlug,
                        solved_count=item.solvedCount
                    )
                )
            for item in matched_user.tagProblemsSolved.intermediate:
                intermediate_tags.append(
                    ParsedLeetCodeTagSolved(
                        tag_name=item.tagName,
                        tag_slug=item.tagSlug,
                        solved_count=item.solvedCount
                    )
                )
            for item in matched_user.tagProblemsSolved.advanced:
                advanced_tags.append(
                    ParsedLeetCodeTagSolved(
                        tag_name=item.tagName,
                        tag_slug=item.tagSlug,
                        solved_count=item.solvedCount
                    )
                )

        tags = ParsedLeetCodeTagGroups(
            fundamental=fundamental_tags,
            intermediate=intermediate_tags,
            advanced=advanced_tags
        )

        return ParsedLeetCodeData(
            username=matched_user.username,
            real_name=real_name,
            about_me=about_me,
            user_avatar=user_avatar,
            problems=problems,
            tags=tags
        )
