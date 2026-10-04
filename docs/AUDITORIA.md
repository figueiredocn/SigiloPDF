# Auditoria inicial de 4 de outubro de 2026

Registro histórico das seis primeiras ferramentas. As contagens e limitações abaixo
correspondem àquela etapa; para a publicação 1.0.0, veja [auditoria de publicação](AUDITORIA_PUBLICACAO.md).

Escopo: Informações do PDF, Juntar PDFs, Dividir PDF, Extrair páginas, Remover
páginas e Girar páginas. Nenhuma ferramenta nova foi implementada.

## Problemas confirmados e corrigidos

- A janela fechava com workers ativos. Agora aguarda o término sem bloquear o
  loop de eventos, bloqueia novas entradas e fecha automaticamente depois.
- Caminhos de fluxos alternativos NTFS eram aceitos e podiam gravar dados dentro
  de um documento existente. Todos os fluxos são recusados, assim como nomes
  reservados de dispositivos. Caminhos locais estendidos do Windows são aceitos.
- A normalização de caminhos estava repetida nos cores. Foi consolidada sem
  modificar o comportamento das ferramentas ou criar outro parser.
- A tela de rotação impunha altura mínima de 843 pixels à janela. As páginas
  agora têm rolagem, mantendo controles acessíveis em telas menores.
- A mensagem de seleção vazia mencionava extração em ferramentas de remoção e
  rotação. Foi substituída por uma mensagem neutra em pt-BR.
- O status de informações usava interpretação automática de texto rico. Agora
  usa texto simples, como as demais telas que apresentam dados e mensagens.
- Pillow era uma dependência obrigatória sem uso nas seis ferramentas. Foi
  movido para o extra opcional `images` e retirado de `requirements.txt`.

## Verificação

- Suíte completa: 173 testes aprovados no Windows, sem falhas ou testes ignorados.
- Os testes novos verificam fechamento com workers nas seis ferramentas, thread
  gráfica dos sinais, rolagem, caminhos estendidos, dispositivos e fluxos NTFS.
- Existe somente um parser de páginas, reutilizado pelas ferramentas.
- Widgets são atualizados por slots na thread gráfica; workers chamam serviços.
- Não foram encontradas chamadas externas de rede ou telemetria no código.
- Arquivos existentes continuam protegidos por criação exclusiva (`xb`).
- Testes existentes verificam preservação dos originais e limpeza após falhas
  normais de geração/gravação, inclusive conflitos que surgem durante a operação.
- Importações, instalação local editável e dependências foram verificadas.
- As seis ferramentas foram validadas na janela nativa do Windows, incluindo
  fechamento durante operações. A altura mínima passou de 843 para 530 pixels.
- A verificação do processo Qt não detectou conexões TCP ou endpoints UDP naquele
  momento; a revisão de código também não identificou chamadas de rede.

## Limitações conhecidas

- Edição de PDFs criptografados permanece recusada nesta versão.
- Uma chamada demorada da biblioteca não é interrompida à força: fechar a janela
  aguarda a operação. Não há isolamento de processo ou limite de memória/CPU.
- Interrupção forçada, queda de energia ou impedimento do sistema operacional
  podem deixar temporários ou saídas parciais. A limpeza nesses casos é de melhor
  esforço e não pode ser garantida pelo aplicativo.
- Novas versões não preservam a validade de assinaturas digitais originais.
- Restam trechos semelhantes de orquestração e tratamento de erros específicos;
  não foi feita uma refatoração ampla sem benefício funcional demonstrado.
