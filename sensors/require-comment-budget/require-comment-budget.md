# Comentários demais (ou em português) em `{{file}}`

Esta edição acrescentou {{comments}} linhas de comentário para {{code}} linhas de código. O orçamento é
de {{allowed}}: uma linha de comentário a cada 30 de código, com no mínimo uma. {{portuguese}} das linhas
novas de comentário parecem estar em português.

A conta não julga nenhum comentário isolado. É o formato que um diff gerado toma quando os comentários
narram o código em vez de dizer o que o código não diz: passos numerados, banners de seção, uma linha
repetindo a de baixo, histórico da mudança.

A regra está em `.claude/rules/code-comments.rule.md` e na seção "Code comments" do CLAUDE.md:

- **O padrão é não comentar.** Fica só o *porquê* que não dá para ler no código: uma restrição que não
  é óbvia, o contorno de um comportamento de ferramenta, um valor que parece errado e não é.
- **Sempre em inglês**, mesmo com docs e commits em português.
- **Nunca narre a mudança** ("movido daqui", "agora faz X", "antes era Y"). O git guarda a história.

## O que fazer

Releia cada comentário que esta edição escreveu. Para cada um, diga o que ele informa que o código e o
teste não informam. Se não houver nada, apague. Se ele explica um nome ruim, renomeie. Se está em
português, traduza para inglês.

Não bloqueia: se todos passam nesse crivo, siga.
