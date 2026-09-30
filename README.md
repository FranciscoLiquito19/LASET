# LASET

Relatório de Laboratório de Sistemas Autónomos: **Sistema de Escrita/Leitura Multi-Protocolo**, com I2C, RS232, RS485, CAN e Ethernet.

Autores: Francisco Liquito e Pedro Ribeiro. Ano letivo: 2026/2027.

## Compilar

O relatório migrado usa o template oficial em `template_laset/Modelo_LaSET.tex`.
Instalar uma distribuição LaTeX com os pacotes usados nesse ficheiro, além de
`latexmk` e BibTeX. A bibliografia mantém o estilo `unsrt` do template.

```sh
cd template_laset
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error Modelo_LaSET.tex
```

O PDF é gerado em `template_laset/Modelo_LaSET.pdf` (caminho relativo à raiz do
repositório). O `latexmk` executa pdfLaTeX, BibTeX e as passagens necessárias
para resolver as citações e os índices.

A fase de Análise de Requisitos está configurada em
`template_laset/Outros/Identificacao.tex`: `\Requisitostrue`, `\Projectofalse`
e `\Finalfalse`. Inclui Introdução, Estado da Arte, Análise de Requisitos e
Arquitectura de Alto Nível. A inclusão do anexo segue o comportamento original
do template; o esquema elétrico ainda não tem conteúdo.

A versão anterior permanece em `main.tex`, `sections/` e `references/`, sem
alterações. Para a compilar a partir da raiz, continua disponível
`latexmk -pdf -outdir=build main.tex`, com `biblatex`/Biber e estilo IEEE.

## Estrutura

- `template_laset/Modelo_LaSET.tex`: ficheiro principal do relatório migrado.
- `template_laset/Capitulos/`: conteúdo organizado pelos capítulos oficiais.
- `template_laset/Outros/Identificacao.tex`: fase, título e autores.
- `template_laset/bibliografia.bib`: referências migradas para BibTeX.
- `main.tex`, `sections/` e `references/`: versão anterior preservada.

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
