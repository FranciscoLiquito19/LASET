# LASET

Relatório de Laboratório de Sistemas Autónomos: **Sistema de Escrita/Leitura Multi-Protocolo**, com I2C, RS232, RS485, CAN e Ethernet.

Autores: Francisco Liquito e Pedro Ribeiro. Ano letivo: 2026/2027.

## Compilar

Instalar uma distribuição LaTeX com os pacotes usados em `main.tex`, além de `latexmk` e `biber`. A bibliografia usa `biblatex` com estilo IEEE.

```sh
latexmk -pdf -outdir=build main.tex
```

O PDF é gerado em `build/main.pdf`. A pasta `build/` e os ficheiros temporários não são versionados.

## Estrutura

- `main.tex`: configuração, dados da capa e organização do relatório.
- `sections/`: conteúdo das secções.
- `references/referencias.bib`: referências bibliográficas.

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
git add main.tex sections/ references/
git commit -m "Descrever a alteração"
git push -u origin descricao-da-alteracao
```

No GitHub, abrir um pull request para rever e integrar a alteração no ramo principal. Usar um nome diferente para cada novo ramo.
