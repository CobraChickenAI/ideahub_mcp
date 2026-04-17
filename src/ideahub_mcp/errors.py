from __future__ import annotations


class IdeaHubError(Exception):
    def __init__(self, code: str, message: str, fix: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fix = fix

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "fix": self.fix}
