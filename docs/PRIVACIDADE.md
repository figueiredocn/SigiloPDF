# Privacidade

**Seus arquivos são processados localmente.**

O SigiloPDF não possui telemetria, analytics, autenticação, serviços cloud,
backend remoto ou APIs externas de processamento. Todas as operações sobre documentos funcionam offline e não enviam documentos,
metadados, caminhos ou conteúdo a servidores. A única consulta de rede do
aplicativo é a verificação opcional de releases públicas descrita abaixo.

Informações consultadas permanecem na memória da aplicação e na tela. A ferramenta
de informações não escreve PDFs, relatórios, histórico ou logs de documentos.
Juntar PDFs grava somente a saída escolhida e um arquivo temporário local na mesma
pasta, removido ao concluir a operação quando o sistema permite. Não altera os
originais. Dividir PDF também grava somente na pasta local escolhida, usando
temporários locais e preservando o original e arquivos já existentes. Não há
processamento remoto na extração: somente o PDF de saída e os temporários na pasta de
destino são gravados. O resumo e a seleção permanecem em memória. Não há
envio de dados. Avisos do parser que podem conter trechos de documentos não são
encaminhados ao console.
Remover páginas também processa localmente e grava apenas uma nova saída e os
temporários na pasta escolhida. Não modifica o original nem transmite conteúdo.
Girar páginas segue a mesma política: processamento local, resumo em memória
e saída nova, sem envio de documentos ou informações.
Caminhos UNC e unidades de rede do Windows são recusados antes da leitura. O seletor
de arquivos usa Qt com textos em pt-BR; pastas sincronizadas escolhidas pelo
usuário podem ter sincronização externa independente do aplicativo.

A instalação de dependências acessa o repositório de pacotes. Esse passo não
processa documentos. Depois de instalado, o aplicativo funciona offline.

Organizar páginas renderiza miniaturas localmente com PyMuPDF. O cache existe
somente na memória da janela; nenhum arquivo de miniatura é gravado. A saída
usa as páginas originais com pypdf e temporários locais removidos ao concluir,
quando o sistema permite. Não há chamadas de rede nem logs de documentos.

Imagens para PDF lê imagens somente de caminhos locais, mantém miniaturas em
memória e grava apenas o PDF de saída e seu temporário na pasta escolhida.
Não modifica as imagens originais, não registra conteúdo e não acessa a rede.
Arquivos existentes recebem nomes com sufixo; não são substituídos.

Numeração, metadados e proteção por senha também são exclusivamente locais.
Não há upload, telemetria, analytics ou armazenamento remoto. Nenhuma senha
é armazenada em arquivos, logs, configurações, histórico ou banco de dados.
A senha permanece apenas temporariamente na memória necessária à operação;
os campos são limpos ao iniciá-la e referências do serviço são liberadas ao
concluir ou falhar. O temporário de proteção já contém o PDF criptografado,
nunca uma senha em texto claro. Python/Qt não garantem sobrescrita de toda a
memória utilizada por strings; não há promessa de apagamento forense da RAM.

A remoção de metadados elimina Info e XMP comuns do catálogo e das páginas,
sem alterar o conteúdo visual. Não garante anonimização completa: textos,
anexos, anotações e outros dados internos podem identificar pessoas ou origem.

Comprimir PDF também é exclusivamente local. Os candidatos ficam no diretório
temporário do sistema e são limpos após erro, cancelamento, troca de entrada/opções
ou fechamento normal. O melhor candidato permanece até salvar ou descartar a
comparação. Metadados e criptografia são preservados; senhas ficam somente em
memória durante inspeção/compressão. Nenhum conteúdo ou tamanho é enviado pela
ferramenta. Veja [Compressão](COMPRESSAO.md).

As miniaturas e a visualização ampliada são geradas localmente, somente em
memória, sem salvar imagens temporárias. O cache de ícones é limitado a 64 MiB
por painel e cada imagem ampliada a aproximadamente quatro milhões de pixels.
A troca de arquivo invalida resultados antigos; o fechamento cancela prévias
e aguarda a liberação dos workers.

Em Ajuda → Sobre, o botão Repositório abre uma URL fixa do projeto no navegador
somente após uma ação explícita. O navegador pode acessar o GitHub; o SigiloPDF
não envia conteúdo, caminho, senha ou contexto de documentos nessa ação.

## Verificação opcional de versões

A partir da versão 1.1.0, Ajuda → Verificar atualizações pode consultar
`https://api.github.com/repos/figueiredocn/SigiloPDF/releases/latest`. A consulta
automática vem desativada. Ao habilitá-la, ocorre no máximo uma tentativa a cada
24 horas, inclusive se houver falha; a consulta manual depende de seu clique.
É um GET com Accept e User-Agent genérico SigiloPDF, sem autenticação, cookies,
identificador exclusivo, versão de Windows ou contexto de uso/documentos.
O GitHub recebe os dados normais necessários à conexão HTTPS, como o IP.

São armazenados localmente apenas preferência, instante da última tentativa
e última versão pública observada. A configuração fica em
`%LOCALAPPDATA%/SigiloPDF/update_preferences.json` no Windows; não contém
histórico, nomes, caminhos ou senhas de documentos. Pode ser desativada na mesma
tela. Falhas não impedem usar as ferramentas offline. Baixar atualização abre
a página oficial somente após clique, sem download ou instalação automática.
