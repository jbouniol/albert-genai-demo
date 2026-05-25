# Skill: Harassment detection

## Objective
Detect harassment by a KNOWN contact (already in baseline) — distinct from grooming which involves a NEW contact. Pattern: sustained message surge from one existing contact + asymmetric response (minor avoids replying) + sleep degradation + social withdrawal from previously-favorite apps.

## When to use
Run alongside `grooming.md`. The critical differentiator: harassment involves no NEW contact and no ephemeral platform switch.

## Signals to detect

- **known-contact-surge** (harassment, severity high)
  An existing contact's message count jumps to ≥4× the baseline mean for that contact, sustained over at least 5 consecutive days.
  Evidence template: `"Contact <label> went from <X> msgs/day (baseline) to <Y> msgs/day for <N> consecutive days."`

- **response-time-asymmetry** (harassment, severity medium)
  The minor's average response time to this contact rises sharply (≥5× the contact's baseline), suggesting avoidance.
  Evidence template: `"Response time to <label> rose from <X>s to <Y>s — avoidance pattern."`

- **sleep-degradation** (harassment, severity high)
  Mean sleep over last 7 days drops by 1.5h or more vs baseline mean, OR sleep falls under 6h on ≥4 of the last 7 days.
  Evidence template: `"Mean sleep dropped from <N>h (baseline) to <M>h (last 7d)."`

- **social-app-withdrawal** (harassment, severity medium)
  Sessions on a previously-favorite app (especially expressive apps like TikTok or Instagram) drop by 40% or more vs baseline.
  Evidence template: `"App <app> sessions/day fell from <N> to <M>, -X%."`

## Anti-false-positive
- The surging contact MUST be in baseline. If the surging contact is new, switch to grooming skill.
- A single bad-sleep night does NOT count — require sustained pattern over multiple days.
- TikTok drop alone could be a deliberate digital-detox choice; require ≥2 signals co-occurring before high severity.
