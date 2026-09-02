"""Errors distinguishing MVP failure conditions from ordinary bugs.

Mirrors agents/researcher/CONTRACT.md's "Failure conditions" section —
each of these corresponds to a named condition there.
"""


class StructuralFailure(Exception):
    """A CONTRACT.md structural failure condition: a SCRIPT.md-cited claim
    ID has no file, or a claim's Classification is missing/invalid. Maps
    to a REJECT verdict per the Phase 5 implementation notes.
    """


class NoLoadableContent(Exception):
    """Nothing could be loaded at all (e.g. no research/claims files
    exist). Maps to "abort, no REVIEW.md written" per CONTRACT.md.
    """
