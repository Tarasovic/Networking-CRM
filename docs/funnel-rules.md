# Funnel rules

Each rule is implemented in `crm/rules.py` and covered by `tests/test_rules.py`.

## 1. Lifecycle of a contact

```
Pending Reach-Out ──request──> Pending LinkedIn Connection ──accepted──> Send the message!
        │                                                                      │
        └──────────────────────────message──────────────────────────────────> Pending Response
                                                                               │
                      ┌──── reply, "talk later" (Next Action = agreed date) ───┤
                      │                                                        │
               Pending Reach-Out                         3 days, no reply ──> follow-up (once)
                                                                               │
                                                         3 more days ──> Died check ──> Died
                                                                               │
                                                   call / coffee held ──> Done ──> promote to People?
```

## 2. The chase: 3 days, one follow-up

* `Follow-up Date = Last Reach Out + 3`. When it arrives and the status is *Pending Response*, the brief lists a **follow-up**.
* After the follow-up is ticked, the next due date is a **Died check**: mark Died, or keep waiting. There is never a second chase; asking for one triggers a prompt instead.
* A **connection request never sets Last Reach Out**. Otherwise a pending invite would trigger a "follow-up" to someone who can't see your messages yet.

## 3. Sequencing: who is up next

* Every contact at a target gets a `Sequence #`. The *current number* is the lowest one still open (not Done/Died).
* If anyone at the current number is waiting (request or reply), **nothing** is up next for that target. This stops you from spamming a team.
* Equal numbers run in parallel (e.g. three analysts at #1).
* Seniors are usually gated: `after = <contact>` means "only once that conversation has happened" (e.g. a VP after the analyst call).
* A reply like "busy until month-end" sets `Next Action` to the agreed date and pauses the target until then.

## 4. Move-on for strict sequences

For teams where you want one request out at a time: when #n's request is sent, #n+1 gets `Next Action = today + 2`. If #n accepts first, the date is simply cleared. The brief surfaces #n+1 on that date as "send the request if #n hasn't accepted".

## 5. Stale requests: 14 days

A connection request still pending after 14 days appears under *Pending requests* with three options: try email, move to the next person, or mark Died. The system never decides alone.

## 6. Keep-warm

People with a Reach Out Frequency get listed when `Last Contact + frequency` falls within the next 7 days. The suggested message is always a no-ask update.

## 7. Daily brief

* One run every morning; one 15-minute calendar event with the whole brief as plain text.
* Sections in order: Chase, Died checks, Due dates, Up next, Pending requests, Keep-warm. On **Mondays** a hygiene block flags targets with no open contacts, contacts missing a sequence number, and contacts gated on someone who doesn't exist (they would never open).
* At most 10 items in full; the rest are listed as `+N more <section>: names`.
* **Empty day: no event.** If nothing is due and there are no hygiene findings, no event is created.
* The brief only reads. Nothing is sent or written. Every message goes out manually, by the human.
