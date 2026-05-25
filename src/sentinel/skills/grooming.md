# Skill: Grooming detection

## Objective
Detect grooming patterns from metadata ONLY (no message content — privacy by design). Grooming is the COMBINATION of: new external contact + escalating frequency + nocturnal drift + platform shift toward ephemeral + isolation from baseline friends. A single signal in isolation is low confidence.

## When to use
Always run this skill on any window. It is the highest-priority risk pattern. Always cross-check against the `normal_life_event` skill — a new school friend can superficially trigger one of these signals.

## Signals to detect

- **new-contact-escalation** (grooming, severity medium)
  A contact absent in baseline (days 0-13) appears, and the message count to that contact multiplies at least 3× between first-appearance week and last 7 days.
  Evidence template: `"Contact <label> absent before day X; <N> msgs/day in last 7d vs <M> in first observation week."`

- **nocturnal-drift** (grooming, severity high)
  Conversations with a specific contact shift over the window into late-night hours (22h-3h).
  Evidence template: `"Conversations with <label> moved from <early hours> to <late hours>."`

- **ephemeral-platform-switch** (grooming, severity high)
  A contact migrates from a persistent platform (Discord, Instagram, iMessage) to an ephemeral one (Snapchat). Ephemerality reduces parental observability.
  Evidence template: `"Contact <label> shifted from <app1> to <app2> at day X."`

- **isolation-from-baseline-friends** (grooming, severity medium)
  Aggregate interactions with baseline friends drop by 40% or more while a single new contact captures attention.
  Evidence template: `"Baseline friends went from <N> msgs (first 7d) to <M> msgs (last 7d), -X%."`

- **high-engagement-asymmetry** (grooming, severity low)
  Average response time to a new contact stays under ~180 seconds sustained over days (high dependency signal).
  Evidence template: `"Mean response time to <label> = <N> seconds."`

## Anti-false-positive
A new friend from school or sport produces ONLY new-contact-escalation, typically alone. Grooming requires AT LEAST 3 of the above signals co-occurring AND involving the SAME new contact. If only 1-2 signals fire, set severity low.
