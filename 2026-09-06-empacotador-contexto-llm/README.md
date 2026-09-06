# contextpack

CLI em Go que decide **quais arquivos de um projeto cabem na janela de
contexto de um LLM**, dado um orçamento de tokens, priorizando os arquivos
modificados mais recentemente.

## Por que esse tema

"Context engineering" — decidir o que entra na janela de contexto de um
agente de IA — é um dos temas mais discutidos em ferramentas de
desenvolvimento em 2026, com o crescimento de agentes de código (Claude
Code, OpenCode, Aider, Goose etc.) que precisam escolher, a cada execução,
um subconjunto de arquivos de um repositório grande para caber no limite de
tokens do modelo. A maioria das ferramentas resolve isso de forma gulosa
(pega os N arquivos mais recentes até estourar o orçamento), mas esse
problema é literalmente uma instância do **problema da mochila 0/1
(0/1 knapsack)**: cada arquivo tem um "peso" (tokens) e um "valor"
(prioridade), e queremos maximizar o valor total sem exceder a capacidade
(orçamento). Implementar a solução ótima via programação dinâmica, em vez da
heurística gulosa, é o algoritmo central deste projeto — inclusive existem
casos em que a solução gulosa por si é subótima (dois arquivos médios podem
valer mais que um grande), o que os testes automatizados comprovam.

## O que o programa faz

1. Varre um diretório recursivamente (ignorando `.git`, `node_modules`,
   `vendor`, `__pycache__`, `dist`, `build`, etc.).
2. Para cada arquivo com extensão de código/texto (configurável), estima a
   contagem de tokens usando a heurística amplamente adotada de
   **~4 caracteres por token** (aproximação documentada pela própria OpenAI
   para modelos de texto/código em inglês — não é uma contagem exata via
   BPE, mas é suficiente para decisões de orçamento com boa margem de
   segurança).
3. Atribui a cada arquivo uma prioridade baseada na idade (dias desde a
   última modificação): quanto mais recente, maior a prioridade — a ideia é
   que arquivos tocados recentemente são mais relevantes para o trabalho
   atual do agente.
4. Resolve o problema da mochila 0/1 via programação dinâmica
   (`O(n * orçamento)`) para encontrar o subconjunto de arquivos que
   **maximiza a prioridade total sem exceder o orçamento de tokens**.
5. Imprime um relatório (texto ou JSON) com os arquivos incluídos e
   excluídos, tokens usados e prioridade total.

## Como instalar e rodar

Requer apenas o Go (nenhuma dependência externa — só biblioteca padrão).

```bash
cd 2026-09-06-empacotador-contexto-llm
go build -o contextpack .

# Relatório em texto, orçamento de 4000 tokens, no diretório atual
./contextpack -dir . -budget 4000

# Saída em JSON
./contextpack -dir /caminho/do/projeto -budget 8000 -json

# Restringir a extensões específicas
./contextpack -dir . -budget 4000 -ext go,md
```

### Flags

| Flag       | Padrão | Descrição                                                        |
|------------|--------|-------------------------------------------------------------------|
| `-dir`     | `.`    | Diretório raiz a escanear                                          |
| `-budget`  | `8000` | Orçamento de tokens da janela de contexto                          |
| `-ext`     | (padrão interno) | Extensões separadas por vírgula (ex: `go,py,md`)         |
| `-json`    | `false`| Imprime o resultado em JSON em vez de texto                        |

## Como rodar os testes

```bash
cd 2026-09-06-empacotador-contexto-llm
go test ./... -v
```

Os testes cobrem:
- a heurística de estimativa de tokens (arredondamento correto);
- a função de prioridade por idade (limites mínimo/máximo);
- o algoritmo da mochila com uma instância clássica de solução conhecida,
  com orçamento zero, com orçamento generoso (inclui tudo) e verificando que
  o orçamento nunca é excedido;
- a varredura de diretório (extensões filtradas, diretórios ignorados,
  prioridade por idade calculada corretamente com `os.Chtimes`);
- o parsing de extensões passadas via flag.

## Limitações conhecidas (premissas assumidas)

- A contagem de tokens é uma **aproximação** (4 caracteres ≈ 1 token). Para
  uma contagem exata seria necessário embutir as tabelas de merge de um
  tokenizer real (ex.: `tiktoken`), o que foi considerado fora do escopo de
  um programa de um dia.
- A prioridade é baseada apenas na idade do arquivo (heurística simples e
  determinística). Um agente real poderia combinar isso com relevância
  semântica, histórico de edições recentes no git, etc. — deixado como
  possível evolução futura.
