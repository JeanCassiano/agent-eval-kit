# O nome da branch não segue a convenção de prefixo

Recebido: `{{received}}`

Esperado: `<prefixo>/<nome-em-kebab-case>`, com minúsculas, dígitos e hífens, sem hífen no início ou no
fim. As exceções são as branches de release, descritas abaixo.

## Prefixos

O prefixo é o tipo dos commits da branch, a mesma lista que o `check-commit-convention` aceita:

- `feat/`: funcionalidade nova ou melhoria (verificador, métrica, comando, painel).
- `fix/`: correção de bug.
- `refactor/`: reestruturação que preserva o comportamento.
- `docs/`, `test/`, `ci/`, `build/`, `perf/`, `style/`, `revert/`: branch cujo trabalho é quase todo
  desse tipo.
- `chore/`: o resto que não é produto, como DX, tooling, harness e dependências.

Quando a branch mistura tipos, vale o que decide o que ela entrega: `feat`, `fix` e `refactor` ganham
dos demais.

## Release

- `release/X.Y.Z`: prepara a versão `vX.Y.Z`. Versão com três números, sem zero à esquerda e sem `v`.
- `chore/back-merge-vX-Y-Z`: traz uma release de volta para a `develop`.

`develop` e `main` são de longa duração e não levam prefixo.

## Exemplos

```
feat/verificador-json-fields
fix/p95-interpolacao
chore/claude-hooks
release/1.2.0
chore/back-merge-v1-2-0
```

## Limite conhecido

Só vê branches criadas pela linha de comando (`git checkout -b`, `git switch -c`, `git worktree add -b`,
`git worktree add <caminho>`, `git branch <nome>`, `git branch -m|-c <novo>`). Branch criada pela interface do GitHub ou por automação não passa por aqui; a
convenção vale do mesmo jeito e é cobrada na revisão.

Referência: [Conventional Branch](https://conventionalbranch.org/)
