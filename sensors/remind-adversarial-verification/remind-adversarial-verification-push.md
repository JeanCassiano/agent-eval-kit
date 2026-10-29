# Este push move o head do PR {{pr}}: a auditoria ficou velha

A branch `{{branch}}` tem o PR {{pr}} aberto. Um veredito `audit: pass <sha>` vale para um SHA só, e
este push cria outro head.

- Se o PR já saiu do draft, volte com `gh pr ready {{pr}} --undo`.
- Reescreva o corpo contra o head novo com `gh pr edit --body-file`: o que os commits novos desfizeram ou
  estreitaram, e toda contagem refeita neste head. Se o head anterior falhou na auditoria, corrija cada
  instância que aquele veredito apontou no corpo.
- Depois do push, confirme que o `headRefOid` do PR é o SHA local e rode uma auditoria nova com o
  `pr-auditor`, num contexto frio.

Não bloqueia: o veredito é julgamento. O fluxo está em `.claude/rules/workflow.rule.md`.
