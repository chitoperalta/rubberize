"""Custom exceptions for the library."""


class RubberizeError(Exception):
    """Base class for all rubberize exceptions."""


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


class RubberizeKeywordError(RubberizeError, KeyError):
    """This error is raised when the user uses an unknown mapping key."""
