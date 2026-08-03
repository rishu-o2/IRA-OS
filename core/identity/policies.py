from typing import Set, Dict
from .roles import Role
from .permissions import Permission


class PermissionPolicy:
    """
    Base class for resolving permissions based on roles.
    Can be inherited by EnterprisePolicy, PluginPolicy, etc.
    """
    def permissions(self, role: Role) -> Set[Permission]:
        raise NotImplementedError()


class DefaultPermissionPolicy(PermissionPolicy):
    """
    The standard IRA OS mapping of roles to permissions.
    """
    def __init__(self):
        self._mapping: Dict[Role, Set[Permission]] = {
            Role.OWNER: set(Permission),  # Owner has all permissions
            Role.ADMIN: {
                Permission.READ_MEMORY, Permission.WRITE_MEMORY,
                Permission.OPEN_APPLICATION, Permission.READ_FILES,
                Permission.WRITE_FILES, Permission.NETWORK, Permission.SYSTEM
            },
            Role.ASSISTANT: {
                Permission.READ_MEMORY, Permission.WRITE_MEMORY,
                Permission.OPEN_APPLICATION, Permission.SEND_MESSAGE,
                Permission.VOICE_OUTPUT, Permission.NETWORK
            },
            Role.GUEST: {
                Permission.READ_MEMORY, Permission.OPEN_APPLICATION
            },
            Role.AUTOMATION: {
                Permission.READ_MEMORY, Permission.WRITE_MEMORY,
                Permission.CONTROL_DEVICE, Permission.READ_FILES,
                Permission.WRITE_FILES, Permission.NETWORK
            },
            Role.DEVELOPER: set(Permission)
        }

    def permissions(self, role: Role) -> Set[Permission]:
        return self._mapping.get(role, set())
