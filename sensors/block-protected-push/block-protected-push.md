# Push para branch protegida (`{{branch}}`)

Push direto numa branch protegida pula o PR e, com ele, a revisão, o CI, a auditoria adversarial e o
merge que registra quem aprovou o quê. Aqui ainda tem um agravante: a `main` é o
que quem clona o repositório roda na demo.

Abra um PR em draft (`.claude/rules/workflow.rule.md`).

Protegidas: {{protected}}.

## O que foi detectado

Um destes:

- um argumento que nomeia a branch protegida: `git push origin develop`, `+main`, `refs/heads/main`
- um refspec cujo destino é a branch protegida: `HEAD:develop`, `:main`, `feat/x:main`, `develop:main`
- um push que manda a branch atual estando nela: `git push`, `git push origin`, `git push -u origin HEAD`
- `--all`, `--branches` ou `--mirror`, que levam todas as branches
- um push que recebe argumentos do `xargs`, que o sensor não tem como ler

Não é bloqueado:

- refspec no sentido contrário, como `main:feat/x`, que lê a protegida e escreve em outra
- push de tag (`git push origin v1.2.0`, `git push origin --tags`)

## Worktree ou comando que aponta outro checkout?

O sensor lê o repositório que o comando atinge pelo próprio texto, não só o diretório do hook:
`cd <caminho>`, `git -C <caminho>`, `--git-dir` e `GIT_DIR=` (na frente do comando, via `env` ou num
`export` anterior no mesmo comando). Se o repositório indicado por `--git-dir`/`GIT_DIR` não existe ou
a branch dele não pode ser lida, o sensor bloqueia. Uma troca de branch anterior no mesmo comando
só conta quando ligada por `&&` (`git switch -c feat/x && ...`), porque aí o resto só roda se a troca
deu certo. Depois de `;`, `||`, `&`, `|` ou quebra de linha, o sensor considera a branch de antes e a
nova, e bloqueia se qualquer uma for protegida.

## Exceções legítimas

Uma emergência que precise mesmo pular a revisão é decisão humana. Rode o git fora do agente, para que
fique registrada como tal.
