# Gerador de Changelog a partir de Conventional Commits

CLI em Python que lê o histórico de um repositório git, interpreta as mensagens
de commit no padrão [Conventional Commits](https://www.conventionalcommits.org/)
e gera um `CHANGELOG.md` em Markdown, agrupado por categoria (funcionalidades,
correções, breaking changes, etc).

## Por que esse tema

Automação de changelog é uma prática consolidada e em alta no ecossistema de
ferramentas de desenvolvimento (ex: `semantic-release`, `standard-version`,
`release-please`, `commitlint`) — times usam Conventional Commits justamente
para poder gerar changelogs e decidir versões automaticamente, sem depender de
alguém escrever isso manualmente a cada release. Também é um tema
especialmente apropriado para o próprio projeto Oficina 20h: este repositório
ganha um `CHANGELOG.md` novo a cada dia, então uma ferramenta que soubesse
gerar esse tipo de registro a partir dos commits fazia sentido como primeiro
projeto.

O escopo foi limitado deliberadamente à leitura/parsing/formatação — não inclui
bump automático de versão nem publicação (`npm publish`, tags, etc), para
manter o programa pequeno, sem dependências externas e sem exigir nenhum
serviço pago.

## Como funciona

1. Roda `git log` no repositório apontado (usando separadores de campo/registro
   não imprimíveis para lidar com mensagens de commit multi-linha com segurança).
2. Interpreta cada mensagem com uma regex do cabeçalho Conventional Commits:
   `tipo(escopo)!: descrição`, mais o rodapé `BREAKING CHANGE: ...`.
3. Agrupa os commits por seção (Funcionalidades, Correções, Documentação,
   Performance, Refatoração, Testes, Build & CI, Manutenção, Breaking Changes,
   Outras mudanças).
4. Renderiza tudo como Markdown, pronto para colar em um `CHANGELOG.md`.

Commits que não seguem o padrão não são descartados — caem em "Outras
mudanças" com a mensagem original, para nunca perder histórico.

## Instalação

Nenhuma dependência é necessária para rodar o programa — usa apenas a
biblioteca padrão do Python (3.9+) e o `git` já instalado no sistema.

Para rodar os testes, é necessário o `pytest`:

```bash
pip install pytest
```

## Como rodar

```bash
# Gera o changelog do histórico completo do repositório atual, no stdout
python3 changelog_gen.py

# Gera o changelog de um intervalo específico (ex: desde a última tag)
python3 changelog_gen.py --range v1.0.0..HEAD --title "v1.1.0"

# Aponta para outro repositório e escreve direto em um arquivo
python3 changelog_gen.py --repo ../outro-projeto --output CHANGELOG.md

# Exemplo real: gera o changelog deste próprio repositório (Oficina 20h)
python3 changelog_gen.py --repo ../.. --title "Histórico"
```

Saída de exemplo:

```markdown
## v0.1.0

### ✨ Funcionalidades

- **cli**: primeira versão (`75162ae`)

### 🐛 Correções

- corrige bug bobo (`c1f7fc5`)
```

## Como rodar os testes

```bash
pip install pytest
python3 -m pytest -q
```

Os testes cobrem:
- o parser de mensagens de commit (tipos conhecidos, escopo, breaking change
  via `!` e via rodapé `BREAKING CHANGE:`, mensagens fora do padrão);
- o agrupamento em seções e a renderização em Markdown;
- um teste de integração ponta a ponta que cria um repositório git **real**
  temporário (via `git init` em um diretório temporário), faz commits nele e
  roda o gerador contra esse repositório de verdade — incluindo um teste do
  filtro por intervalo de revisões (`--range`).
