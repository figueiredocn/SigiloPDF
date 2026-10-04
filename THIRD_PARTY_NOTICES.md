# Licenças de terceiros

A licença MIT em LICENSE cobre o código próprio do SigiloPDF. Ela não substitui as licenças das bibliotecas usadas pelo aplicativo.

- **PyMuPDF / MuPDF:** AGPL ou licença comercial da Artifex. A redistribuição de uma aplicação combinada com a versão AGPL deve observar suas condições; a licença MIT dos nossos arquivos não torna o conjunto distribuído exclusivamente MIT. Consulte a [documentação oficial](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright) e a licença fornecida com o pacote.
- **PySide6 / Qt:** opções LGPL, GPL e comercial, conforme componentes e modalidade. Consulte as [licenças do Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html) e os avisos incluídos nos pacotes.
- **pypdf:** BSD-3-Clause.
- **Pillow:** licença HPND, com avisos adicionais de bibliotecas incorporadas.
- **cryptography**, instalado pelo extra `pypdf[crypto]`: Apache-2.0 ou BSD-3-Clause; componentes incorporados têm avisos próprios.
- **pytest**, usado no desenvolvimento: MIT.

Os pacotes Windows incluem bibliotecas nas versões de `requirements-release.txt`. A distribuição completa segue AGPL-3.0, conforme [DISTRIBUTION_LICENSE.md](DISTRIBUTION_LICENSE.md), mantendo a MIT do código próprio. Os avisos integrais ficam em `_internal/licencas`, e as fontes correspondentes são disponibilizadas na mesma release. Consulte [fontes e reconstrução](docs/FONTES_CORRESPONDENTES.md).

Bibliotecas nativas incorporadas incluem os codecs do Pillow, componentes de MuPDF e Qt, OpenSSL e runtime do Python. Os manifests de fontes registram versões, origem e SHA-256. DLLs de runtime Microsoft Visual C++ preservam os direitos da Microsoft e são componentes de sistema redistribuídos pelos fornecedores. O pacote não altera esses binários nem suas licenças.
