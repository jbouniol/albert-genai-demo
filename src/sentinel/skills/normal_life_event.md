# Skill: Normal life event recognition (anti-false-positive)

## Objective
Prevent false positives by recognizing legitimate behavioral shifts that LOOK like risk patterns but are not. Examples: exam period, holiday, illness, a healthy new friendship, a new sport activity, a temporary family event.

## When to use
Always run AFTER the three risk skills (grooming/harassment/addiction). If the observed deltas can be explained by a normal life event AND no high-severity risk signal is firing, set `matches_normal_life_event=true` in the output.

## Step-by-step checks
1. Is the pattern CONTAINED in time — does behavior return to baseline within the window? → likely normal life event.
2. Is there NO new external contact, NO ephemeral platform switch, NO isolation from baseline friends? → unlikely to be grooming.
3. Is the screen-time spike paired with INCREASED sessions on study/group apps (Discord, group chats)? → likely exam period.
4. Is the sleep degradation ISOLATED (a few days) rather than sustained? → likely transient (party, exam stress, illness).

## Signals to detect

- **exam-period-pattern** (normal_life_event, severity low)
  Short (3-5 day) screen-time spike + slight sleep dip + slight uptick in study-friendly apps (Discord group chats) + RETURN to baseline AFTER.
  Evidence template: `"Screen time spike days X-Y matches exam-style pattern; baseline restored after day Z."`

- **new-healthy-friendship** (normal_life_event, severity low)
  A new contact appears with DAYTIME hours, on a NON-ephemeral app, and baseline friends are NOT isolated.
  Evidence template: `"New contact <label> on <app>, peak hours <N>h-<M>h, baseline friend interactions unchanged."`

- **contained-transient-spike** (normal_life_event, severity low)
  Sleep drop OR screen-time spike lasting ≤3 days then back to baseline.
  Evidence template: `"Transient deviation days X-Y, returned to baseline after."`

## How this affects the overall result
- If at least one `normal_life_event` signal is detected AND NO `grooming` or `harassment` signal of severity `high` is present → set `matches_normal_life_event=true`.
- If a `normal_life_event` signal AND a high-severity risk signal both fire → keep `matches_normal_life_event=false` (risk takes priority) but mention the ambiguity in `overall_observation`.
