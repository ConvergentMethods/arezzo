"""Arezzo error hierarchy.

The compiler is a correctness guarantee. If it emits a request, that request
MUST be valid. If there is any doubt, raise one of these errors. Partial
correctness is total failure.
"""


class ArezzoCompileError(Exception):
    """Base class for all Arezzo compilation errors."""


class ArezzoAddressError(ArezzoCompileError):
    """Raised when an address cannot be resolved or is ambiguous.

    Includes: heading not found, multiple heading matches, named range
    not found, bookmark not found, index out of bounds.
    """


class ArezzoOperationError(ArezzoCompileError):
    """Raised when an operation type is invalid or its parameters are wrong.

    Includes: unknown operation type, missing required params, invalid
    param values, operation not applicable to target element.
    """


class ArezzoIndexError(ArezzoCompileError):
    """Raised when UTF-16 index arithmetic produces an invalid result.

    Includes: index in surrogate pair boundary, index past document end,
    index inside structural element marker, negative index.
    """
