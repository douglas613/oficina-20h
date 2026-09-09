# Changelog — Oficina 20h

Um registro de cada execução do projeto (a cada 2 horas, em duas instâncias
intercaladas — Claude Code e Cowork): tema escolhido, o que foi construído e onde.

| Data       | Hora  | Instância   | Tema                                              | Descrição                                                                                                  | Pasta                              |
|------------|-------|-------------|---------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| 2026-09-05 | —     | Claude Code | Gerador de changelog a partir de Conventional Commits | CLI em Python que lê o `git log`, interpreta mensagens no padrão Conventional Commits (`feat`, `fix`, `BREAKING CHANGE`, etc.) e gera um changelog em Markdown agrupado por categoria. | `2026-09-05-gerador-changelog/` |
| 2026-09-06 | —     | Claude Code | Empacotador de contexto para LLMs (context engineering) | CLI em Go que escaneia um diretório, estima tokens por arquivo e usa o algoritmo da mochila 0/1 (programação dinâmica) para selecionar o subconjunto de arquivos mais recentes que maximiza relevância dentro de um orçamento de tokens de contexto. | `2026-09-06-empacotador-contexto-llm/` |
| 2026-09-09 | 21:04 | Claude Code | Scanner ATS de compatibilidade currículo x vaga | CLI em Node.js (stdlib apenas) que calcula um score de compatibilidade de palavras-chave entre currículo e vaga, lista termos faltantes e sinaliza problemas de formatação que quebram parsers de ATS (contato ausente, seções faltando, layout em colunas), no molde de produtos pagos como Jobscan/ResumeWorded — vendável como serviço avulso, micro-SaaS freemium ou ferramenta interna de triagem para agências de recrutamento. | `2026-09-09-2104-code-scanner-ats/` |
