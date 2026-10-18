"""The application service boundary is structural and adapter-independent."""
from dataclasses import dataclass

from app.application.contracts import UseCase


@dataclass(frozen=True)
class RenameCommand:
    current: str
    replacement: str


class RenameUseCase:
    """Small contract fixture; not a production business module."""

    def execute(self, command: RenameCommand) -> str:
        if not command.replacement.strip():
            raise ValueError("replacement must not be blank")
        return command.replacement.strip()


def test_use_case_contract_accepts_a_concrete_application_service() -> None:
    service: UseCase[RenameCommand, str] = RenameUseCase()
    assert service.execute(RenameCommand("old", " new ")) == "new"
