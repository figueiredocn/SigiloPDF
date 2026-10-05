# Status do SigiloPDF

## Versão analisada

1.1.0, revisão de 5 de outubro de 2026, comparada à release pública v1.0.0.
A auditoria inicial executou 423 testes existentes, todos aprovados, antes de
implementar a consulta opcional de atualizações. Os números finais e artefatos
estão nas notas da release e no relatório local de validação. A revisão final
executou 451 testes, todos aprovados, incluindo 28 novos testes de atualização.
O binário real também passou em Windows Sandbox, sem Python pré-instalado e
sem rede: portátil, ferramentas, instalação em pasta escolhida, versão instalada,
desinstalação e preservação de um documento sintético de controle.

## Funcionalidades estáveis

| Recurso | Estado verificado |
|---|---|
| Informações do PDF | Funcional; leitura, seleção e arraste |
| Juntar PDFs | Funcional; ordem, progresso e saída exclusiva |
| Dividir PDF | Funcional; quatro modos existentes e pontos de divisão |
| Extrair páginas | Funcional; parser compartilhado e ordem informada |
| Remover páginas | Funcional; exige manter pelo menos uma página |
| Girar páginas | Funcional; rotação dos objetos sem rasterização |
| Organizar páginas | Funcional; seleção, grupos, arraste, setas e desfazer |
| Miniaturas e preview | Funcional com limites de memória e resolução |
| Imagens para PDF | Funcional; JPG/JPEG/PNG/BMP e ordem configurável |
| PDF para imagens | Funcional; PNG/JPEG, seleção e resolução configurável |
| Numeração | Funcional; texto vetorial e seleção de páginas |
| Metadados | Funcional; edição/remoção de Info e XMP comuns |
| Proteção e remoção autorizada | Funcional; AES-256 e senha correta |
| Compressão | Funcional com limitações; estrutura/imagens e comparação |
| Sobre e interação oculta | Funcionais, com regressão testada |
| Atualizações | Manual/automática opcional; estados e falhas simulados |

Workers chamam serviços e retornam sinais; widgets são atualizados na thread
gráfica. O fechamento aguarda tarefas e cancela prévias entre páginas.
As saídas não sobrescrevem documentos, inclusive em conflitos de concorrência.
O core permanece sem PySide6. Nenhuma ferramenta de documentos usa rede.

## Funcionalidades com limitações

- Ferramentas gerais recusam PDFs criptografados; Informações indica proteção.
  Proteção permite remoção mediante senha correta; Compressão pede senha e
  preserva criptografia. Não existe quebra ou descoberta de senha.
- Compressão não garante atingir a meta; reduzir imagens pode diminuir sua
  qualidade. Imagens incompatíveis são preservadas. Até sete tentativas.
- Metadados comuns podem ser removidos; isso não garante anonimização do conteúdo.
- Preview: ícones limitados a 64 MiB por painel; ampliação de aproximadamente
  quatro milhões de pixels. Histórico de organização limitado a 20 estados.

## Problemas corrigidos nesta revisão

- Versões fixas e divergentes no empacotamento foram substituídas pela fonte única.
- Desde v1.0.0: corrigidos conflito de sinal do preview, resultados de sessões
  antigas e miniaturas enfileiradas ao fechar a janela.
- Seleções inválidas deixam de manter uma rotação temporária residual.
- Consulta de releases tem pool próprio, timeout e resposta limitada; falhas
  mantêm o aplicativo utilizável offline.

## Limitações conhecidas

- PDFs não são isolados em sandbox de processo; documentos maliciosos ou enormes
  podem consumir recursos. Encerramento forçado pode deixar temporários.
- Saídas modificadas podem invalidar assinaturas digitais. Compressão detecta
  assinaturas para aviso, sem validar certificados.
- Distribuição Windows sem assinatura digital. Outros sistemas e equipamentos
  precisam de validação própria; não se promete ausência de alertas de antivírus.
- Checker não instala atualizações; proxies autenticados não são suportados.
  GitHub pode limitar consultas. DNS/certificados dependem do sistema operacional.
- Desinstalação preserva documentos e a configuração local de atualizações.

## Próximas melhorias planejadas

Validar acessibilidade e mais ambientes Windows, ampliar documentação de PDFs
incomuns e estudar assinatura de distribuição. Atualização silenciosa, serviços
residentes, telemetria e processamento remoto não integram esta versão.
