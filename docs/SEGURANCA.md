# Segurança

O aplicativo lê o PDF localmente sem executar JavaScript, abrir links ou anexos.
Ele não modifica os documentos originais nem persiste senhas ou histórico.
Criptografia é indicada mesmo quando uma senha vazia permite leitura.
Nas ferramentas gerais, se uma senha for necessária, o conteúdo protegido permanece indisponível. A ferramenta Proteger PDF permite remover proteção mediante senha correta.
Juntar PDFs e Dividir PDF recusam arquivos criptografados, inclusive os com senha
vazia, para não remover sua proteção. A saída deve ser um arquivo novo; não há
substituição.
A geração usa um temporário local, com limpeza ao terminar. Se o sistema impedir
a limpeza ou o processo for interrompido abruptamente, poderá restar um temporário
`.sigilopdf-*.tmp` ou uma saída incompleta na pasta escolhida.
Na divisão, conflitos de nomes recebem sufixos sem substituir arquivos. Falhas
tentam desfazer apenas os arquivos criados pela operação; se o sistema impedir
a limpeza, poderá restar uma saída parcial na pasta escolhida.
Extrair páginas também recusa PDFs criptografados, preserva os objetos de páginas
sem rasterização e cria uma saída nova. O original não pode ser escolhido como
destino. Arquivos existentes recebem sufixos numéricos, com a mesma escrita
exclusiva e limpeza de temporários usada na divisão.
Remover páginas exige que pelo menos uma página seja mantida. O original não
pode ser destino, PDFs criptografados são recusados e conflitos recebem nomes
seguros. A nova versão preserva os objetos de páginas suportados por pypdf,
sem rasterizar o conteúdo.
Girar páginas também recusa PDFs criptografados e impede o original como destino.
A orientação é alterada nos objetos de página sem gerar imagens. Conflitos de
nomes recebem sufixos, e falhas tentam remover apenas a saída criada pela operação.

No Windows, fluxos alternativos do NTFS (caminhos com `:` após a unidade) e nomes
de dispositivos reservados são recusados. Caminhos locais estendidos `\\?\C:\`
são aceitos; compartilhamentos de rede continuam bloqueados.

PDFs são entradas não confiáveis. Um arquivo danificado recebe mensagem amigável;
formatos incomuns podem não ser suportados. A leitura em thread mantém a interface
responsiva, mas não constitui isolamento de processo: PDFs enormes ou maliciosos
podem consumir memória e CPU. Não existe sandbox nem limite global de recursos nesta base.
Mantenha Python e dependências atualizados ao distribuir o aplicativo.
Fechar a janela durante uma operação aguarda sua conclusão; não há interrupção
forçada de uma chamada em andamento da biblioteca PDF. Uma geração nova não
preserva a validade de assinaturas digitais do documento original.

Relate vulnerabilidades sem anexar documentos pessoais, caminhos reais ou senhas.
Use arquivos sintéticos e instruções de reprodução. Use o canal privado de vulnerabilidades habilitado no GitHub, conforme
[SECURITY.md](../SECURITY.md); não publique detalhes sensíveis em issues abertas.

A proteção utiliza AES-256 (revisão 6 do padrão PDF), implementada pela
biblioteca pypdf com o extra crypto já instalado. Não há criptografia própria,
descoberta automática de senha ou tentativa de quebra. A remoção exige senha
fornecida e validada pela biblioteca; a saída sem proteção é uma nova cópia.
Senha vazia ou confirmação divergente são recusadas na proteção. Não há
armazenamento de senhas, recuperação de senha ou registro em logs. Novas senhas
com mais de 127 bytes UTF-8 são recusadas para evitar truncamento silencioso.

Numeração acrescenta texto sem rasterização. Metadados editados permanecem
coerentes entre Info e XMP comum, e a limpeza descarta objetos sem referência.
A limpeza não remove dados pessoais do conteúdo, anexos ou anotações e não
constitui anonimização absoluta. Assinaturas digitais perdem validade ao criar
uma versão modificada. Temporários e saídas parciais são removidos quando o
sistema permite; falhas de energia, encerramento forçado ou permissões podem
impedir a limpeza. O fechamento normal aguarda os workers.
