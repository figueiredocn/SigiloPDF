# Changelog

## [1.1.0] - 2026-10-05

### Adicionado

- Compressão local nos modos Leve, Equilibrada, Forte e Tamanho desejado, com comparação antes de salvar.
- Preview ampliado com navegação, zoom e ajuste à janela.
- Divisão adicional por pontos após páginas.
- Verificação opcional de releases oficiais, manual ou no máximo a cada 24 horas, desativada inicialmente.
- Fonte única de versão para aplicação e empacotamento.

### Melhorado

- Miniaturas compartilhadas e seleção visual sincronizada com o parser existente.
- Organização com arraste de grupos, movimentos laterais, início/fim e desfazer limitado.
- Preview temporário de rotação e seleção em PDF para imagens e Numeração.
- Sobre em Ajuda, com versão e acesso discreto à verificação de atualizações.
- Scripts existentes de build passam a consultar a versão central, preservando pacotes antigos.

### Corrigido

- Conflito com sinal nativo do Qt que impedia abrir o preview ampliado.
- Resultados antigos durante troca rápida de PDFs; workers retidos até entregar sua conclusão.
- Miniaturas enfileiradas durante o fechamento, evitando atualização tardia e divisão por zero.
- Rotação temporária residual quando a seleção se torna inválida.

## [1.0.0]

### Adicionado

- Consulta de informações técnicas dos PDFs.
- Junção, divisão, extração, remoção e rotação de páginas.
- Organização visual de páginas com miniaturas.
- Conversão de imagens para PDF e de páginas para imagens.
- Numeração de páginas e edição ou remoção de metadados comuns.
- Proteção por senha e remoção da proteção mediante senha correta.
- Interface em pt-BR, processamento local e criação de saídas sem substituir os originais.
