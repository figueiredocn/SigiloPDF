# Contribuindo

Contribuições são bem-vindas. Para mudanças maiores, abra uma issue antes de começar para discutirmos o problema e o escopo.

1. Faça um fork e clone sua cópia.
2. Crie uma branch para a alteração.
3. Instale as dependências conforme o README e faça a mudança.
4. Execute `python -m pytest -q` no ambiente virtual. Se alterar a interface, valide também a abertura da janela e o fluxo afetado.
5. Abra um pull request descrevendo o problema, a solução e a validação.

Mantenha o processamento local e a direção UI → services → core. O core não importa PySide6. Não introduza telemetria, upload ou serviços remotos. Preserve o pt-BR na interface e mensagens, reutilize o parser existente e evite dependências e refatorações sem relação com a mudança.

Use documentos sintéticos nos testes. Não envie documentos pessoais, senhas, caminhos privados ou credenciais. Preserve os originais e a escrita segura das saídas. Leia também [AGENTS.md](AGENTS.md), [arquitetura](docs/ARQUITETURA.md) e [código de conduta](CODE_OF_CONDUCT.md).
