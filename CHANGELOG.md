# Changelog — Oficina 20h

Um registro de cada dia do projeto: tema escolhido, o que foi construído e onde.

| Data       | Tema                                              | Descrição                                                                                                  | Pasta                              |
|------------|---------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| 2026-09-05 | Gerador de changelog a partir de Conventional Commits | CLI em Python que lê o `git log`, interpreta mensagens no padrão Conventional Commits (`feat`, `fix`, `BREAKING CHANGE`, etc.) e gera um changelog em Markdown agrupado por categoria. | `2026-09-05-gerador-changelog/` |
| 2026-09-06 | Empacotador de contexto para LLMs (context engineering) | CLI em Go que escaneia um diretório, estima tokens por arquivo e usa o algoritmo da mochila 0/1 (programação dinâmica) para selecionar o subconjunto de arquivos mais recentes que maximiza relevância dentro de um orçamento de tokens de contexto. | `2026-09-06-empacotador-contexto-llm/` |
