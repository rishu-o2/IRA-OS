from typing import List

from core.logging import Logger
from .contracts import ConfirmationProvider
from .exceptions import MutationError
from .models import ConfirmationLevel, MutationContext


class ConfirmationManager:
    """
    Coordinates requesting confirmation from pluggable ConfirmationProviders.
    """

    def __init__(self, logger: Logger) -> None:
        self._providers: List[ConfirmationProvider] = []
        self._logger = logger

    def register_provider(self, provider: ConfirmationProvider) -> None:
        """Register a new confirmation provider."""
        self._providers.append(provider)

    async def request_confirmation(self, context: MutationContext, level: ConfirmationLevel) -> bool:
        """
        Find a provider that supports the requested level and ask for confirmation.
        """
        if level == ConfirmationLevel.NONE:
            return True

        for provider in self._providers:
            if provider.supports(level):
                try:
                    return await provider.request_confirmation(context, level)
                except Exception as e:
                    self._logger.error(
                        "ConfirmationProvider raised an error.", 
                        provider=type(provider).__name__, 
                        error=str(e)
                    )
                    return False
        
        # If no provider can handle the level, we fail closed (secure by default).
        self._logger.warning(
            "No ConfirmationProvider found for requested level. Denying mutation.",
            level=level.value,
        )
        return False
