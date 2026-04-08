# Release: Smart Tasks (v2.4.0) — phased rollout 25%

## Summary
Smart Tasks replaces legacy Quick Shortcuts with a guided checklist experience, deeper reminders integration, and team-sharing templates.

## Success criteria (launch gates)
- Crash rate remains **≤ 0.12%** during rollout window
- API **p95 latency** does not regress more than **15%** vs pre-release baseline
- **Payment success rate** stays **≥ 98.5%**
- **Support ticket volume** not more than **1.4×** baseline for comparable cohorts

## Known risks
- Smart Tasks panel is a new native surface; prior beta showed rotation-related crashes on iOS.
- Heavier client polling may increase perceived latency under load.
- Migration messaging may confuse users who relied on Quick Shortcuts.

## Known issues (non-blocking)
- Help link from Smart Tasks may open wrong article ID on Android (fix scheduled v2.4.1).
