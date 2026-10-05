# Contribuindo

Contribuições são bem-vindas. Para mudanças maiores, abra uma issue antes de começar para discutirmos o problema e o escopo.

1. Faça um fork e clone sua cópia.
2. Crie uma branch para a alteração.
3. Instale as dependências conforme o README e faça a mudança.
4. Execute `python -m pytest -q` no ambiente virtual. Se alterar a interface, valide também a abertura da janela e o fluxo afetado.
5. Abra um pull request descrevendo o problema, a solução e a validação.

Mantenha o processamento dos documentos local e a direção UI → services → core.
O core não importa PySide6. Workers chamam serviços e retornam resultados por
sinais, sem acessar widgets. Operações pesadas ficam fora da thread gráfica.
Não introduza telemetria, upload ou processamento remoto. A consulta opcional de
releases oficiais é a exceção de rede já documentada em
[privacidade](docs/PRIVACIDADE.md); não deve receber contexto de documentos.

Use pt-BR na interface, erros e documentação. Escreva funções pequenas com type
hints e responsabilidades separadas. Reutilize o parser de páginas: divisão usa
ordem crescente; extração preserva a ordem informada. Novas ferramentas devem ter
escopo discutido, testes e validação próprios; não ative placeholders como se
fossem funções prontas.

Use documentos sintéticos nos testes. Não envie documentos pessoais, senhas,
caminhos privados ou credenciais. Não registre conteúdo, caminhos pessoais ou
senhas em logs. Preserve os originais e a escrita segura: destino explícito,
sem sobrescrita automática e com nomes novos em conflitos. Evite dependências e
refatorações sem relação com a mudança.

Leia também a [arquitetura](docs/ARQUITETURA.md), as
[limitações de segurança](docs/SEGURANCA.md) e o
[código de conduta](CODE_OF_CONDUCT.md).
