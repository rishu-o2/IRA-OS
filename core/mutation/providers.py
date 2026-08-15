from .contracts import ConfirmationProvider
from .models import ConfirmationLevel

class DenyByDefaultProvider(ConfirmationProvider):
    """
    A fail-safe confirmation provider that denies all requests.
    Used as the default provider when no active user-facing provider is registered.
    """
    def supports(self, level: ConfirmationLevel) -> bool:
        # We catch everything that isn't NONE (NONE doesn't reach providers)
        return True

    async def request_confirmation(self, context, level: ConfirmationLevel) -> bool:
        return False
