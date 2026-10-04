# SigiloPDF

**Seus documentos. Seu computador. Seu controle.**

SigiloPDF é um aplicativo desktop open source para trabalhar com arquivos PDF localmente. Ele reúne tarefas comuns como juntar, dividir, reorganizar, converter e proteger documentos sem exigir o envio dos arquivos para serviços online.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![Licença MIT](https://img.shields.io/badge/licença-MIT-green)
![Validado no Windows](https://img.shields.io/badge/plataforma-Windows-blue)

## Por que este projeto existe?

Juntar páginas de um contrato ou reorganizar um relatório parece uma tarefa pequena. Ainda assim, muitas ferramentas pedem que você envie o documento para um serviço online.

Criei o SigiloPDF para poder fazer esse trabalho diretamente no computador, inclusive com arquivos que prefiro não compartilhar com terceiros.

## Privacidade

Os documentos são processados localmente pelo aplicativo. Não há upload, conta, telemetria, analytics ou armazenamento remoto de PDFs. Senhas informadas não são gravadas em arquivos, logs ou configurações; são usadas em memória durante a operação.

O SigiloPDF reduz a necessidade de entregar documentos a serviços externos, mas não substitui boas práticas de segurança no computador. Pastas sincronizadas podem enviar arquivos por ação de outros programas. Consulte a [política de privacidade](docs/PRIVACIDADE.md).

## O que já dá para fazer

- Juntar PDFs, dividir documentos e extrair páginas.
- Remover, girar e reorganizar páginas visualmente.
- Converter imagens em PDF e páginas de PDF em imagens.
- Numerar páginas.
- Consultar informações técnicas, visualizar e editar metadados e remover metadados comuns.
- Proteger PDFs com senha e remover a proteção com a senha correta.

As operações criam novas saídas e preservam os originais. Nomes em conflito recebem um sufixo. A remoção de metadados comuns não elimina todas as possíveis informações identificadoras de um documento.

## Interface

As capturas abaixo foram feitas no aplicativo, com documentos de demonstração.

![Tela inicial](assets/screenshots/home.png)

<details>
<summary>Organização de páginas, junção e privacidade</summary>

![Organizar páginas](assets/screenshots/organizar.png)
![Juntar PDFs](assets/screenshots/juntar.png)
![Informações sobre processamento local](assets/screenshots/privacidade.png)

</details>

## Executando pelo código-fonte

Instale Python 3.11 ou superior e Git. No PowerShell do Windows:

```powershell
git clone https://github.com/figueiredocn/SigiloPDF.git
cd SigiloPDF
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install --no-deps -e .
.venv\Scripts\python.exe -m app.main
```

A instalação das dependências precisa de acesso à internet. O processamento de documentos funciona offline. A validação desta versão foi feita no Windows; outros sistemas ainda precisam de validação própria.

Para executar os testes:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Download

Os executáveis serão disponibilizados na página de [Releases](https://github.com/figueiredocn/SigiloPDF/releases). Esta primeira publicação distribui o código-fonte; ainda não há instalador ou executável oficial.

## Documentação e contribuições

Consulte a [arquitetura](docs/ARQUITETURA.md), as [limitações de segurança](docs/SEGURANCA.md), o [roadmap](docs/ROADMAP.md) e o [guia de contribuição](CONTRIBUTING.md). Para relatar vulnerabilidades, leia [SECURITY.md](SECURITY.md).

O código do projeto usa a [licença MIT](LICENSE). As dependências têm licenças próprias, incluindo condições relevantes para redistribuição: veja [avisos de terceiros](THIRD_PARTY_NOTICES.md).

## Autor

Criado e mantido por Felipe Figueiredo.

Este projeto surgiu como uma iniciativa pessoal para disponibilizar uma alternativa simples e aberta para tarefas comuns com documentos PDF.
