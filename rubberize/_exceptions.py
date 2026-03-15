"""Custom exceptions for the library."""


class RubberizeError(Exception):
    """Base class for all rubberize exceptions."""


class RubberizeRuntimeError(RubberizeError):
    """This error is raised when there is a run-time error."""


class RubberizeNotImplementedError(RubberizeError):
    """This error is raised when the user attempts to use a feature that
    is currently not implemented (but may be implemented in the future).
    """


class RubberizeTypeError(RubberizeError, TypeError):
    """This error is raised when the user attempts to pass the wrong
    argument type.
    """


class RubberizeValueError(RubberizeError, ValueError):
    """This error is raised when the user attempts to pass the wrong
    argument value of correct type.
    """


class RubberizeSyntaxError(RubberizeError, SyntaxError):
    """This error is raised when the user uses a feature incorrectly, or
    attempts to use a feature that will not be implemented.
    """


class RubberizeAttributeError(RubberizeError, AttributeError):
    """This error is raised when the user uses an unknown attribute."""


class RubberizeKeyError(RubberizeError, KeyError):
    """This error is raised when the user uses an unknown mapping key."""


class RubberizeUserWarning(UserWarning):
    """Base warning for Rubberize user code."""
