# Design decisions

Short notes on choices that changed during real use.

**One calendar event per day, not one reminder per contact.**
The first version created a calendar reminder for every follow-up. With a few dozen contacts that meant dozens of events to create, move and delete as plans changed, and they drifted out of sync with the database. Now the database holds every date (`Next Action`, the formula-driven `Follow-up Date`) and a single morning job reads it and writes one event.

**Plain text everywhere it leaves the database.**
Calendar apps render event descriptions literally, so `<br>` and `&amp;` showed up as raw characters. The brief is plain text with real line breaks, and a test enforces it.

**Notes are append-only, dated lines.**
An earlier version had a separate "Interactions" table. In practice nobody opened it, so the history moved into the contact's own Notes field, one `YYYY-MM-DD: what happened` line per event. Lines are never rewritten, so the history stays trustworthy.

**A connection request is not a touch.**
Setting `Last Reach Out` on a request started the 3-day chase for people who hadn't even accepted. Requests now have their own status and their own 14-day clock.

**One follow-up, then a decision.**
Unlimited chasing feels productive and burns goodwill. After one follow-up the only options are "Died" or "keep waiting", and a human makes that call.

**The human sends everything.**
The assistant drafts and logs; it never sends a message, email or invite. Every write to the database is shown as a draft first and applied after an explicit "proceed".

**Affiliation means the person's own employer.**
A headhunter's client or a deal counterparty mentioned in passing goes into notes, never into the Affiliations tag. Otherwise filtering People by company becomes useless.

**Promotion is a hand-off, not a copy.**
When a contact reaches Done, the outreach row keeps its history and gains a link; the People page is created separately with its own template and keep-warm frequency.
