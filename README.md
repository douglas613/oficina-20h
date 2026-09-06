# Oficina 20h

Um programa (ou ferramenta) real e testável, novo a cada dia, construído de forma
totalmente autônoma por um agente de IA.

## Como funciona

- Uma rotina automatizada roda uma vez por dia, sem supervisão humana.
- A cada execução, o agente:
  1. Lê o histórico deste repositório (este `README.md` e o `CHANGELOG.md` na raiz)
     para não repetir tema, tecnologia central ou tipo de programa já coberto.
  2. Pesquisa um tema atual e específico em tecnologia, IA, ferramentas de
     desenvolvimento, dados ou automação — algo concreto o suficiente para virar
     um programa real (CLI, script, algoritmo, biblioteca) em poucas horas.
  3. Implementa o programa em uma subpasta nova, com testes automatizados
     (quando fizer sentido para o tipo de programa) e um `README.md` local.
  4. Roda os testes, confirma que tudo funciona, e só então commita e envia
     as mudanças para o repositório remoto.
  5. Registra o dia no `CHANGELOG.md` da raiz.

## Estrutura do repositório

Cada dia vive na sua própria subpasta, seguindo o padrão:

```
AAAA-MM-DD-nome-curto-do-tema/
├── README.md        # o que é, por que esse tema, como instalar e rodar, como testar
├── (código-fonte)
└── (testes automatizados, quando aplicável)
```

Nada é compartilhado entre pastas por padrão — cada dia é independente e pode usar
a linguagem, as dependências e a abordagem mais adequadas ao tema escolhido.

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
