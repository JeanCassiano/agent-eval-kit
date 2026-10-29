# Verificação pulada

Detectado: `{{bypass}}`

Os hooks do git (os deste repositório e os que cada pessoa tiver configurado) são o piso de
verificação de um commit ou de um push. Pular não resolve o problema: só o empurra para o CI, para quem
revisa ou para o histórico publicado, onde uma credencial vazada não volta mais.

Rode o comando normal e deixe os hooks executarem. Se um deles falhar, a falha é o ponto: corrija o
que ele encontrou.

## O que conta como pular

- `--no-verify` em `git commit` ou `git push`, inclusive abreviado (`--no-veri` em diante)
- `git commit -n`, e qualquer grupo de flags curtas com `n`
- `core.hooksPath` redirecionado, por `git -c`, por `git config` ou por uma variável `GIT_CONFIG_*`
- qualquer um dos acima dentro de `bash -c`, `eval`, subshell (`( … )`, `$( … )`, crases), atrás de
  `env`, `command`, `time`, `nohup`, `sudo`, `nice`, `ionice`, `timeout`, `stdbuf`, `xargs`, `flock`,
  `watch` ou `exec`, dentro de `if`/`while`/`for`, em segundo plano (`&`) ou num pipe, ou num alias do
  git definido no mesmo comando

Se um hook está errado de verdade, corrija o hook num PR. Desligar um controle é decisão humana: rode o
git fora do agente.

## Limite conhecido

O sensor lê o texto do comando. Ele lê o que está escrito dentro de `$(...)` e de crases, mas não
executa nada: o que só aparece quando o comando roda (a saída de um `$(...)` usada como argumento, uma
variável, um alias do git configurado em outra sessão) fica com a revisão.
