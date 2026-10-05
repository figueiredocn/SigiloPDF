# Roadmap

## Funcionalidades da versão 1.0 implementadas

- Janela em pt-BR, identidade visual e cards das doze ferramentas.
- Informações do PDF com seleção, arraste e leitura em segundo plano.
- Juntar PDFs com ordem configurável, progresso e preservação dos originais.
- Dividir PDF por página, intervalo, páginas específicas ou combinação, com nomes sem sobrescrita.
- Extrair páginas com resumo, ordem informada e preservação da qualidade original.
- Remover páginas com resumo, proteção contra remoção total e saída nova.
- Girar páginas em 90° horário, 90° anti-horário ou 180°, com seleção ou aplicação total.
- Organizar páginas com miniaturas progressivas, seleção múltipla e saída sem rasterização.
- Imagens para PDF com JPG/JPEG/PNG/BMP, ordem configurável, páginas e ajustes proporcionais.
- PDF para imagens em PNG/JPEG, seleção pelo parser existente, 96/150/200/300 DPI e cancelamento entre páginas.
- Numeração vetorial com seleção, número/página inicial, formatos, posições e margem segura.
- Metadados comuns: leitura, edição e remoção de Info/XMP, com aviso sobre anonimização.
- Proteção AES-256 e remoção mediante senha correta, sem persistência de senhas.
- Tela Sobre com versão, licença e processamento local.
- Separação UI → services → core e testes com documentos sintéticos.

## Versão 1.1.0

- Comprimir PDF: Leve, Equilibrada, Forte e Tamanho desejado.
- Otimização estrutural antes da redução de imagens, sem rasterizar páginas.
- Até sete tentativas, limites mínimos de qualidade e indicação de meta não atingida.
- Comparação antes de salvar, nomes seguros e cancelamento entre etapas.
- Preservação de criptografia e aviso sobre assinaturas detectadas.
- Verificação opcional de releases oficiais, manual ou a cada 24 horas.
- Versão centralizada, pacotes Windows e histórico preservado no GitHub Releases.

## Publicação e etapas futuras

- Na versão 1.1.0: miniaturas compartilhadas, seleção Ctrl/Shift, visualização
  ampliada, movimentação de grupos, desfazer limitado e divisão por pontos.
- Validar estas melhorias em outros equipamentos antes de distribuir um novo
  executável. Processamento de documentos continua local.

- Código-fonte da versão 1.0 publicado, com documentação, capturas reais e testes automatizados.
- Distribuição Windows x64 preparada e validada, com instalador, portátil, licenças e fontes correspondentes.
- Revisão de acessibilidade e validação em outras versões de Windows permanecem como etapas futuras.

Cada ferramenta deverá ter testes, mensagens em pt-BR, saídas escolhidas
explicitamente e proteção contra sobrescrita automática. Não há previsão
de telemetria, contas, nuvem ou processamento remoto.
