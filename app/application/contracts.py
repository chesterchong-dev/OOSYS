"""Stable application-layer interfaces used by API adapters."""
from typing import Protocol, TypeVar

CommandT = TypeVar("CommandT", contravariant=True)
ResultT = TypeVar("ResultT", covariant=True)


class UseCase(Protocol[CommandT, ResultT]):
    """A single application operation accepting a command and returning a result.

    Concrete use cases own authorization coordination, domain orchestration,
    and explicit transaction boundaries. API routers inject this interface
    rather than importing concrete services or persistence implementations.
    """

    def execute(self, command: CommandT) -> ResultT:
        """Validate application-level preconditions and execute the use case."""
        ...
