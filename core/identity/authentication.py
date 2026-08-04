import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any, Tuple
from contextvars import ContextVar, Token

from core.config import IdentityConfig, ConfigurationManager
from core.events import EventBus
from .models import Identity, IdentityAuthenticated, IdentityLoggedOut
from .session import Session
from .session_registry import SessionRegistry
from .registry import IdentityRegistry
from .exceptions import AuthenticationError, SessionExpiredError

_current_session: ContextVar[Optional[Session]] = ContextVar("_current_session", default=None)
_current_identity: ContextVar[Optional[Identity]] = ContextVar("_current_identity", default=None)
_context_stack: ContextVar[Tuple[Tuple[Optional[str], Optional[Session], Optional[Identity], Token, Token], ...]] = ContextVar("_auth_context_stack", default=())


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

        if timeout_seconds <= 0:
            raise SessionExpiredError("Session timeout is not positive.")
            
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

        if self._is_expired(session):
            self._session_registry.remove(session.session_id)
            raise SessionExpiredError(f"Session '{session.session_id}' has expired before authentication completed.")
        
        self._push_context(session, identity)
        
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
            if session and self._is_expired(session):
                self._session_registry.remove(target_session_id)
                self._restore_context_for_session(target_session_id)
                raise SessionExpiredError(f"Session '{target_session_id}' has expired.")

            if session:
                self._session_registry.remove(target_session_id)
                self._restore_context_for_session(target_session_id)
                
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
        session = self.current_session()
        if session is None:
            return None
        return _current_identity.get()

    def current_session(self) -> Optional[Session]:
        """Gets the session for the current async task context."""
        session = _current_session.get()
        if not session:
            return None
        if self._is_expired(session):
            self._session_registry.remove(session.session_id)
            self._restore_context_for_session(session.session_id)
            return None
        return session

    def set_context(self, session: Optional[Session], identity: Optional[Identity]) -> None:
        """Manually overrides the current context. Useful for middlewares."""
        if session is None and identity is None:
            self._restore_context_for_session(None)
            return
        self._push_context(session, identity) if session is not None and identity is not None else None

    def active_sessions(self, identity_id: str) -> List[Session]:
        """Returns all active sessions for a given identity."""
        sessions = self._session_registry.list_by_identity(identity_id)
        active = []
        for s in sessions:
            if self._is_expired(s):
                self._session_registry.remove(s.session_id)
            else:
                active.append(s)
        return active

    def _push_context(self, session: Session, identity: Identity) -> None:
        prev_session = _current_session.get()
        prev_identity = _current_identity.get()
        session_token = _current_session.set(session)
        identity_token = _current_identity.set(identity)
        frames = list(_context_stack.get())
        frames.append((session.session_id, prev_session, prev_identity, session_token, identity_token))
        _context_stack.set(tuple(frames))

    def _restore_context_for_session(self, session_id: Optional[str]) -> bool:
        frames = list(_context_stack.get())
        for index in range(len(frames) - 1, -1, -1):
            frame = frames[index]
            if frame[0] != session_id:
                continue
            if index == len(frames) - 1:
                _, _, _, session_token, identity_token = frame
                _current_session.reset(session_token)
                _current_identity.reset(identity_token)
            frames.pop(index)
            _context_stack.set(tuple(frames))
            return True
        return False

    def _is_expired(self, session: Optional[Session]) -> bool:
        if not session:
            return False
        if session.expires_at is None:
            return False
        return datetime.now(timezone.utc) >= session.expires_at
