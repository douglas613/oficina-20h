# Repropositor de Conteudo

CLI em Node.js (apenas runtime padrao, zero dependencias) que pega um texto
longo — artigo, post de blog, transcricao de video — e gera automaticamente
três variantes prontas para redes sociais:

- **Thread para X/Twitter** — sentencas empacotadas em tweets numerados
  `(i/N)`, respeitando o limite de 280 caracteres e quebrando sentencas
  longas por palavra inteira quando necessario.
- **Post para LinkedIn** — gancho + pontos-chave em formato de lista com
  seta, CTA de comentario e hashtags.
- **Legenda para Instagram** — gancho + bullets curtos + CTA de "salvar" +
  bloco de hashtags no final (convencao comum da plataforma).

A selecao das frases mais relevantes usa sumarizacao extrativa por
frequencia de palavras (estilo algoritmo de Luhn): conta a frequencia de
cada palavra relevante (ignorando stopwords em PT/EN), pontua cada sentenca
pela media de frequencia das suas palavras, e aplica um leve bonus a
sentencas do inicio do texto (que costumam carregar a tese central). As
hashtags saem das palavras mais frequentes do proprio texto.

## Por que esse tema

Criadores de conteudo, agencias de marketing e freelancers de social media
gastam uma quantidade enorme de tempo reescrevendo manualmente o mesmo
conteudo para cada rede (thread no X, post no LinkedIn, legenda no
Instagram) — é o trabalho de "repurposing" que ferramentas como Repurpose.io,
Contentdrips e assistentes de redação para redes sociais cobram para
resolver. Esta versao ataca a parte de texto do problema (sem exigir video
ou IA generativa paga) com um algoritmo determinístico, rápido e sem custo
de API.

## Potencial de monetizacao

- **Ferramenta interna para agencias de marketing/social media**: alimenta o
  repropositor com cada artigo de blog do cliente e usa a saida como
  primeiro rascunho, cortando o tempo de producao de conteudo por cliente.
- **Micro-SaaS/plugin freemium**: versao web ou plugin de CMS (WordPress,
  Ghost) que gera as tres variantes automaticamente ao publicar um post,
  cobrando por volume de artigos processados por mes (modelo usado por
  ferramentas de repurposing pagas).
- **Servico avulso para criadores de conteudo/consultores PJ** que publicam
  em múltiplas redes mas só escrevem em uma: venda como "pacote de
  distribuicao de conteudo" cobrado por artigo ou por assinatura mensal.

## Como instalar e rodar

Requer apenas Node.js (18+) — nenhuma dependencia externa (`npm install` nao
é necessario).

```bash
node repropositor.js --file caminho/para/artigo.txt
```

Ou via stdin:

```bash
cat artigo.txt | node repropositor.js
```

Saida como JSON (útil para integrar com outra ferramenta):

```bash
node repropositor.js --file artigo.txt --json
```

Escrever cada variante em um arquivo separado:

```bash
node repropositor.js --file artigo.txt --out-dir saida/
# gera saida/twitter.txt, saida/linkedin.txt, saida/instagram.txt
```

## Como rodar os testes

Usa o test runner nativo do Node.js (`node --test`), sem framework externo:

```bash
npm test
# ou diretamente:
node --test tests/repropositor.test.js
```

11 testes cobrem: divisao de sentencas, ranqueamento por frequencia,
empacotamento de tweets dentro do limite de caracteres (incluindo quebra de
sentencas muito longas), numeracao sequencial da thread, deduplicacao e
filtro de hashtags curtas, e o pipeline completo (`repurpose`) com texto
normal e com texto vazio.
