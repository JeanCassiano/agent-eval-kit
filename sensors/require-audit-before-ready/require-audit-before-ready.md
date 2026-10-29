# `gh pr ready` sem auditoria aprovada para o head atual

PR: {{pr}}
Head: `{{head}}`

{{reason}}

Um PR só sai do draft quando tem, nos comentários, um veredito do `pr-auditor` cuja linha começa com
`audit: pass <sha>`, e o `<sha>` é o `headRefOid` atual
do PR, completo (40 caracteres; prefixo não vale).
Se o último veredito para este head for `audit: fail`, ele vale até sair um `pass` novo.

## O que fazer

1. Confirme que o push terminou e que o `headRefOid` do PR é o seu `git rev-parse HEAD`.
2. Rode a skill `adversarial-pr-verification` com o agente `pr-auditor`, num contexto frio, contra esse
   head.
3. Publique o veredito como comentário do PR: `gh pr comment <n> --body-file <arquivo>`, com
   `audit: pass <sha>` ou `audit: fail <sha>` na primeira linha. Rode o `gh pr ready` numa chamada
   separada: o sensor lê o PR antes de o comando rodar, então `gh pr comment … && gh pr ready` num
   comando só é bloqueado.
4. Corrija o que falhou, dê push e repita. Só com `audit: pass` neste head o `gh pr ready` passa.

Se o erro foi do `gh` (rede, autenticação, PR inexistente), resolva e tente de novo: sem ler o PR, o
sensor não tem como confirmar a auditoria e por isso bloqueia.

Voltar para draft (`gh pr ready --undo`) nunca é bloqueado.
