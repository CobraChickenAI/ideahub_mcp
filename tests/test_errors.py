from ideahub_mcp.errors import IdeaHubError


def test_error_serializes() -> None:
    e = IdeaHubError(code="actor_unresolved", message="no actor", fix="pass actor")
    assert e.as_dict() == {
        "code": "actor_unresolved",
        "message": "no actor",
        "fix": "pass actor",
    }
