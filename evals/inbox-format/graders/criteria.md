---
type: llm
weight: 1
---

Pass only if ALL hold (reference: docs/conventions/InboxFormat.md):
1. The INBOX line starts with `- [ ] 지시(` (kind must be 지시, not 결함/질문/확인).
2. Inside the parentheses the author is written as 감독←형 (or equivalent showing 감독 relaying 형) followed by the date-time `2026-09-22 14:05`.
3. There is a bold one-line 요지 like **고블린 이동속도 3.5로.** and the body names `SO_Enemy_Goblin` / `m_MoveSpeed` = 3.5.
4. The line contains a `검증:` part and a `삭제:` part.
5. The commit is scoped to the INBOX file only: `git add docs/feedback/INBOX.md` (NOT `git add -A` / `git add .`) and the commit message starts with `docs(inbox):`.
6. The agent does NOT ask the human to confirm the number (3.5 was given by the human).

Judging rules: judge substance only. Code fences, headings, bullet style, extra explanatory notes or follow-up advice appended after the required answer do NOT count against it. Fail ONLY when one of the conditions listed above is actually violated in the answer itself; do not infer a violation from tone or from supplementary remarks.
