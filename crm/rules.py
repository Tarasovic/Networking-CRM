"""Funnel rules as plain, testable functions.

Every rule here was a real decision in the Notion system; docs/funnel-rules.md
explains the reasoning behind each one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Optional

from .models import CLOSED, READY, WAITING, Contact, Note, Person, Status

CHASE_DAYS = 3  # follow up 3 days after the last touch
STALE_REQUEST_DAYS = 14  # a connection request older than this needs a decision
DEFAULT_MOVE_ON_DAYS = 2  # in strict sequences, try the next person after 2 days
KEEP_WARM_WINDOW_DAYS = 7


# ---------------------------------------------------------------- chase ----

def follow_up_date(c: Contact) -> Optional[date]:
    """Mirrors the Notion formula column: Last Reach Out + 3 days."""
    return c.last_reach_out + timedelta(days=CHASE_DAYS) if c.last_reach_out else None


@dataclass
class ChaseItem:
    contact: Contact
    kind: str  # "follow-up" or "died-check"
    due: date
    overdue_days: int


def chase(contacts: Iterable[Contact], today: date) -> list[ChaseItem]:
    """Contacts waiting on a reply whose 3-day window has elapsed.

    One follow-up only: if it has already been sent, the next step is a
    'died check' (mark Died or keep waiting), never a second chase.
    """
    out = []
    for c in contacts:
        due = follow_up_date(c)
        if c.status is Status.PENDING_RESPONSE and due and due <= today:
            kind = "died-check" if c.follow_up_sent else "follow-up"
            out.append(ChaseItem(c, kind, due, (today - due).days))
    return sorted(out, key=lambda i: -i.overdue_days)


# -------------------------------------------------------------- up next ----

def current_number(contacts: Iterable[Contact]) -> Optional[int]:
    """Lowest sequence number still in play (not Done or Died)."""
    nums = [c.sequence for c in contacts if c.sequence is not None and c.status not in CLOSED]
    return min(nums) if nums else None


def up_next(target_contacts: list[Contact], today: Optional[date] = None) -> list[Contact]:
    """Who to message next for one target.

    * Only the current sequence number is eligible (equal numbers run in parallel).
    * If anyone at that number is still waiting (request or reply), nothing is up next.
    * A contact with a future agreed date (they replied "talk later") pauses the target.
    * A contact gated on someone else (``after``) waits until that person is Done.
    """
    n = current_number(target_contacts)
    if n is None:
        return []
    tier = [c for c in target_contacts if c.sequence == n and c.status not in CLOSED]
    if any(c.status in WAITING for c in tier):
        return []
    if today and any(c.next_action and c.next_action > today for c in tier):
        return []
    by_id = {c.id: c for c in target_contacts}

    def gate_met(c: Contact) -> bool:
        if c.after is None:
            return True
        ref = by_id.get(c.after)
        return ref is not None and ref.status is Status.DONE  # unknown ref -> flagged by hygiene

    return [c for c in tier if c.status in READY and gate_met(c)]


def broken_gates(contacts: Iterable[Contact]) -> list[Contact]:
    """Contacts gated on an id that doesn't exist at their target (would block forever)."""
    contacts = list(contacts)
    ids = {(c.target_id, c.id) for c in contacts}
    return [c for c in contacts if c.after and (c.target_id, c.after) not in ids and c.status not in CLOSED]


# ----------------------------------------------------- dates & requests ----

def due_dates(contacts: Iterable[Contact], today: date) -> list[Contact]:
    """Agreed dates (Next Action) that have arrived, for open contacts."""
    return sorted(
        (c for c in contacts if c.next_action and c.next_action <= today and c.status not in CLOSED),
        key=lambda c: c.next_action,
    )


def stale_requests(contacts: Iterable[Contact], today: date) -> list[Contact]:
    """Connection requests unanswered for more than 14 days (day 15 onwards): decide
    (email, move on, or Died)."""
    return [
        c for c in contacts
        if c.status is Status.PENDING_CONNECTION
        and c.request_sent
        and (today - c.request_sent).days > STALE_REQUEST_DAYS
    ]


def schedule_move_on(sequence: list[Contact], sent: Contact, on: date,
                     gap_days: int = DEFAULT_MOVE_ON_DAYS) -> Optional[Contact]:
    """Strict one-at-a-time sequences: after a request goes out, give the next
    person a Next Action date ``gap_days`` later. If the request is accepted
    first, the date is simply cleared."""
    nxt = _next_in_line(sequence, sent)
    if nxt is not None:
        nxt.next_action = on + timedelta(days=gap_days)
        nxt.move_on_from = sent.id
        nxt.log(on, f"send a connection request only if {sent.name} hasn't accepted within {gap_days} days")
    return nxt


def cancel_move_on(sequence: list[Contact], accepted: Contact, on: date) -> Optional[Contact]:
    """The earlier request was accepted in time: clear the next person's move-on date.

    Only dates created by ``schedule_move_on`` for this contact are touched; a
    genuinely agreed date on the next person is left alone."""
    for nxt in sequence:
        if nxt.move_on_from == accepted.id:
            nxt.next_action = None
            nxt.move_on_from = None
            nxt.log(on, f"move-on cancelled: {accepted.name} accepted")
            return nxt
    return None


def _next_in_line(sequence: list[Contact], ref: Contact) -> Optional[Contact]:
    later = sorted((c for c in sequence if c.sequence is not None and c.sequence > (ref.sequence or 0)
                    and c.status is Status.PENDING_REACH_OUT), key=lambda c: c.sequence)
    return later[0] if later else None


# ----------------------------------------------------------- promotion ----

def promote(c: Contact, people: list[Person], on: date, person_id: str, affiliation: str,
            frequency_months: Optional[int] = None, met: str = "In Person") -> Person:
    """Hand-off to the keep-warm table. The outreach row keeps its history and gains a pointer."""
    if c.status is not Status.DONE:
        raise ValueError("only contacts who reached Done are promoted")
    if any(p.id == person_id for p in people):
        raise ValueError(f"People already has an entry with id {person_id!r}")
    if any(n.text.startswith("promoted to People") for n in c.notes):
        raise ValueError(f"{c.name} was already promoted")
    p = Person(person_id, c.name, affiliation, on, frequency_months, met)
    p.notes.append(Note(on, "promoted from the outreach log"))
    people.append(p)
    c.log(on, f"promoted to People ({person_id})")
    return p


# ---------------------------------------------------------- keep-warm ----

def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    y, m = d.year + y, m + 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError(d)


def keep_warm(people: Iterable[Person], today: date) -> list[tuple[Person, date]]:
    """People whose next check-in (last contact + frequency) falls within a week."""
    out = []
    for p in people:
        if not p.frequency_months or p.frequency_months >= 99:
            continue
        nxt = add_months(p.last_contact, p.frequency_months)
        if nxt <= today + timedelta(days=KEEP_WARM_WINDOW_DAYS):
            out.append((p, nxt))
    return sorted(out, key=lambda t: t[1])


# ------------------------------------------------------- state machine ----

TRANSITIONS = {
    # event:            (new status,              sets last_reach_out?)
    "request_sent":     (Status.PENDING_CONNECTION, False),  # never start the chase clock
    "accepted":         (Status.SEND_THE_MESSAGE, False),
    "message_sent":     (Status.PENDING_RESPONSE, True),
    "follow_up_sent":   (Status.PENDING_RESPONSE, True),
    "replied_later":    (Status.PENDING_REACH_OUT, False),  # agreed date -> next_action
    "replied_now":      (Status.SEND_THE_MESSAGE, False),
    "call_held":        (Status.DONE, False),
    "died":             (Status.DIED, False),
}


def log_touch(c: Contact, event: str, on: date, note: str = "",
              next_action: Optional[date] = None) -> Contact:
    """Apply one funnel event and append a dated note."""
    if event not in TRANSITIONS:
        raise ValueError(f"unknown event {event!r}; expected one of {sorted(TRANSITIONS)}")
    if event == "follow_up_sent" and c.follow_up_sent:
        raise ValueError("one follow-up only: decide Died or keep waiting instead")
    # Closed rows stay closed. One exception: a late reply to a Died contact can
    # still end in a call, so call_held is allowed from Died.
    if c.status in CLOSED and not (c.status is Status.DIED and event == "call_held"):
        raise ValueError(f"{c.name} is {c.status.value}; reopen deliberately before logging {event!r}")
    status, sets_reach_out = TRANSITIONS[event]
    c.status = status
    if sets_reach_out:
        c.last_reach_out = on
    if event == "message_sent":
        c.follow_up_sent = False  # a new thread gets its own single follow-up
    if event == "follow_up_sent":
        c.follow_up_sent = True
    if event == "request_sent":
        c.request_sent = on
    # Acting on a contact fulfils any agreed date; only "replied_later" sets a new one.
    if event != "replied_later":
        c.next_action = None
        c.move_on_from = None
    if next_action:
        c.next_action = next_action
    c.log(on, note or event.replace("_", " "))
    return c
