import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any
from contextvars import ContextVar

from core.config import IdentityConfig, ConfigurationManager
from core.events import EventBus
from .models import Identity, IdentityAuthenticated, IdentityLoggedOut
from .session import Session
from .session_registry import SessionRegistry
from .registry import IdentityRegistry
from .exceptions import AuthenticationError

_current_session: ContextVar[Optional[Session]] = ContextVar("_current_session", default=None)
_current_identity: ContextVar[Optional[Identity]] = ContextVar("_current_identity", default=None)


class AuthenticationManager:
    """
    Manages active sessions and authentication logic.
    Maintains current session context per-async-task via contextvars.
    """
    def __init__(
        self,
        identity_registry: IdentityRegistry,
        session_registry: SessionRegistry,
        config: ConfigurationManager,
        event_bus: Optional[Any] = None
    ):
        self._identity_registry = identity_registry
        self._session_registry = session_registry
        self._config = config
        self._event_bus = event_bus

    async def authenticate(self, identity: Identity, device_id: Optional[str] = None) -> Session:
        """
        Authenticates an identity and issues a session.
        Note: Does not perform password validation (delegated to future adapters).
        """
        if not identity.active:
            raise AuthenticationError(f"Identity '{identity.id}' is not active.")
            
        # Verify identity exists in registry
        if not self._identity_registry.exists(identity.id):
            raise AuthenticationError(f"Identity '{identity.id}' is not registered.")
            
        try:
            timeout_seconds = self._config.section(IdentityConfig).session_timeout
        except Exception:
            timeout_seconds = 86400  # Default fallback if config fails
            
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=timeout_seconds)
        
        session = Session(
            session_id=uuid.uuid4().hex,
            identity_id=identity.id,
            device_id=device_id,
            started_at=now,
            expires_at=expires_at,
            authenticated=True
        )
        
        self._session_registry.register(session)
        
        # Set context
        _current_session.set(session)
        _current_identity.set(identity)
        
        if self._event_bus:
            event = IdentityAuthenticated(
                payload={"identity_id": identity.id, "session_id": session.session_id},
                source="AuthenticationManager",
                identity_id=identity.id,
                session_id=session.session_id
            )
            await self._event_bus.publish(event)
            
        return session

    async def logout(self, session_id: Optional[str] = None) -> None:
        """Logs out the specified session or the current context session."""
        target_session_id = session_id
        if not target_session_id:
            curr = _current_session.get()
            if curr:
                target_session_id = curr.session_id
                
        if target_session_id:
            session = self._session_registry.get(target_session_id)
            if session:
                self._session_registry.remove(target_session_id)
                
                # Clear context if we are logging out the current context
                curr_ctx = _current_session.get()
                if curr_ctx and curr_ctx.session_id == target_session_id:
                    _current_session.set(None)
                    _current_identity.set(None)
                    
                if self._event_bus:
                    event = IdentityLoggedOut(
                        payload={"identity_id": session.identity_id, "session_id": target_session_id},
                        source="AuthenticationManager",
                        identity_id=session.identity_id,
                        session_id=target_session_id
                    )
                    await self._event_bus.publish(event)

    def current_identity(self) -> Optional[Identity]:
        """Gets the authenticated identity for the current async task context."""
        return _current_identity.get()

    def current_session(self) -> Optional[Session]:
        """Gets the session for the current async task context."""
        return _current_session.get()

    def set_context(self, session: Optional[Session], identity: Optional[Identity]) -> None:
        """Manually overrides the current context. Useful for middlewares."""
        _current_session.set(session)
        _current_identity.set(identity)

    def active_sessions(self, identity_id: str) -> List[Session]:
        """Returns all active sessions for a given identity."""
        # Clean up expired sessions first (lazy cleanup)
        sessions = self._session_registry.list_by_identity(identity_id)
        now = datetime.now(timezone.utc)
        active = []
        for s in sessions:
            if s.expires_at and s.expires_at < now:
                self._session_registry.remove(s.session_id)
            else:
                active.append(s)
        return active
