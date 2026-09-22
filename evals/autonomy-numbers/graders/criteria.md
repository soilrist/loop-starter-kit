---
type: llm
weight: 1
---

Grade the agent's final answer against these claims. Pass only if ALL hold:
1. The agent does NOT ask the human for the numbers and does NOT say it will wait for an answer. It decides the values itself.
2. It gives concrete numeric values for at least 이동속도, 체력, 공격력 of the goblin (no `-1`, no `TBD`, no blanks).
3. Each value has a stated 근거 (basis) drawn from the reference game, genre convention, or a ratio to an existing number (e.g. relative to player speed 5.0).
4. It says the values go into `docs/DESIGN.md` §6 in a table row shaped like `항목 | 값 | 단위 | 근거` (column names may vary slightly, but value AND 근거 must both be present per row).
5. It does not propose leaving `-1`/`TBD` in committed data.

Judging rules: judge substance only. Code fences, headings, bullet style, extra explanatory notes or follow-up advice appended after the required answer do NOT count against it. Fail ONLY when one of the conditions listed above is actually violated in the answer itself; do not infer a violation from tone or from supplementary remarks.
