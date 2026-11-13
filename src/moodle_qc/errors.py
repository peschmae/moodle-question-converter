"""Errors shown to the user as a message, without a traceback."""


class UserError(Exception):
    """A problem the user can fix (missing collection config, invalid file, …)."""
