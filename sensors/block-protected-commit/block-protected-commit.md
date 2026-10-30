# `{{action}}` numa branch protegida

Você está na `{{branch}}`, uma branch compartilhada. Trabalho nunca chega nela por commit local ou
amend: chega por PR revisado, e o merge é o único jeito de o histórico dela andar.

Crie uma branch antes:

```
git switch --create feat/minha-mudanca
```

O `check-branch-prefix` documenta os prefixos. Depois faça o commit lá, dê push e abra o PR em draft.

## Já fez o commit aqui por engano?

O commit ainda é local, então nada se perdeu. Leve-o para a branch nova antes de mexer no histórico da
`{{branch}}`. `git branch --force` não é um reset e move a ref sem precisar estar nela:

```
git branch feat/minha-mudanca
git switch feat/minha-mudanca
git branch --force {{branch}} origin/{{branch}}
```

## Worktree ou comando que aponta outro checkout?

O sensor lê o repositório que o comando atinge pelo próprio texto, não só o diretório do hook:
`cd <caminho>`, `git -C <caminho>`, `--git-dir` e `GIT_DIR=` (na frente do comando, via `env` ou num
`export` anterior no mesmo comando). Se o repositório indicado por `--git-dir`/`GIT_DIR` não existe ou
a branch dele não pode ser lida, o sensor bloqueia. Uma troca de branch anterior no mesmo comando
só conta quando ligada por `&&` (`git switch -c feat/x && ...`), porque aí o resto só roda se a troca
deu certo. Depois de `;`, `||`, `&`, `|` ou quebra de linha, o sensor considera a branch de antes e a
nova, e bloqueia se qualquer uma for protegida.

Branches protegidas: {{protected}}.
