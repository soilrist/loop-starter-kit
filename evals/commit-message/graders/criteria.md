---
type: llm
weight: 1
---

Pass only if ALL hold (reference: docs/conventions/GitCommit.md):
1. Subject line is Conventional-Commit shaped with type `feat` and a scope in parentheses, e.g. `feat(combat): 3연타 콤보 추가` (type must be feat, not chore/docs).
2. Trailer `Loop: 128` is present exactly.
3. Trailer `Slice: M1-03` is present exactly.
4. Trailer `Checks:` is present and reports L1 pass, L2 pass, and L3 as skipped/not done (e.g. `L3 skip(editor off)` or 못 함). It must NOT claim L3 passed.
5. Nothing in the message claims a check passed that was not run.

Judging rules: judge substance only. Code fences, headings, bullet style, extra explanatory notes or follow-up advice appended after the required answer do NOT count against it. Fail ONLY when one of the conditions listed above is actually violated in the answer itself; do not infer a violation from tone or from supplementary remarks.
