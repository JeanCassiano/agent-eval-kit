# Audite este PR agora, num contexto frio

{{draft}}

Rode a skill `adversarial-pr-verification` (agente `pr-auditor`) assim que o draft existir, sem esperar
o CI. Auditoria e CI são gates independentes e respondem perguntas diferentes: o CI pergunta se o código
roda; a auditoria pergunta se o corpo do PR diz a verdade.

- Antes, responda você mesmo essa pergunta sobre o corpo do PR: toda contagem, todo "nenhum uso", todo
  "não mexe em X", todo print citado é um comando rodado neste head ou um arquivo que você abriu, nunca
  memória. Corrija o que não se sustenta com `gh pr edit --body-file` antes de a auditoria começar.
- A auditoria roda contra o **head exato** e num contexto que não escreveu o código.
- O veredito vai como comentário do próprio PR, com a primeira linha `audit: pass <sha>` ou
  `audit: fail <sha>`, publicado com `gh pr comment <n> --body-file <arquivo>`. Nunca no corpo do PR e
  nunca como arquivo na branch, que criaria um head novo.
- Qualquer push depois disso invalida o veredito: volte o PR para draft, reescreva o corpo contra o head
  novo e audite de novo.
- O `gh pr ready` é bloqueado pelo `require-audit-before-ready` enquanto não houver `audit: pass` com o
  SHA do head atual.

Não bloqueia: o veredito é julgamento. O fluxo está em `.claude/rules/workflow.rule.md`.
