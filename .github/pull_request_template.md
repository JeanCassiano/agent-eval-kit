## O que muda

<!-- História do Jira (AE-N) e o que este PR entrega dela. -->

## Como testei

- [ ] `make verify` (gates do CI, menos o e2e da observabilidade)
- [ ] Mudou métrica ou verificador? Números do teste ponta a ponta (seed fixa) iguais, ou o motivo da mudança descrito acima
- [ ] Mudou export OTel ou o compose? `make verify VERIFY_E2E=1`
- [ ] Mudou a imagem ou a demo? `docker compose run --rm eval demo` com `./out` limpo
- [ ] Mudou o adaptador de modelo? Uma chamada real, com o nome do modelo, sem chave nem resposta crua no PR
- [ ] Mudou o painel? Print com `make screenshot` na seção abaixo

## Auditoria

- [ ] PR aberto em draft
- [ ] `pr-auditor` rodou num contexto frio contra o head atual
- [ ] Comentário `audit: pass <sha>` com o SHA do head atual publicado antes do `gh pr ready`

## Evidência visual
