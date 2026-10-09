# LASET

Relatório de Laboratório de Sistemas Autónomos: **Sistema de Escrita/Leitura Multi-Protocolo**, com I2C, RS232, RS485, CAN e Ethernet.

Autores: Francisco Liquito e Pedro Ribeiro. Ano letivo: 2026/2027.

## Compilar

O único relatório oficial tem como ficheiro principal
`template_laset/Modelo_LaSET.tex`.
Instalar uma distribuição LaTeX com os pacotes usados nesse ficheiro, além de
`latexmk` e BibTeX. A bibliografia mantém o estilo `unsrt` do template.

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
o resultado fica no mesmo caminho indicado acima. O diretório `build/`
e os ficheiros auxiliares de compilação são ignorados pelo Git.

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
- `template_laset/Anexos/`: conteúdo dos anexos.
- `template_laset/bibliografia.bib`: referências bibliográficas em BibTeX.
- `template_laset/build/`: PDF e auxiliares gerados localmente, não versionados.
- `.vscode/settings.json`: configuração de compilação do LaTeX Workshop.

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
