---
type: llm
weight: 1
---

Pass only if ALL hold (reference: .claude/skills/kickoff/SKILL.md step 5 and docs/conventions/Autonomy.md):
1. Before the questions there is a short "지금 가정한 것" (current assumptions) summary of roughly 3–5 lines.
2. There are at most 5 questions.
3. Every question offers 2–4 options, marks a recommended option, and has a one-line note on what changes depending on the choice.
4. No question asks the human for a balance number (HP, speed, damage, drop rate, prices, timers). Numbers are stated as decided-by-loop with 근거 or deferred to a DESIGN §6 table, never asked.
5. The primary reference game is treated as fixed (쾅냥 서바이버) rather than asked again.

Judging rules: judge substance only. Code fences, headings, bullet style, extra explanatory notes or follow-up advice appended after the required answer do NOT count against it. Fail ONLY when one of the conditions listed above is actually violated in the answer itself; do not infer a violation from tone or from supplementary remarks.
