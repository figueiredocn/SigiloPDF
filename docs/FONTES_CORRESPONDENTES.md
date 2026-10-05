# Fontes correspondentes dos pacotes Windows 1.1.0

A release fornece dois arquivos adicionais aos binários:

- `SigiloPDF-1.1.0-fontes-aplicacao.zip`: código próprio, recursos, testes,
  scripts de build, instalador e documentação da revisão usada no pacote.
- `SigiloPDF-1.1.0-fontes-dependencias.zip`: fontes de terceiros, arquivos de
  versões e checksums e receitas originais de compilação dos fornecedores.

O código próprio permanece também sob MIT. A distribuição completa segue AGPL-3.0,
conforme [DISTRIBUTION_LICENSE.md](../DISTRIBUTION_LICENSE.md). Os arquivos de fontes
são oferecidos gratuitamente na mesma página dos binários e não exigem cadastro.

## Conteúdo

Os manifests `SOURCE_LOCK.json`, `VENDOR_SOURCE_LOCK.json` e
`EXTRA_SOURCE_LOCK.json` identificam cada arquivo, versão, URL de origem,
tamanho e SHA-256. Eles cobrem Qt 6.11.2 (qtbase, qtsvg, qtimageformats e
qttranslations), PySide6/Shiboken 6.11.2, PyMuPDF e MuPDF 1.28.2, CPython 3.14.6,
Pillow e codecs nativos, pypdf, cryptography e seus crates Rust, OpenSSL, cffi,
pycparser e fontes do bootloader PyInstaller. MuPDF e Qt incluem as fontes
e avisos de terceiros vendorizados em suas árvores.

O pacote Widgets não inclui QtPdf, QtQuick, QtQml ou teclado virtual. Os plugins
opcionais correspondentes foram excluídos; a manipulação de PDF usa as bibliotecas
já existentes. DLLs de runtime do Microsoft Visual C++ são componentes de sistema
redistribuídos pelos fornecedores; não são código próprio do SigiloPDF.

Não modificamos os fontes das bibliotecas. Os arquivos mantêm as receitas,
patches e avisos de seus fornecedores. Os manifests registram inclusive componentes
de build/transitivos para permitir a reconstrução. Ferramentas gerais como MSVC,
Windows SDK, CMake, Ninja, Rust, NASM e Inno Setup são instaladas separadamente.

## Reconstruir a aplicação

Use Windows x64, Python 3.14.6 e uma pasta nova. Extraia as fontes da aplicação:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-release.txt
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe packaging/collect_sources.py
.venv\Scripts\python.exe packaging/collect_vendor_sources.py
.venv\Scripts\python.exe packaging/collect_extra_sources.py
.\scripts\build_windows.ps1 -OutputDirectory dist\reconstrucao
```

Os coletores acessam a rede somente para baixar fontes públicos de build. Não são
importados pelo aplicativo. Para reutilizar as fontes da release, extraia o conteúdo
do ZIP de dependências em `build/corresponding-sources`; os coletores verificam
e reutilizam os arquivos. A instalação de wheels acima é o procedimento usado
para empacotar a aplicação. Não promete um binário idêntico byte a byte.

## Reconstruir as bibliotecas

Para substituir as wheels por bibliotecas compiladas a partir das fontes:

- **Qt:** use o terminal x64 do MSVC com CMake e Ninja. Compile `qtbase` com
  `configure.bat -opensource -confirm-license -release -shared -nomake tests
  -nomake examples -prefix C:\QtLocal`; depois `cmake --build .` e
  `cmake --install .`. Configure os módulos svg e imageformats com o `qt-configure-module.bat`
  dessa instalação e compile/instale com CMake. As fontes de traduções são incluídas.
- **PySide6/Shiboken:** use `pyside-setup-everywhere-src-6.11.2` com MSVC,
  CMake/Ninja, Python e libclang compatível. A receita `setup.py` e as instruções
  de build estão nessa árvore. A opção `--qtpaths` deve apontar para a instalação
  de Qt acima. Gere a wheel e instale-a no ambiente que será empacotado.
- **PyMuPDF/MuPDF:** extraia a árvore completa de MuPDF e defina
  `PYMUPDF_SETUP_MUPDF_BUILD` para seu caminho. Instale/compile o sdist de
  PyMuPDF com `python -m pip install --no-binary :all: <pasta-pymupdf>`, usando
  MSVC e SWIG. `setup.py`, `pipcl.py` e os projetos/scripts de MuPDF estão incluídos.
- **cryptography:** use Rust e OpenSSL 4.0.3 compilado na mesma arquitetura;
  configure `OPENSSL_DIR`. O sdist inclui `src/rust/Cargo.lock`; os arquivos
  `.crate` correspondentes estão no ZIP. Use Cargo para vendorizar as versões
  do lockfile e instale o sdist. Os scripts e configurações de build do projeto
  original são preservados.
- **Pillow:** a árvore `Pillow-complete` inclui `.github/dependencies.json` e
  `winbuild/build_prepare.py`, com versões, patches e comandos de compilação
  dos codecs. As fontes nativas indicadas por essa receita estão no ZIP; aom,
  dav1d, libyuv e libwebp devem ser disponibilizados nos diretórios `ext` de
  libavif se a compilação precisar ocorrer offline. FreeType usa o subprojeto
  dlg incluído separadamente. Siga a receita x64 para gerar a wheel.
- **CPython:** use `PCbuild/build.bat -p x64` e as instruções de `PCbuild/readme.txt`.
  As fontes de bzip2, libffi, xz, zlib-ng, zstd e OpenSSL usadas pelo build estão
  incluídas; `get_externals.bat` registra as referências originais.
- **Demais pacotes:** seus sdists incluem `pyproject.toml` ou `setup.py`, fontes,
  licenças e configurações de compilação. Instale as wheels resultantes antes
  de executar o script de empacotamento.

Referências dos fornecedores: [Qt no Windows](https://doc.qt.io/qt-6/windows-building.html),
[Qt for Python](https://doc.qt.io/qtforpython-6/building_from_source/windows.html),
[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/installation.html) e
[cryptography](https://cryptography.io/en/latest/installation/).

Esta publicação recompila o aplicativo e valida seus pacotes, mas não recompila
todas as bibliotecas nativas a partir de suas fontes. Elas vêm das wheels oficiais
nas versões fixadas. A documentação e fontes permitem inspecionar e reconstruir
os componentes e modificar a aplicação.
