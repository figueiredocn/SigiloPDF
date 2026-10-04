# SigiloPDF 1.0.0

Esta é a primeira versão pública do SigiloPDF.

O projeto começou com uma necessidade simples: realizar tarefas comuns com PDFs sem enviar documentos pessoais ou profissionais para ferramentas online.

Esta versão reúne junção, divisão, extração, remoção, rotação e organização visual de páginas; conversão entre imagens e PDF; numeração; consulta e edição de metadados; e proteção por senha. A remoção da proteção exige a senha correta.

Os documentos são processados localmente. As operações criam novas saídas e preservam os originais. A interface está em português do Brasil.

Os arquivos para Windows x64 estão disponíveis nos anexos desta release:

- **Instalador:** `SigiloPDF-1.0.0-windows-x64-setup.exe`, com instalação por usuário.
- **Portátil:** `SigiloPDF-1.0.0-windows-x64-portable.zip`. Extraia a pasta inteira e abra `SigiloPDF.exe`; mantenha `_internal` junto do executável.
- **Integridade:** `SHA256SUMS.txt`, com os hashes dos quatro pacotes.
- **Fontes da aplicação:** `SigiloPDF-1.0.0-fontes-aplicacao.zip`, com a revisão exata, recursos, testes e scripts de compilação.
- **Fontes das dependências:** `SigiloPDF-1.0.0-fontes-dependencias.zip`, com 71 arquivos de fontes e seus manifests de versões e hashes.

Requer Windows 10 2004 ou superior, x64. Não exige Python instalado. Os pacotes não possuem assinatura digital.

A distribuição com dependências segue AGPL-3.0. O código próprio permanece também sob MIT. As licenças completas e avisos de terceiros acompanham o aplicativo. Consulte `DISTRIBUTION_LICENSE.md`, `THIRD_PARTY_NOTICES.md` e `docs/FONTES_CORRESPONDENTES.md` no ZIP de fontes da aplicação.

Foram aprovados 360 testes no ambiente de desenvolvimento. Os artefatos finais abriram no Windows e passaram pelo Windows Sandbox sem Python pré-instalado e sem rede: abertura portátil, instalação, abertura instalada e desinstalação. A suíte funcional foi executada pelo código-fonte, não dentro do executável congelado.

O tag original `v1.0.0` preserva a primeira publicação do código. Para reconstruir estes binários, use o ZIP de fontes da aplicação anexado, que registra sua revisão em `SOURCE_REVISION.txt`; os arquivos automáticos “Source code” do GitHub correspondem ao tag original.

Se encontrar algum problema, abra uma issue usando documentos sintéticos. Vulnerabilidades devem seguir o canal privado descrito em SECURITY.md. Ideias que melhorem o projeto mantendo sua proposta de privacidade são bem-vindas.
