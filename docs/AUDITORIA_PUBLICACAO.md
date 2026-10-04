# Auditoria da publicação 1.0.0

## Escopo

Preparação da primeira publicação do código-fonte, sem mudanças nas operações de PDF. A versão do pacote e o valor de fallback da tela Sobre foram atualizados para 1.0.0.

## Verificações locais

- 360 testes aprovados, sem falhas ou testes ignorados.
- Janela principal aberta com o plugin nativo `windows`; fluxos de numeração, metadados, proteção e Sobre também validados na janela nativa.
- `pip check` não encontrou dependências quebradas.
- Índice Git revisado antes do primeiro commit: sem PDFs, ambiente virtual, caches, executáveis, builds, logs, temporários, credenciais ou caminhos pessoais identificados.
- Nenhum histórico Git anterior existia. O primeiro commit usa endereço noreply do GitHub.
- Revisão do código e testes de arquitetura não identificaram chamadas de rede ou telemetria no aplicativo.
- Quatro capturas reais geradas com documentos sintéticos, sem caminhos pessoais visíveis.
- Licenças de dependências documentadas separadamente da MIT do código próprio.

## Limites

Esta revisão não equivale a certificação de segurança. A publicação não inclui instalador ou executável. Outros sistemas operacionais ainda precisam de validação. Instalação de pacotes, GitHub e execução do workflow acessam a rede; essas etapas não processam documentos de usuários.

As limitações operacionais estão descritas em [SEGURANCA.md](SEGURANCA.md). Antes de distribuir binários, é necessário validar o pacote e atender às condições das licenças de terceiros.
