class WorkflowError(Exception):
    """Base exception for the Workflow Engine subsystem."""
    pass


class WorkflowValidationError(WorkflowError):
    """Raised when a WorkflowRequest is malformed."""
    pass


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow or task is not found."""
    pass


class TaskExecutionError(WorkflowError):
    """Raised when a task fails during execution."""
    pass


class WorkflowCancelledError(WorkflowError):
    """Raised when a workflow is cancelled."""
    pass
