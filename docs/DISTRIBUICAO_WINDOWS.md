# Distribuição para Windows

O pacote experimental utiliza PyInstaller em modo de pasta e Inno Setup 6.
As ferramentas de build não são dependências do aplicativo. Nenhuma delas
é usada para processar documentos de usuários.

## Gerar os pacotes

Use Windows 10 2004 ou superior, x64, com o ambiente virtual e as dependências
do projeto instaladas. Instale Inno Setup 6 e execute no PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_windows.ps1
```

O script executa os testes, reúne licenças e versões, gera o aplicativo,
audita o pacote, compila o instalador e cria o ZIP e os hashes SHA-256.
O build tem seu PATH restrito para evitar DLLs de outras ferramentas.
A pasta `dist` contém somente resultados locais e não deve ser adicionada ao Git.
O build recompõe a pasta gerada do aplicativo; não aponta para documentos.
O ZIP existente não é substituído automaticamente.

- Portátil: `dist/SigiloPDF/SigiloPDF.exe`, acompanhado da pasta `_internal`.
- Arquivo portátil: `dist/SigiloPDF-1.0.0-windows-x64-portable.zip`.
- Instalador: `dist/installer/SigiloPDF-1.0.0-windows-x64-setup.exe`.
- Verificação de integridade: `dist/SHA256SUMS.txt`.

O instalador usa a pasta de programas do usuário, sem exigir administrador.
Cria um atalho no menu Iniciar; o atalho na área de trabalho é opcional.
Não associa PDFs nem altera documentos. A desinstalação remove o programa,
sem procurar ou remover os PDFs produzidos pelo usuário.

## Validar

```powershell
.\scripts\validate_windows.ps1 -Executable .\dist\SigiloPDF\SigiloPDF.exe
.\scripts\prepare_sandbox.ps1
```

Abra `build/sandbox.wsb` com Windows Sandbox habilitado. A rede e o
compartilhamento da área de transferência ficam desativados. Apenas os pacotes
gerados entram na máquina isolada; documentos pessoais não são mapeados.
O resultado fica em `build/sandbox-reports/resultado.json`. A validação verifica
ausência de Python no PATH, abertura da versão portátil, instalação, abertura
da versão instalada e desinstalação. Não substitui o teste manual das ferramentas
com PDFs sintéticos, nem valida todas as versões de Windows.

## Antes de publicar

- Exigir aprovação nos testes e na validação dos artefatos finais.
- Reunir as fontes correspondentes e avisos das dependências realmente incluídas.
- Definir e documentar a distribuição combinada sob AGPL, ou obter a licença
  comercial aplicável ao PyMuPDF. A MIT dos arquivos próprios não resolve esta etapa.
- Atender também às condições LGPL/GPL do Qt e às demais licenças; as DLLs
  permanecem separadas para permitir substituição das bibliotecas.
- Anexar os arquivos, hashes e fontes exigidos à mesma release. Não publicar
  apenas um aviso de licença ou um link genérico como substituto das obrigações.
- Informar se o pacote não possui assinatura digital. Não orientar usuários a
  desativar o antivírus ou contornar bloqueios de segurança.

A distribuição Windows adota AGPL-3.0; o código próprio permanece também sob MIT.
Consulte [a licença de distribuição](../DISTRIBUTION_LICENSE.md), os
[avisos de terceiros](../THIRD_PARTY_NOTICES.md) e as
[fontes correspondentes](FONTES_CORRESPONDENTES.md). A release inclui os dois
ZIPs de fontes, além do instalador, portátil e hashes SHA-256.

## Validação local de 4 de outubro de 2026

- 360 testes aprovados no ambiente de desenvolvimento.
- Auditoria do pacote portátil aprovada, sem documentos ou caminhos pessoais
  identificados. O arquivo `direct_url.json` da instalação editável foi excluído.
- O executável abriu e fechou no host com PATH limitado às pastas do Windows.
- Windows Sandbox, sem Python pré-instalado e sem rede: portátil, instalação,
  abertura da versão instalada e desinstalação aprovados.
- A interface empacotada apresentou os doze cards, logotipo e textos em pt-BR.
- Instalador gerado com Inno Setup 6.7.3; pacotes sem assinatura digital.

Esses resultados cobrem inicialização e ciclo de instalação no Windows 10
validado. A suíte funcional de 360 testes foi executada pelo código-fonte;
não foi executada dentro do pacote congelado ou do Sandbox. As fontes de 71
arquivos de dependências foram reunidas e verificadas por SHA-256. Os avisos
e textos completos das licenças acompanham o pacote. A validação do Sandbox
foi repetida com os artefatos finais após a atualização das licenças.
