# Orientações para desenvolvimento do SigiloPDF

- Preserve o processamento exclusivamente local. Não introduza telemetria,
  analytics, login, cloud, backend remoto ou APIs externas para documentos.
- Mantenha a direção UI → services → core. O core nunca importa PySide6.
- Workers chamam services e devolvem resultados por sinais, sem acessar widgets.
- Use pt-BR na interface, mensagens de erro e documentação.
- Escreva funções pequenas com type hints e responsabilidades separadas.
- Não sobrescreva documentos automaticamente. Futuras saídas exigem destino
  explícito e confirmação de substituição quando houver conflito.
- Operações pesadas ficam fora da thread gráfica. Não registre conteúdo,
  caminhos pessoais ou senhas em logs.
- Use PDFs sintéticos em testes; nunca adicione documentos de usuários ao Git.
- Execute `python -m pytest -q` e valide a abertura da janela após mudanças de UI.
- Mantenha o escopo atual: Informações do PDF, Juntar PDFs, Dividir PDF e Extrair
  páginas, Remover páginas, Girar páginas, Organizar páginas, Imagens para PDF, PDF para imagens, Numeração, Metadados e Proteção por senha. Não ative outras ferramentas sem
  solicitação explícita.
- Reutilize o parser de páginas. A divisão usa ordem crescente; a extração usa
  a opção de preservar a ordem informada. Não altere o padrão sem necessidade.
