# Comprimir PDF — versão 1.1

Selecione ou arraste um PDF, escolha um modo, comprima, compare o resultado e
clique em **Salvar arquivo**. Nenhum documento é enviado para servidores.
A versão publicada 1.0 não inclui essa ferramenta; ela está no código-fonte.

## Modos

| Modo | DPI | Qualidade JPEG | Comportamento |
| --- | --- | --- | --- |
| Leve | 225 | 90 | Prioriza otimização sem perda; só recomprime imagens quando a primeira tentativa não reduz significativamente. |
| Equilibrada | 175 | 80 | Padrão; otimiza estrutura e imagens, preservando texto e vetores. |
| Forte | 125 | 65 | Reduz mais as imagens; pode diminuir a qualidade visual. |
| Tamanho desejado | 225 a 96 | 90 a 50 | Tenta atingir a meta progressivamente. |

Imagens abaixo da resolução escolhida não são ampliadas. Considera-se a maior
ocorrência do recurso; dimensões ambíguas usam limites conservadores. Uma imagem
só é substituída com ganho de pelo menos 1% e 1 KB em seu stream.

## Tamanho desejado

Aceita KB ou MB, inclusive decimais com vírgula. As unidades usam base 1024:
1 MB = 1.024 KB. O intervalo permitido vai de 50 KB até 10 GB.

A primeira tentativa otimiza apenas a estrutura. Cada tentativa seguinte parte
novamente do original, com os pares DPI/qualidade: 225/90, 200/85, 175/80,
150/72, 125/65 e 96/50. São no máximo sete tentativas; o processamento para ao
atingir a meta. Não há promessa de tamanho exato ou de encontrar o ótimo entre
todos os parâmetros possíveis.

Se a meta não puder ser atingida nesses limites, a tela informa o melhor
resultado e permite salvá-lo. A melhor saída nunca é maior que o original:
se nenhuma tentativa melhora o tamanho, conserva-se uma cópia exata do original.
Ganhos abaixo de 1% ou 1 KB são apresentados como não significativos.

## Preservação e segurança

PyMuPDF/MuPDF compacta streams, fontes e imagens sem perda na etapa estrutural,
remove objetos órfãos e deduplica objetos. Pillow redimensiona e codifica somente
imagens compatíveis em JPEG. Não há renderização da página para produzir a saída.
Texto selecionável, vetores, formulários, links, anotações, outlines, anexos e
metadados existentes são mantidos pela edição do documento completo.

Imagens com máscaras/transparência, Decode especial, cores incompatíveis ou mais
de 25 milhões de pixels não são recomprimidas. Perfis ICC RGB/cinza são mantidos.
Recursos inline e imagens sem ocorrência identificada permanecem intactos.
A análise por página identifica imagens que ocupam pelo menos 80% da área;
essa indicação não constitui classificação ou OCR.

PDFs protegidos exigem senha quando necessária. O campo segue o padrão mascarado
da ferramenta de proteção; a senha fica apenas em memória, é descartada após
o processamento e nunca é registrada. A criptografia original é mantida,
inclusive nos candidatos temporários. Não há remoção implícita de senha.

Campos e indicadores de assinatura detectados exigem ciência explícita antes
da execução. A detecção não valida certificados nem garante identificar todas
as assinaturas. Uma cópia modificada pode invalidar assinaturas digitais.

## Temporários e desempenho

UI → worker → service → core. Workers devolvem resultados por sinais e não
acessam widgets. O core não importa PySide6. Não há nova dependência ou motor
externo. O pool global executa uma tarefa por vez, evitando chamadas concorrentes
ao PyMuPDF, conforme a [restrição da biblioteca](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html).
Cancelamento ocorre entre recursos e etapas; uma chamada nativa em
andamento termina antes de liberar o worker. Fechar a janela cancela a compressão
e aguarda as tarefas, incluindo inspeção e salvamento.

Os candidatos ficam em um diretório temporário privado do sistema. Tentativas
descartadas são apagadas durante o processamento. Apenas o melhor resultado
permanece enquanto a comparação está aberta. Trocar arquivo/opções ou fechar
normalmente a aplicação remove esse resultado. Erros e cancelamento limpam
o diretório pelo mecanismo de contexto temporário.

Salvar exige destino explícito e reutiliza a escrita exclusiva compartilhada.
O original não pode ser escolhido como saída. Conflitos recebem `_2`, `_3` etc.
Falha de energia, encerramento forçado ou impedimento do sistema podem deixar
temporários; não há promessa de apagamento forense. A biblioteca mantém a
estrutura do documento em memória e não isola PDFs maliciosos/enormes por sandbox.
As imagens são otimizadas individualmente, sem acumular todas em Python.

## Validação no Windows

`python -m tests.smoke_compression` abre a janela com o plugin nativo do Qt,
gera PDFs sintéticos de aproximadamente 5, 20 e 50 MB, comprime em Equilibrada,
salva, reabre, renderiza uma página e verifica hashes dos originais e limpeza.
Os PDFs de teste não são adicionados ao repositório.

Na execução de 4 de outubro de 2026, o documento de 52.810.321 bytes (50,36 MB)
gerou 24.661.947 bytes (23,52 MB): redução de 53,3%, em 3,38 segundos.
A interface continuou recebendo eventos durante a compressão. Os tempos e
ganhos dependem do computador e do conteúdo; não constituem promessa para
outros documentos. O relatório local fica em `build/validacao-compressao.json`.
