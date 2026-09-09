# pii-gate — gateway de privacidade para prompts de LLM

CLI em Python (só biblioteca padrão, zero dependências) que **detecta e
redige informação pessoal identificável (PII)** em um texto antes dele ser
mandado para uma API de LLM de terceiros (ChatGPT, Claude, Gemini, etc), e
permite **restaurar** os valores originais depois, a partir de um mapa
salvo localmente — que nunca é enviado a lugar nenhum.

## O que o programa faz

1. **Detecta** e-mail, CPF, CNPJ, CEP, telefone brasileiro, número de
   cartão de crédito, endereço IP e tokens de API comuns (`sk-...`,
   `ghp_...`, `AKIA...`, `xox?-...`) em texto livre.
2. **Redige** cada ocorrência trocando o valor por um placeholder estável
   (`[EMAIL_1]`, `[CPF_1]`, `[TELEFONE_BR_1]`...) — o mesmo valor sempre
   vira o mesmo placeholder dentro de uma execução, então o texto continua
   coerente para a LLM (ela consegue perceber "é a mesma pessoa
   mencionada duas vezes" sem nunca ver o dado real).
3. **Salva um mapa local** (`--map-file mapa.json`) ligando cada
   placeholder ao valor original, para permitir restaurar a resposta da
   LLM depois (`pii_gate.py restore`) — por exemplo, se a LLM ecoa
   `[EMAIL_1]` na resposta, você troca de volta pelo e-mail real antes de
   mostrar ao usuário final, sem que o e-mail real jamais tenha saído da
   sua máquina/servidor.
4. **CPF, CNPJ e cartão de crédito passam por validação de dígito
   verificador** (algoritmos reais: módulo 11 para CPF/CNPJ, Luhn para
   cartão) — isso evita redigir qualquer sequência de 11 ou 14 dígitos que
   apareça no texto (o que geraria falsos positivos demais e destruiria a
   legibilidade do prompt), redigindo só números que são estruturalmente
   válidos.

## Por que esse tema

Em 2026, LGPD/GDPR e a adoção em massa de LLMs de terceiros dentro de
empresas colidem de frente: times colam trechos de e-mail, planilhas de
clientes, tickets de suporte e contratos direto em prompts do ChatGPT ou
Claude, sem perceber que estão mandando dado pessoal para fora do
perímetro da empresa — isso é hoje classificado pela OWASP como risco
`LLM02: Sensitive Information Disclosure` no Top 10 de LLM. Ferramentas
comerciais para resolver exatamente isso (Presidio da Microsoft, LLM
Guard, Private AI, Strac, gateways de "privacy filter") são uma categoria
de produto ativa e crescendo em 2026 — algumas cobram por token
processado, outras vendem como appliance on-prem para setor regulado
(saúde, financeiro, jurídico).

O diferencial deste projeto para o dia é focar em **documentos brasileiros
reais** (CPF, CNPJ, CEP, telefone BR com DDD) com checksum de verdade — a
maioria das ferramentas gratuitas trata só de padrões americanos/genéricos
(SSN, e-mail, IP) e erra feio ao lidar com CPF/CNPJ. É um nicho concreto
(compliance LGPD para uso de IA generativa) que ainda não tinha sido
coberto neste repositório, roda inteiramente local/determinístico (sem
depender de nenhum serviço de IA nem API paga) e cabe em um único arquivo,
fácil de embutir como middleware em qualquer pipeline que chame uma LLM.

## Potencial de monetização

- **Biblioteca/CLI freemium**: versão grátis com os padrões deste
  arquivo; versão paga com mais entidades (RG, nome próprio via
  dicionário, endereço completo, dados de saúde) e suporte a outros
  países.
- **Middleware vendável para empresas**: plugar como camada obrigatória
  antes de qualquer chamada a API de LLM externa (ChatGPT, Claude API) em
  ferramentas internas — um caso de uso de compliance que empresas
  reguladas (bancos, plano de saúde, jurídico) pagam para não terem que
  construir internamente.
- **Serviço de auditoria**: rodar contra logs/histórico de prompts de uma
  empresa e gerar relatório de quantos dados pessoais vazaram para APIs de
  terceiros nos últimos N meses — vendável como avaliação pontual de
  risco (LGPD gap assessment).

## Como instalar

Nenhuma dependência é necessária para rodar o programa — usa apenas a
biblioteca padrão do Python (3.9+).

Para rodar os testes, é necessário o `pytest`:

```bash
pip install pytest
```

## Como rodar

```bash
# Redige PII de um texto vindo do stdin, imprime o resultado no stdout
echo "Meu email é ana@empresa.com, CPF 529.982.247-25" | python3 pii_gate.py redact

# Salva o mapa de restauração (necessário para poder reverter depois)
python3 pii_gate.py redact -i prompt.txt -o prompt_redigido.txt -m mapa.json

# Restaura os valores originais em cima de uma resposta da LLM
python3 pii_gate.py restore -i resposta_llm.txt -m mapa.json

# Filtra só alguns tipos de entidade
echo "email ana@x.com, CPF 529.982.247-25" | python3 pii_gate.py redact --types EMAIL
```

Sem `--map-file`, a redação é **proposital e explicitamente irreversível**
(o programa avisa isso no stderr) — é o modo mais seguro por padrão, para
o caso de uso onde você só quer garantir que PII não vaze, sem nunca
precisar reconstruir o valor original.

## Como rodar os testes

```bash
pip install pytest
python3 -m pytest -q
```

Os testes (23 casos) cobrem:
- os validadores de dígito verificador (CPF, CNPJ, Luhn) com casos válidos
  e inválidos;
- a detecção de cada tipo de entidade (e-mail, CPF, CNPJ, CEP, telefone
  BR, IP, token de API, cartão de crédito);
- reuso do mesmo placeholder para o mesmo valor repetido no texto, e
  placeholders distintos para valores diferentes;
- filtro por tipo de entidade (`--types`);
- ida e volta completa `redact` → `restore` preservando o texto original
  exatamente, inclusive com muitos placeholders do mesmo tipo (para
  garantir que não há colisão entre `[EMAIL_1]` e `[EMAIL_10]`);
- um teste de integração ponta a ponta via subprocesso, chamando o CLI de
  verdade (`redact` gerando um `mapa.json` real, depois `restore` lendo
  esse arquivo).
