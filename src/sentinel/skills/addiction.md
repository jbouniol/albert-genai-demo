# Skill: Addiction / compulsive use detection

## Objective
Detect compulsive screen use that disrupts sleep and crowds out other behaviors — distinct from grooming and harassment (which are contact-driven). Pattern: sustained high screen time + sleep deprivation + repetitive sessions + saturated nighttime activity, with NO external trigger (no surging contact, no new threat).

## When to use
Run on every window. Especially important when sleep is degraded but contact patterns look benign.

## Signals to detect

- **screen-time-explosion** (addiction, severity high)
  Mean total screen time over the last 7 days exceeds baseline mean by 50% or more, sustained across the FULL week (not a single spike).
  Evidence template: `"Mean screen time went from <N> min/day (baseline) to <M> min/day (last 7d), +X%."`

- **chronic-sleep-deprivation** (addiction, severity high)
  Sleep hours under 6h on at least 5 of the last 7 days.
  Evidence template: `"Sleep under 6h on <N> of last 7 days."`

- **session-fragmentation** (addiction, severity medium)
  A single app exceeds 20 sessions/day on at least 4 days — indicates compulsive check-ins, not focused use.
  Evidence template: `"App <app> exceeded 20 sessions/day on <N> days, peak <X> on day <Y>."`

- **nighttime-saturation** (addiction, severity medium)
  Mean nighttime activity (22h-6h) of 60 min/day or more over the last 7 days.
  Evidence template: `"Mean nighttime activity (last 7d) = <N> min/day."`

## Anti-false-positive
- A short spike (1-3 days) tied to exams or a new game release is NOT addiction — require ≥5 of 7 days sustained.
- If there is a surging external contact, prefer harassment/grooming explanations first.
- Holiday/weekend periods can produce screen-time explosions; check the date context.
