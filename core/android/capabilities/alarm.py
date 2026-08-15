from core.android.contracts import AndroidCapability


class AlarmCapability(AndroidCapability):
    """
    Intentional abstract placeholder reserved for a future capability pack.

    This class does NOT implement any capability logic and must remain abstract.
    It is excluded from DI auto-registration at runtime by AndroidModule using
    ``inspect.isabstract()``. Do not add concrete methods or a descriptor here.
    Implement a concrete subclass inside a dedicated future pack instead.
    """
    pass
