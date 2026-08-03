import threading
from typing import Dict, List, Optional
from .session import Session
from .exceptions import SessionRegistrationError


class SessionRegistry:
    """
    Pure in-memory, thread-safe registry for active sessions.
    """
    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: Dict[str, Session] = {}

    def register(self, session: Session) -> None:
        with self._lock:
            if session.session_id in self._sessions:
                raise SessionRegistrationError(f"Session '{session.session_id}' already exists.")
            self._sessions[session.session_id] = session

    def remove(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def get(self, session_id: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_by_identity(self, identity_id: str) -> List[Session]:
        with self._lock:
            return [s for s in self._sessions.values() if s.identity_id == identity_id]

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
