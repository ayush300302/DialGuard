"""Borrower domain model."""

from dataclasses import dataclass


@dataclass
class Borrower:
    """Represents a borrower to be contacted by collections operations."""

    id: str
    phone_number: str = ""
    name: str = ""
