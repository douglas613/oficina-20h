# Oficina 20h

Um programa real, pequeno e testável — com potencial real de gerar renda —
construído de forma totalmente autônoma por um agente de IA, a cada 2 horas,
24 horas por dia.

## Como funciona

- Duas instâncias de agente rodam em paralelo, cada uma a cada 2 horas e
  intercaladas entre si (uma no Claude Code, outra no Cowork), sem supervisão
  humana. Juntas cobrem uma execução por hora, o dia inteiro.
- A cada execução, o agente:
  1. Lê o histórico deste repositório (este `README.md` e o `CHANGELOG.md` na
     raiz) e o índice acumulado (Artifact com o histórico visual de ambas as
     instâncias) para não repetir tema, mecanismo central ou tipo de programa
     já coberto por nenhuma das duas instâncias.
  2. Pesquisa uma ideia, ferramenta ou mecanismo com **potencial real de
     gerar renda** (para uso próprio, como produto/serviço, ou aplicado a um
     negócio) — algo concreto o suficiente para virar um programa real (CLI,
     script, algoritmo, biblioteca) implementável e testável em minutos, não
     horas. O critério não é "tecnologia em alta", é potencial de renda real.
  3. Implementa o programa em uma subpasta nova, com testes automatizados
     (quando fizer sentido para o tipo de programa) e um `README.md` local
     explicando o ângulo de monetização.
  4. Roda os testes, confirma que tudo funciona, e só então commita e envia
     as mudanças para o repositório remoto.
  5. Registra a execução no `CHANGELOG.md` da raiz e no índice acumulado.

## Estrutura do repositório

Cada execução vive na sua própria subpasta, seguindo o padrão:

```
AAAA-MM-DD-HHmm-code-nome-curto-do-tema/    # instância Claude Code
AAAA-MM-DD-HHmm-cowork-nome-curto-do-tema/  # instância Cowork
├── README.md        # o que é, por que esse tema, potencial de monetização, como instalar/rodar/testar
├── (código-fonte)
└── (testes automatizados, quando aplicável)
```

Nada é compartilhado entre pastas por padrão — cada execução é independente e pode
usar a linguagem, as dependências e a abordagem mais adequadas ao tema escolhido.

## Regras que o agente segue

- Sem dados sensíveis, credenciais reais, chaves de API ou serviços pagos.
- Preferência por dependências gratuitas, de código aberto e, quando possível,
  já presentes na biblioteca padrão da linguagem escolhida.
- Sem projetos que resultem apenas em uma página web estática (isso é coberto
  por outra rotina separada deste mesmo ecossistema).
- Todo dia com programa funcionando e testado antes do commit final — nunca
  código quebrado fica registrado como "concluído".

## Histórico

Veja [`CHANGELOG.md`](./CHANGELOG.md) para a lista completa de dias, temas e pastas.
