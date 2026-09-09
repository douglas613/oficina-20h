# Scanner ATS — Compatibilidade de Currículo x Vaga

CLI em Node.js (só biblioteca padrão, zero dependências) que compara o texto
de um currículo com o texto de uma descrição de vaga e produz um relatório
de compatibilidade no mesmo espírito de ferramentas comerciais como Jobscan
ou ResumeWorded.

## O que o programa faz

1. **Score de compatibilidade (0–100%)** — extrai as palavras-chave da vaga
   (removendo artigos/preposições comuns em PT/EN) e calcula quanto desse
   vocabulário, ponderado por frequência, aparece no currículo.
2. **Palavras-chave faltando** — lista, em ordem de frequência na vaga, os
   termos que o currículo não menciona — o que o candidato deveria
   considerar adicionar (se for verdade sobre sua experiência).
3. **Problemas de formatação estilo ATS** — sinaliza padrões conhecidos por
   quebrar parsers automáticos de currículo: ausência de e-mail/telefone
   detectável, ausência de seções padrão (Experiência, Educação,
   Habilidades), uso de layout em colunas/tabelas (tabs ou múltiplos
   espaços), e currículo curto ou longo demais.

## Por que esse tema

Ferramentas de "ATS resume check" são um produto real e maduro: Jobscan,
ResumeWorded, Teal e dezenas de concorrentes menores cobram assinatura
mensal (ou por scan) para exatamente este tipo de comparação
palavra-chave-a-palavra-chave entre currículo e vaga — é um dos poucos
nichos de "carreira" em que candidatos pagam de forma recorrente, porque a
dor (ser filtrado por um ATS antes de um humano ler o currículo) é
concreta e frequente (a cada nova candidatura). O mecanismo central
(frequência de palavras-chave + checagem de formatação) não depende de IA
generativa nem de serviço pago — é inteiramente determinístico e cabe em
um único arquivo, o que o torna fácil de embutir num produto maior.

## Potencial de monetização

- **Serviço para candidatos**: ofertar como consultoria/serviço avulso
  ("mando meu currículo + a vaga, recebo o relatório e ajusto") vendido em
  marketplaces como Fiverr/Workana, ou como parte de um pacote de
  "otimização de currículo".
- **Micro-SaaS freemium**: expor esta lógica atrás de uma página simples
  com upload de currículo + link da vaga, cobrando por scan além de um
  limite gratuito mensal — mesmo modelo do Jobscan.
- **Ferramenta interna para agências de RH/recrutamento**: pré-filtrar
  candidatos por aderência de palavras-chave antes da triagem humana,
  economizando tempo de recrutador (cobrado como parte de um serviço de
  recrutamento).
- **Isca de conteúdo/lead magnet**: oferecer o scan gratuito em troca do
  e-mail do candidato, alimentando uma lista para cursos ou mentorias de
  carreira.

## Como instalar e rodar

Não há dependências para instalar — só precisa do Node.js (18+; testado
com o runtime de teste nativo, disponível a partir da v18).

```bash
node ats_scanner.js --resume caminho/curriculo.txt --job caminho/vaga.txt
```

Opções:

- `--top N` — quantas palavras-chave faltantes listar (padrão: 10).
- `--json` — imprime o relatório em JSON em vez de texto formatado.

Exemplo com os arquivos de amostra incluídos em `exemplos/`:

```bash
node ats_scanner.js --resume exemplos/curriculo.txt --job exemplos/vaga.txt
```

## Como rodar os testes

Os testes usam o runner nativo do Node.js (`node:test` + `node:assert`),
sem precisar instalar nada:

```bash
node --test
```

12 testes cobrem: tokenização (remoção de stopwords), cálculo de score
(texto idêntico = 100%, texto não relacionado = score baixo, vaga vazia =
0%), detecção de palavras-chave faltantes, e cada um dos alertas de
formatação (contato ausente, seções ausentes, layout em colunas,
currículo curto).
