# Licenças de terceiros

A licença MIT em LICENSE cobre o código próprio do SigiloPDF. Ela não substitui as licenças das bibliotecas usadas pelo aplicativo.

- **PyMuPDF / MuPDF:** AGPL ou licença comercial da Artifex. A redistribuição de uma aplicação combinada com a versão AGPL deve observar suas condições; a licença MIT dos nossos arquivos não torna o conjunto distribuído exclusivamente MIT. Consulte a [documentação oficial](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright) e a licença fornecida com o pacote.
- **PySide6 / Qt:** opções LGPL, GPL e comercial, conforme componentes e modalidade. Consulte as [licenças do Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) e os avisos incluídos nos pacotes.
- **pypdf:** BSD-3-Clause.
- **Pillow:** licença HPND, com avisos adicionais de bibliotecas incorporadas.
- **cryptography**, instalado pelo extra `pypdf[crypto]`: Apache-2.0 ou BSD-3-Clause; componentes incorporados têm avisos próprios.
- **pytest**, usado no desenvolvimento: MIT.

Esta publicação contém o código-fonte do projeto, sem bibliotecas incorporadas ou executáveis. Antes de distribuir um instalador ou pacote que inclua dependências, reúna as licenças, avisos e fontes exigidos pelas versões efetivamente distribuídas e verifique as condições de cada componente.
