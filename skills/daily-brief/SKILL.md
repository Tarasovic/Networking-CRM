---
name: daily-brief
description: Scheduled task prompt. Every morning, read the outreach databases and put one plain-text calendar event on today's calendar listing who to chase, what's due and who's up next. Read-only; never sends anything.
---

# Daily networking brief (scheduled task prompt)

Runs every morning before the working day starts, in the user's time zone. Each run starts fresh, so this prompt is complete on its own.

## Hard rules

- **Read Notion only.** Never send a message, email or invite. Never write to Notion.
- Create **one** 15-minute calendar event today at the user's chosen time (or the next quarter hour if later). No attendees. If an event from an earlier run today exists, update it instead of duplicating.
- **Nothing due and no hygiene findings → no event.** Silence is the signal.
- If Notion can't be read, create a "Networking: brief incomplete" event saying what failed.

## What to collect

Use the funnel rules in `docs/funnel-rules.md`:

1. **Chase:** Pending Response and `Last Reach Out + 3 <= today`. Label "follow-up due", or "Died check" if Follow-up Sent is ticked. Overdue first.
2. **Due dates:** open contacts whose Next Action has arrived (agreed dates, recruiter check-ins, move-on dates in strict sequences).
3. **Applications** (live system only; not in the demo code): an application in "to do" has an apply-by date; a submitted application has an assessment deadline. Skip rejected, closed or completed ones.
4. **Up next:** per target, the current sequence number, unless someone at that number is waiting or a condition isn't met.
5. **Pending requests:** connection requests older than 14 days.
6. **Keep-warm:** People whose next check-in is within 7 days.
7. **Mondays only:** a hygiene block covering targets with no open contacts, contacts missing a sequence number, and contacts gated on a contact that doesn't exist.

At most 10 items in full; list the rest as `+N more <section>: names`.

## Event format

**Title:** `Networking: <counts>`, e.g. `Networking: 2 follow-ups, 1 up next`.

**Description: plain text only.** Calendar apps show HTML literally, so use real line breaks and no tags or entities. Layout:

```
Daily networking brief · Mon 02 Mar 2026

CHASE

1. <Name> · <Company / Team>
Why: <one line>
Do: <one line>
Draft: "<short message in the user's voice>"
<link to the Notion row>

...
Nothing in: <empty sections>.
Nothing sent or written to Notion.
```

**Drafts:** tight and specific, built only from facts in Notion. Never invent a detail such as an office location or a shared connection; if one is needed, write the draft to ask for it.

## After posting

End the session message with: "Tell me what you sent (e.g. 'sent 1, 2') and I'll log it."
