"""Data model for the outreach CRM.

Three tables, mirroring the Notion workspace the system was built in:

* ``Target``  - a company + team you want to break into (e.g. "Maersk / Corporate Development").
* ``Contact`` - one person at a target (or a standalone recruiter), with a funnel status.
* ``Person``  - a relationship worth keeping warm after the outreach funnel is done.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class Priority(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    TRIED_AND_DIED = "Tried and Died"  # every avenue exhausted; kept for the record


class Seniority(str, Enum):
    ANALYST = "Analyst"
    ASSOCIATE = "Associate"
    VP = "VP"
    DIRECTOR_MD = "Director/MD"
    HR_RECRUITER = "HR/Recruiter"


class Status(str, Enum):
    """Where a contact sits in the funnel.

    PENDING_REACH_OUT  -> queued, nothing sent yet
    SEND_THE_MESSAGE   -> a message is due now (e.g. they just accepted a request)
    PENDING_CONNECTION -> connection request sent, waiting for an accept
    PENDING_RESPONSE   -> message sent, waiting for a reply (the chase clock runs)
    DONE               -> call / coffee held, or the thread closed on a good note
    DIED               -> no reply after the one follow-up, or a dead end
    """

    PENDING_REACH_OUT = "Pending Reach-Out"
    SEND_THE_MESSAGE = "Send the message!"
    PENDING_CONNECTION = "Pending LinkedIn Connection"
    PENDING_RESPONSE = "Pending Response"
    DONE = "Done"
    DIED = "Died"


CLOSED = {Status.DONE, Status.DIED}
WAITING = {Status.PENDING_RESPONSE, Status.PENDING_CONNECTION}
READY = {Status.PENDING_REACH_OUT, Status.SEND_THE_MESSAGE}


@dataclass
class Note:
    """One append-only, dated line of contact history."""

    on: date
    text: str

    def render(self) -> str:
        return f"{self.on.isoformat()}: {self.text}"


@dataclass
class Target:
    id: str
    company: str
    team: str
    priority: Priority
    notes: str = ""

    @property
    def label(self) -> str:
        return f"{self.company} / {self.team}"


@dataclass
class Contact:
    id: str
    name: str
    seniority: Seniority
    status: Status
    target_id: Optional[str] = None  # None = standalone recruiter
    sequence: Optional[int] = None  # equal numbers run in parallel
    last_reach_out: Optional[date] = None
    follow_up_sent: bool = False
    next_action: Optional[date] = None  # an agreed date to act on
    request_sent: Optional[date] = None  # connection request date
    after: Optional[str] = None  # contact id that must be DONE first
    move_on_from: Optional[str] = None  # set when next_action is a move-on date
    notes: list[Note] = field(default_factory=list)

    def log(self, on: date, text: str) -> None:
        """Notes are append-only: history is never rewritten."""
        self.notes.append(Note(on, text))


@dataclass
class Person:
    """Keep-warm relationship (the 'People' table)."""

    id: str
    name: str
    affiliation: str
    last_contact: date
    frequency_months: Optional[int] = None  # None or >= 99 means "don't nudge"
    met: str = "In Person"
    notes: list[Note] = field(default_factory=list)
