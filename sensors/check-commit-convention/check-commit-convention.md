# Mensagem de commit recusada

Recebido: `{{received}}`

{{violation}}

Esperado: `<tipo>(<escopo>): <assunto>`, com no máximo 72 caracteres na linha inteira.

## Escolhendo o tipo

O tipo é fixo em inglês porque é sintaxe do padrão; o assunto continua em português. Quando mais de um
cabe, vence o de cima.

| Tipo       | Para                                                                    |
| ---------- | ----------------------------------------------------------------------- |
| `feat`     | funcionalidade nova ou melhoria (verificador, métrica, comando, painel) |
| `fix`      | correção de bug em algo que já existe                                   |
| `perf`     | mudança cujo objetivo é desempenho                                      |
| `refactor` | reestruturação que preserva o comportamento                             |
| `test`     | só testes                                                               |
| `docs`     | só documentação                                                         |
| `build`    | imagem, Docker, empacotamento                                           |
| `ci`       | workflows e pipeline (GitHub Actions)                                   |
| `chore`    | o que não é produto: DX, tooling, harness, dependências, release        |
| `style`    | só formatação, sem mudar o significado                                  |
| `revert`   | reverte um commit anterior                                              |

## O resto da linha

- **Escopo**: opcional, uma palavra minúscula (`runner`, `checks`, `metrics`, `report`, `cli`,
  `agents`, `otel`, `compose`, `grafana`, `docs`, `harness`).
- **Assunto**: imperativo, em português, sem ponto final. Os 72 caracteres contam tipo e escopo.
- **Breaking change**: `!` depois do tipo ou escopo e rodapé `BREAKING CHANGE:`. Só quando exige ação de
  quem opera, nunca para dizer "commit grande".

## Exemplos

```
feat(checks): adiciona verificador de faixa numérica
fix(metrics): usa interpolação linear no p95
chore(harness): migra os hooks para sensores em Python
chore(release): 1.2.0
```

Os formatos lidos são `-m`, `--message`, heredoc (`-m "$(cat <<'EOF' ... EOF)"` e `-F - <<EOF`) e
`-F <arquivo>`. Commit aberto no editor não passa por aqui.

Referência: [Conventional Commits 1.0.0](https://www.conventionalcommits.org/pt-br/v1.0.0/)
