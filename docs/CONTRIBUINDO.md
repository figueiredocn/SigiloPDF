# Contribuindo

1. Leia `AGENTS.md`, arquitetura, privacidade e segurança.
2. Crie o ambiente virtual e instale `requirements.txt`.
3. Faça alterações pequenas dentro do escopo acordado.
4. Use PDFs sintéticos e execute `python -m pytest -q`.
5. Abra `python -m app.main` e confira as mensagens em pt-BR.
6. Descreva o comportamento alterado e os testes na pull request.

Não envie documentos pessoais para o repositório ou serviços externos. Dependências
devem ter uma finalidade local clara. O core não importa Qt; operações de UI não
devem ler documentos de forma síncrona. Novas ferramentas exigem revisão própria
e não devem ser ativadas como placeholders funcionais.
