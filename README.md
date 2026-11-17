# LASET

Relatório de Laboratório de Sistemas Autónomos: **Sistema de Escrita/Leitura Multi-Protocolo**, com I2C, RS232, RS485, CAN e Ethernet.

Autores: Francisco Liquito e Pedro Ribeiro. Ano letivo: 2026/2027.

## Compilar

O único relatório oficial tem como ficheiro principal
`template_laset/Modelo_LaSET.tex`.
Instalar uma distribuição LaTeX com os pacotes usados nesse ficheiro, além de
`latexmk` e BibTeX. A bibliografia mantém o estilo `unsrt` do template.
Os diagramas vetoriais são compilados diretamente com TikZ/PGF, usando
os estilos comuns de `template_laset/Outros/Estilo_Visual.tex`.

```sh
cd template_laset
mkdir -p build
latexmk -pdf \
  -outdir=build \
  -interaction=nonstopmode \
  -halt-on-error \
  -file-line-error \
  Modelo_LaSET.tex
```

O PDF é gerado em `template_laset/build/Modelo_LaSET.pdf` (caminho relativo à raiz do
repositório). O `latexmk` executa pdfLaTeX, BibTeX e as passagens necessárias
para resolver as citações e os índices.

No VS Code, a receita existente do LaTeX Workshop usa
`"latex-workshop.latex.outDir": "%DIR%/build"` e passa esse diretório ao
`latexmk` através de `-outdir=%OUTDIR%`. Ao compilar o ficheiro principal,
o resultado fica no mesmo caminho indicado acima. O PDF oficial é versionado;
os ficheiros auxiliares de compilação em `build/` são ignorados pelo Git.

A fase de Análise de Requisitos está configurada em
`template_laset/Outros/Identificacao.tex`: `\Requisitostrue`, `\Projectofalse`
e `\Finalfalse`. Inclui Introdução, Estado da Arte, Análise de Requisitos e
Arquitetura de Alto Nível. O ficheiro `Anexos/AnexoA.tex` está reservado para
o esquema elétrico da fase de projeto/final e contém apenas comentários,
pelo que não gera um capítulo vazio nesta fase.

## Estrutura

- `template_laset/Modelo_LaSET.tex`: ficheiro principal do único relatório oficial.
- `template_laset/Capitulos/`: conteúdo organizado pelos capítulos oficiais.
- `template_laset/Outros/Identificacao.tex`: fase, título e autores.
- `template_laset/Figuras/`: imagens utilizadas no relatório.
- `template_laset/Figuras/diagramas/`: fontes TikZ dos esquemas e gráficos temporais.
- `template_laset/Anexos/`: conteúdo dos anexos.
- `template_laset/bibliografia.bib`: referências bibliográficas em BibTeX.
- `template_laset/build/`: PDF oficial versionado e auxiliares de compilação ignorados pelo Git.
- `.vscode/settings.json`: configuração de compilação do LaTeX Workshop.

As [notas da revisão](docs/revisao_final.md) incluem os resultados de
validação e um roteiro para leitura conjunta do PDF.

## Apresentação e guião

- [PowerPoint atualizado](apresentacao/output/Apresentacao_LaSET_Integracao_Robotica_Revista.pptx): 10 slides centrados na integração de equipamentos em sistemas robóticos, com fundamentos, estado da arte, casos de utilização, requisitos, arquitetura e verificação prevista.
- [Guião em PDF](apresentacao/output/Guiao_Apresentacao.pdf) e [fonte editável](apresentacao/Guiao_Apresentacao.md): divisão entre Pedro e Francisco Liquito, falas, tempos e perguntas de preparação.

RF17 distingue os quatro pares mínimos obrigatórios com Ethernet dos
percursos adicionais que podem ser definidos e implementados em projeto.
Os critérios de ensaio abrangem todos os percursos efetivamente definidos.

A versão de 29 de outubro acompanha um cenário ilustrativo com motor,
bateria e sensor. A reutilização em diferentes sistemas é um objetivo;
funcionamento em óleo e sob pressão permanece uma possibilidade futura,
com condições e validação por definir. O guião acompanha esta versão,
com Pedro nos slides 1 a 5 e Francisco Liquito nos slides 6 a 10,
numa duração de ensaio de cerca de nove minutos.

## Trabalhar em conjunto

Após receber acesso ao repositório, clonar o projeto:

```sh
git clone https://github.com/FranciscoLiquito19/LASET.git
cd LASET
```

Antes de começar uma alteração, atualizar a cópia local e criar um ramo:

```sh
git pull --ff-only
git switch -c descricao-da-alteracao
```

Depois de editar e compilar, guardar apenas os ficheiros pretendidos e publicar o ramo:

```sh
git add template_laset/ README.md
git commit -m "Descrever a alteração"
git push -u origin descricao-da-alteracao
```

No GitHub, abrir um pull request para rever e integrar a alteração no ramo principal. Usar um nome diferente para cada novo ramo.
