from datetime import date
from pathlib import Path

import pytest

from crm import brief, rules
from crm.models import Contact, Person, Priority, Seniority, Status, Target
from crm.store import load_json, save_json

D = date(2026, 3, 2)  # a Monday
SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample.json"


def mk(id, status, seq=1, **kw):
    return Contact(id=id, name=id.title(), seniority=Seniority.ANALYST, status=status,
                   target_id="t", sequence=seq, **kw)


# ---- chase -----------------------------------------------------------

def test_follow_up_due_exactly_three_days_after_last_touch():
    c = mk("a", Status.PENDING_RESPONSE, last_reach_out=date(2026, 2, 27))
    assert rules.follow_up_date(c) == date(2026, 3, 2)
    [item] = rules.chase([c], D)
    assert item.kind == "follow-up" and item.overdue_days == 0


def test_not_due_before_three_days():
    c = mk("a", Status.PENDING_RESPONSE, last_reach_out=date(2026, 2, 28))
    assert rules.chase([c], D) == []


def test_after_follow_up_it_becomes_a_died_check():
    c = mk("a", Status.PENDING_RESPONSE, last_reach_out=date(2026, 2, 27), follow_up_sent=True)
    assert rules.chase([c], D)[0].kind == "died-check"


def test_connection_request_never_starts_the_chase_clock():
    c = mk("a", Status.PENDING_REACH_OUT)
    rules.log_touch(c, "request_sent", date(2026, 2, 1))
    assert c.last_reach_out is None and c.status is Status.PENDING_CONNECTION
    assert rules.chase([c], D) == []


def test_only_one_follow_up_allowed():
    c = mk("a", Status.PENDING_RESPONSE, last_reach_out=date(2026, 2, 20))
    rules.log_touch(c, "follow_up_sent", date(2026, 2, 23))
    with pytest.raises(ValueError):
        rules.log_touch(c, "follow_up_sent", date(2026, 2, 26))


# ---- sequencing ------------------------------------------------------

def test_waiting_contact_blocks_the_rest_of_the_target():
    a = mk("a", Status.PENDING_CONNECTION, 1)
    b = mk("b", Status.PENDING_REACH_OUT, 2)
    assert rules.up_next([a, b], D) == []


def test_equal_numbers_run_in_parallel():
    a = mk("a", Status.PENDING_REACH_OUT, 1)
    b = mk("b", Status.SEND_THE_MESSAGE, 1)
    assert {c.id for c in rules.up_next([a, b], D)} == {"a", "b"}


def test_closed_contacts_open_the_next_number():
    a = mk("a", Status.DIED, 1)
    b = mk("b", Status.PENDING_REACH_OUT, 2)
    assert rules.up_next([a, b], D) == [b]


def test_gated_contact_waits_for_its_condition():
    a = mk("a", Status.DIED, 1)
    b = mk("b", Status.PENDING_REACH_OUT, 2, after="a")
    assert rules.up_next([a, b], D) == []  # 'a' died rather than reaching Done
    a.status = Status.DONE
    assert rules.up_next([a, b], D) == [b]


def test_future_agreed_date_pauses_the_target():
    a = mk("a", Status.PENDING_REACH_OUT, 1, next_action=date(2026, 3, 9))
    assert rules.up_next([a], D) == []


def test_move_on_schedules_the_next_person_two_days_later():
    a, b, c = mk("a", Status.PENDING_CONNECTION, 1), mk("b", Status.PENDING_REACH_OUT, 2), mk("c", Status.PENDING_REACH_OUT, 3)
    nxt = rules.schedule_move_on([a, b, c], a, date(2026, 3, 2))
    assert nxt is b and b.next_action == date(2026, 3, 4) and c.next_action is None


# ---- requests, dates, keep-warm --------------------------------------

def test_requests_go_stale_after_fourteen_days():
    fresh = mk("a", Status.PENDING_CONNECTION, request_sent=date(2026, 2, 16))
    stale = mk("b", Status.PENDING_CONNECTION, request_sent=date(2026, 2, 15))
    assert rules.stale_requests([fresh, stale], D) == [stale]


def test_due_dates_ignore_closed_contacts():
    a = mk("a", Status.PENDING_REACH_OUT, next_action=D)
    b = mk("b", Status.DONE, next_action=D)
    assert rules.due_dates([a, b], D) == [a]


def test_keep_warm_window_and_opt_out():
    near = Person("p1", "Near", "X", date(2025, 12, 5), 3)  # due 2026-03-05, within a week
    far = Person("p2", "Far", "X", date(2026, 1, 15), 3)  # due 2026-04-15
    never = Person("p3", "Never", "X", date(2020, 1, 1), 999)
    assert [p.id for p, _ in rules.keep_warm([near, far, never], D)] == ["p1"]


def test_add_months_clamps_month_end():
    assert rules.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)


# ---- notes & brief ---------------------------------------------------

def test_notes_are_append_only():
    c = mk("a", Status.PENDING_REACH_OUT)
    rules.log_touch(c, "message_sent", date(2026, 3, 1), "first message")
    rules.log_touch(c, "call_held", date(2026, 3, 5), "call held")
    assert [n.text for n in c.notes] == ["first message", "call held"]


def test_empty_day_creates_no_event():
    t = Target("t", "Co", "Team", Priority.HIGH)
    assert brief.render([t], [mk("a", Status.DONE)], [], date(2026, 3, 3)) is None


def test_brief_caps_items_and_reports_overflow():
    t = Target("t", "Co", "Team", Priority.HIGH)
    cs = [mk(f"c{i}", Status.PENDING_RESPONSE, i, last_reach_out=date(2026, 2, 1)) for i in range(12)]
    text = brief.render([t], cs, [], D)
    assert "10. " in text and "11. " not in text
    assert "+2 more chase" in text


def test_brief_is_plain_text():
    targets, contacts, people = load_json(SAMPLE)
    text = brief.render(targets, contacts, people, D)
    assert "<" not in text and "&amp;" not in text


def test_sample_round_trips(tmp_path):
    targets, contacts, people = load_json(SAMPLE)
    out = tmp_path / "copy.json"
    save_json(out, targets, contacts, people)
    t2, c2, p2 = load_json(out)
    assert [c.name for c in c2] == [c.name for c in contacts] and len(t2) == len(targets) and len(p2) == len(people)


# ---- regressions from review -------------------------------------------

def test_acting_on_a_contact_clears_its_agreed_date():
    c = mk("a", Status.PENDING_REACH_OUT, next_action=D)
    rules.log_touch(c, "request_sent", D)
    assert c.next_action is None and rules.due_dates([c], date(2026, 3, 20)) == []


def test_new_message_resets_the_single_follow_up():
    c = mk("a", Status.PENDING_RESPONSE, last_reach_out=date(2026, 2, 1), follow_up_sent=True)
    rules.log_touch(c, "replied_later", date(2026, 2, 5), next_action=date(2026, 2, 20))
    rules.log_touch(c, "message_sent", date(2026, 2, 20))
    assert c.follow_up_sent is False
    assert rules.chase([c], date(2026, 2, 23))[0].kind == "follow-up"


def test_closed_contacts_reject_new_events():
    c = mk("a", Status.DIED)
    with pytest.raises(ValueError):
        rules.log_touch(c, "message_sent", D)


def test_dangling_gate_is_flagged():
    b = mk("b", Status.PENDING_REACH_OUT, 2, after="ghost")
    assert rules.up_next([b], D) == [] and rules.broken_gates([b]) == [b]


def test_accepting_cancels_the_move_on_date():
    a, b = mk("a", Status.PENDING_REACH_OUT, 1), mk("b", Status.PENDING_REACH_OUT, 2)
    rules.log_touch(a, "request_sent", D)
    rules.schedule_move_on([a, b], a, D)
    assert b.next_action == date(2026, 3, 4)
    rules.log_touch(a, "accepted", date(2026, 3, 3))
    rules.cancel_move_on([a, b], a, date(2026, 3, 3))
    assert b.next_action is None


def test_promotion_requires_done_and_links_both_sides():
    people = []
    c = mk("a", Status.PENDING_RESPONSE)
    with pytest.raises(ValueError):
        rules.promote(c, people, D, "p9", "X", 3)
    c.status = Status.DONE
    p = rules.promote(c, people, D, "p9", "X", 3)
    assert people == [p] and "promoted to People (p9)" in c.notes[-1].text


def test_sections_always_print_in_fixed_order():
    t = Target("t", "Co", "Team", Priority.HIGH)
    died = mk("a", Status.PENDING_RESPONSE, 1, last_reach_out=date(2026, 2, 1), follow_up_sent=True)
    fresh = mk("b", Status.PENDING_RESPONSE, 2, last_reach_out=date(2026, 2, 26))
    text = brief.render([t], [died, fresh], [], D)
    assert text.index("CHASE") < text.index("DIED CHECKS")
    assert text.count("\nCHASE\n") == 1


def test_accepting_never_wipes_a_genuinely_agreed_date():
    a = mk("a", Status.PENDING_CONNECTION, 1, request_sent=D)
    b = mk("b", Status.PENDING_REACH_OUT, 2, next_action=date(2026, 3, 20))
    rules.log_touch(a, "accepted", date(2026, 3, 3))
    assert rules.cancel_move_on([a, b], a, date(2026, 3, 3)) is None
    assert b.next_action == date(2026, 3, 20)


def test_closed_rows_stay_closed_except_late_call():
    done = mk("a", Status.DONE)
    with pytest.raises(ValueError):
        rules.log_touch(done, "died", D)
    died = mk("b", Status.DIED)
    rules.log_touch(died, "call_held", D)
    assert died.status is Status.DONE


def test_promotion_is_not_duplicated():
    people = []
    c = mk("a", Status.DONE)
    rules.promote(c, people, D, "p1", "X")
    with pytest.raises(ValueError):
        rules.promote(c, people, D, "p2", "X")
    c2 = mk("b", Status.DONE)
    with pytest.raises(ValueError):
        rules.promote(c2, people, D, "p1", "X")
