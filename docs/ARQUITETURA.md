# Arquitetura

Fluxo obrigatório: **UI → services → core**.

`app/main.py` configura o Qt e abre `MainWindow`. A UI apresenta cards e uma
página de informações. `PdfInfoPage` envia o caminho selecionado para
`PdfInfoWorker`, que chama `PdfInfoService.inspect`. O serviço chama
`read_pdf_info` do core. Um resultado imutável retorna por sinal para a UI.

O core contém o modelo `PdfInfo`, validação e leitura com pypdf. Não depende
de PySide6. O arquivo é aberto em modo binário somente leitura e fechado após
a consulta. Metadados são tratados como dados, sem execução de conteúdo.

Workers usam `QThreadPool` e sinais com receptores na thread gráfica. Durante
uma consulta, a página desabilita novas entradas, mas a janela continua responsiva.
O pool global mantém a tarefa viva mesmo ao navegar para a página inicial.

`ui/components` contém a área de arraste, `ui/styles` contém QSS distribuído com
o pacote, `utils` reserva utilitários futuros e `assets` reserva recursos visuais.
Pillow é dependência obrigatória para leitura e normalização de imagens. Testes abrangem core, serviço, arquitetura e UI.

A janela adia o fechamento enquanto houver workers ou tarefas no pool em execução,
mantendo o loop de eventos ativo para receber resultados. Durante esse encerramento,
novas entradas ficam bloqueadas. Após o término, a janela fecha automaticamente.
As páginas possuem rolagem para preservar o acesso aos controles em telas menores.
A validação de caminhos locais é compartilhada por todas as ferramentas.

Juntar PDFs usa `MergePdfPage` → workers → `MergePdfService` → core. A inspeção
dos arquivos e a junção são tarefas separadas, ambas em segundo plano. O core
preserva a ordem das páginas, usa a mesma validação de caminhos locais e cria
um temporário na pasta escolhida. Depois da geração, copia para um destino
aberto exclusivamente com `xb`; arquivos existentes nunca são substituídos,
inclusive em conflitos que surjam durante a operação. Falhas de gravação tentam
remover a saída parcial e o temporário. A UI recebe progresso por sinais.

Dividir PDF segue `SplitPdfPage` → workers → `SplitPdfService` → core. O parser
`page_selection.py` interpreta números e intervalos, valida limites e retorna
páginas únicas em ordem crescente, sem Qt. `split_pdf.py` extrai as páginas e
`split_output.py` grava as saídas com modo exclusivo `xb`. Conflitos recebem
sufixos `_2`, `_3` etc., inclusive se outro processo criar o destino durante a
geração. Em caso de falha, a operação tenta remover somente as saídas que criou.
A inspeção e a divisão usam `QThreadPool` e sinais, sem bloquear a interface.

Extrair páginas usa `ExtractPdfPage` → workers → `ExtractPdfService` → core.
Reutiliza `parse_page_selection` com `preserve_order=True`: as páginas seguem
a ordem informada e as repetições são removidas. A divisão mantém o padrão de
ordem crescente. O serviço prepara o resumo antes da geração; o core revalida
a seleção no documento aberto. `extract_pdf.py` copia objetos de páginas com
pypdf, sem rasterização, e reutiliza `write_unique_pdf` para gravar com nomes
seguros. O arquivo original nunca é usado como destino.

Remover páginas usa `RemovePdfPage` → workers existentes de edição de páginas →
`RemovePdfService` → `remove_pdf.py`. A tela reaproveita seleção, arraste, destino
e progresso da extração, com resumo próprio. O core reutiliza o parser e a escrita
segura, valida que pelo menos uma página seja mantida e copia os objetos das
páginas restantes na ordem original. O resumo é revalidado no PDF aberto.

Girar páginas usa `RotatePdfPage` → workers existentes → `RotatePdfService` →
`rotate_pdf.py`. O serviço captura direção e aplicação em todas as páginas ou
seleção em uma configuração própria para cada worker. A seleção usa o parser
existente. O core copia todas as páginas e altera apenas `/Rotate` nas afetadas,
somando à orientação existente e normalizando módulo 360. Não rasteriza páginas
nem altera resolução. A escrita reutiliza os nomes seguros e temporários locais.

Organizar páginas usa `ReorderPdfPage` → `ReorderWorker` → `ReorderPdfService` →
core. `pdf_thumbnails.py` renderiza miniaturas RGB limitadas a 180 pixels com
PyMuPDF, em segundo plano. Somente a thread gráfica cria QPixmap e ícones.
`PageThumbnailList` mantém índices originais independentes da posição visual.
`reorder_pdf.py` valida uma permutação completa com índices a partir de zero e
copia objetos de páginas usando pypdf e a escrita segura compartilhada.
Miniaturas ficam somente em memória e são descartadas ao trocar o documento.
O fechamento cancela a renderização entre páginas e aguarda os workers;
a gravação em andamento termina antes do fechamento. Não há cancelamento
forçado de uma chamada individual da biblioteca.

Imagens para PDF usa `ImagesPdfPage` → `ImagesWorker` → `ImagesPdfService` →
`image_reader.py` e `images_to_pdf.py`. Inspeção, thumbnails e geração ocorrem
fora da thread gráfica. A UI cria somente ícones pequenos a partir de PNGs
retornados por sinais. JPEG usa `draft` antes da miniatura; PNG e BMP podem
precisar decodificar seus pixels, mas apenas a miniatura fica na UI.
O core aplica orientação EXIF, DPI válido (96 DPI na ausência), fundo branco
para transparência e uma matriz proporcional com recorte na área das margens.
JPEG RGB/cinza sem transformação EXIF é incorporado sem recompressão. Outras
imagens usam pixels normalizados e compressão sem perda. A escrita compartilha
`write_unique_pdf`; a ordem da lista é capturada antes de iniciar a geração.
O fechamento aguarda a operação e libera os ícones. Não há arquivos de thumbnails.
