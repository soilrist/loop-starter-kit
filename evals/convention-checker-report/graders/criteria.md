---
type: llm
weight: 1
---

Pass only if ALL hold (reference: docs/conventions/CodingStyle.md, docs/engines/unity.md):
1. The report has the four sections: 위반 (as a table), 확인 필요, 점검한 규칙, 못 본 규칙.
2. The 위반 table flags at least these: (a) `public float speed` — public field forbidden, must be `[SerializeField] private float m_Speed` (m_ prefix); (b) `private Transform target` — missing `m_` prefix; (c) the `TODO` comment — forbidden, belongs in INBOX/ROADMAP; (d) `GameObject.Find` inside `Update` — forbidden, cache in Awake/Start; (e) file name `goblinController.cs` does not match class `GoblinController` and/or missing namespace.
   At least 4 of these 5 must be present.
3. Each violation row cites the rule document/item it comes from (not personal taste).
4. The agent does not rewrite the whole file as a fix; it only reports (showing the corrected identifier in a "고친 모습" column is fine).
5. 점검한 규칙 lists the rules actually compared (non-empty).

Judging rules: judge substance only. Code fences, headings, bullet style, extra explanatory notes or follow-up advice appended after the required answer do NOT count against it. Fail ONLY when one of the conditions listed above is actually violated in the answer itself; do not infer a violation from tone or from supplementary remarks.
