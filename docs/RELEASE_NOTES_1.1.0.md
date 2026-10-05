# SigiloPDF 1.1.0

Esta versão melhora a manipulação visual das páginas e acrescenta compressão
local e uma forma opcional de consultar novas versões do aplicativo.

## O que mudou

- Miniaturas compartilhadas, seleção por clique, Ctrl/Shift e campos de intervalos.
- Visualização ampliada com navegação, zoom e ajuste à janela.
- Organização por arraste de páginas ou grupos, setas laterais, início/fim e desfazer.
- Divisão por pontos após páginas, além dos quatro modos anteriores.
- Preview da rotação antes de salvar; seleção visual em exportação e numeração.
- Compressão com comparação de tamanho antes de salvar uma nova cópia.
- Sobre mais discreto em Ajuda e versão centralizada no código e nos pacotes.
- Correções de troca rápida de arquivos e fechamento com miniaturas pendentes.

## Pré-visualização

As miniaturas são geradas progressivamente no computador. Duplo clique amplia
a página; use as setas para navegar e os controles de zoom. Os campos de páginas
continuam disponíveis e a extração preserva a ordem digitada. As imagens de
preview não são usadas para reconstruir os PDFs salvos.

## Organização de páginas

Arraste uma página ou um conjunto selecionado para a posição desejada. As setas
movem uma posição; os botões início/fim movem o conjunto. Alt+←/→ e Ctrl+Z também
estão disponíveis. A numeração visual distingue posição atual e página original.
Salvar usa exatamente essa ordem e mantém o arquivo original.

## Compressão

Há modos Leve, Equilibrada, Forte e Tamanho desejado. O aplicativo otimiza a
estrutura e, quando adequado, as imagens, sem transformar páginas inteiras em
imagens. Compare o resultado antes de salvar. A meta pode não ser alcançada;
modos mais fortes podem reduzir a qualidade das imagens. Consulte
[limitações da compressão](COMPRESSAO.md).

## Atualizações

O SigiloPDF agora pode verificar se existe uma versão nova disponível. Essa
consulta acessa apenas as releases públicas do projeto no GitHub e não envia
seus documentos. Em Ajuda → Verificar atualizações, consulte manualmente ou
habilite a verificação automática, inicialmente desativada. Há no máximo uma
tentativa automática a cada 24 horas. A opção pode ser desativada na mesma tela.
Baixar atualização abre a release oficial após seu clique; não instala nem
substitui o executável em uso. O aplicativo continua funcionando sem internet.

## Privacidade

O processamento dos PDFs continua sendo feito localmente. Não há upload,
telemetria, analytics, conta ou histórico de documentos. A configuração do
checker contém somente preferência, última tentativa e última versão observada.
Veja [Privacidade](PRIVACIDADE.md) e [Status](STATUS_DO_PROJETO.md).

## Download

- **Instalador:** `SigiloPDF-1.1.0-windows-x64-setup.exe`. Instala por usuário,
  permite escolher a pasta e inclui desinstalação. Atalho na área de trabalho é opcional.
- **Portátil:** `SigiloPDF-1.1.0-windows-x64-portable.zip`. Extraia a pasta inteira
  e abra `SigiloPDF.exe`; mantenha `_internal` junto dele. Não exige Python.
- **SHA256SUMS.txt:** hashes dos pacotes e fontes correspondentes.

A distribuição completa segue AGPL-3.0 e inclui fontes da aplicação e das
dependências; o código próprio permanece também sob MIT. Pacotes não possuem
assinatura digital. A desinstalação preserva PDFs e configurações locais.
Versões anteriores permanecem disponíveis no histórico de Releases.

## Validação

451 testes unitários, de integração e regressão foram aprovados antes do build.
O autoteste do binário Windows cobre abertura, informações, junção, organização,
miniaturas, ampliação, compressão, saída, Sobre e checker com respostas simuladas.
A consulta real de releases é verificada separadamente. Os limites e resultados
da revisão estão em [Status do projeto](STATUS_DO_PROJETO.md).
Portátil e instalador também passaram no Windows Sandbox sem Python e sem rede,
incluindo ferramentas, instalação em pasta escolhida, desinstalação e preservação
de um documento sintético. O executável foi validado no host com PATH restrito.

## Obrigado

Obrigado a quem vem testando o SigiloPDF e enviando sugestões. Várias das
melhorias desta versão vieram diretamente desse retorno.
