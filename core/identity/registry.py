import threading
from typing import Dict, List, Optional
from .models import Identity
from .exceptions import IdentityRegistrationError


class IdentityRegistry:
    """
    Pure in-memory, thread-safe registry for identities.
    Provides O(1) lookups by ID and username.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._by_id: Dict[str, Identity] = {}
        self._by_username: Dict[str, Identity] = {}

    def register(self, identity: Identity) -> None:
        """Register a new identity. Raises IdentityRegistrationError if duplicate ID or username."""
        with self._lock:
            if identity.id in self._by_id:
                raise IdentityRegistrationError(f"Identity with ID '{identity.id}' already exists.")
            if identity.username in self._by_username:
                raise IdentityRegistrationError(f"Identity with username '{identity.username}' already exists.")
            
            self._by_id[identity.id] = identity
            self._by_username[identity.username] = identity

    def remove(self, identity_id: str) -> None:
        """Removes an identity by ID. Idempotent."""
        with self._lock:
            identity = self._by_id.pop(identity_id, None)
            if identity:
                self._by_username.pop(identity.username, None)

    def replace(self, identity: Identity) -> None:
        """Replaces an existing identity."""
        with self._lock:
            existing = self._by_id.get(identity.id)
            if not existing:
                raise IdentityRegistrationError(f"Identity with ID '{identity.id}' does not exist to replace.")
            
            # If username changed, ensure the new username isn't taken by someone else
            if existing.username != identity.username:
                if identity.username in self._by_username:
                    raise IdentityRegistrationError(f"Username '{identity.username}' is already taken.")
                self._by_username.pop(existing.username, None)
            
            self._by_id[identity.id] = identity
            self._by_username[identity.username] = identity

    def get(self, identity_id: str) -> Optional[Identity]:
        """Get an identity by ID."""
        with self._lock:
            return self._by_id.get(identity_id)
            
    def get_by_username(self, username: str) -> Optional[Identity]:
        """Get an identity by username."""
        with self._lock:
            return self._by_username.get(username)

    def exists(self, identity_id: str) -> bool:
        """Check if an identity exists by ID."""
        with self._lock:
            return identity_id in self._by_id

    def list(self) -> List[Identity]:
        """Returns all registered identities."""
        with self._lock:
            return list(self._by_id.values())

    def clear(self) -> None:
        """Clears all registrations."""
        with self._lock:
            self._by_id.clear()
            self._by_username.clear()
