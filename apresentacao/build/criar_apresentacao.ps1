$ErrorActionPreference = 'Stop'
$workspace = 'C:\Users\Pedro Ribeiro\LASET'
$build = Join-Path $workspace 'apresentacao\build'
$candidate = Join-Path $build 'candidato-v2.pptx'
$preview = Join-Path $build 'previews'
New-Item -ItemType Directory -Force -Path $preview | Out-Null

function Color([string]$Hex) {
    return [Convert]::ToInt32($Hex.Substring(0,2),16) + 256*[Convert]::ToInt32($Hex.Substring(2,2),16) + 65536*[Convert]::ToInt32($Hex.Substring(4,2),16)
}
$navy = Color '234D65'
$teal = Color '287D83'
$ink = Color '24343E'
$grey = Color '52646F'
$light = Color 'EDF3F6'
$rule = Color 'CFDADD'
$white = Color 'FFFFFF'
$optionalColor = Color '7B6B54'
$fit = [System.Collections.Generic.List[object]]::new()

function Text($Slide,[string]$Value,[single]$X,[single]$Y,[single]$W,[single]$H,[single]$Size=21,[int]$RGB=$ink,[bool]$Bold=$false,[int]$Align=1,[string]$Name='') {
    $shape = $Slide.Shapes.AddTextbox(1,$X,$Y,$W,$H)
    if ($Name) { $shape.Name=$Name }
    $shape.Fill.Visible=0
    $shape.Line.Visible=0
    $frame=$shape.TextFrame
    $frame.MarginLeft=0
    $frame.MarginRight=0
    $frame.MarginTop=0
    $frame.MarginBottom=0
    $frame.WordWrap=-1
    $frame.AutoSize=0
    $frame.VerticalAnchor=1
    $range=$frame.TextRange
    $range.Text=$Value
    $range.Font.Name='Arial'
    $range.Font.Size=$Size
    $range.Font.Color.RGB=$RGB
    $range.Font.Bold=0
    if ($Bold) { $range.Font.Bold=-1 }
    $range.ParagraphFormat.Alignment=$Align
    $range.ParagraphFormat.SpaceBefore=0
    $range.ParagraphFormat.SpaceAfter=0
    $range.ParagraphFormat.SpaceWithin=1.12
    $shape.Width=$W
    $shape.Height=$H
    return $shape
}

function New-Slide([string]$Title) {
    $slide=$presentation.Slides.Add($presentation.Slides.Count+1,12)
    $slide.FollowMasterBackground=0
    $slide.Background.Fill.Solid()
    $slide.Background.Fill.ForeColor.RGB=$white
    if ($Title) { [void](Text $slide $Title 48 36 864 72 32 $navy $true 1 'Título') }
    if ($presentation.Slides.Count -gt 1) {
        [void](Text $slide ([string]$presentation.Slides.Count) 911 510 30 20 12 $grey $false 3 'Número do slide')
    }
    return $slide
}

function Notes($Slide,[string]$Value) {
    $Slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text=$Value
}

function Native-Table($Slide,[object[]]$Rows,[single[]]$Widths,[single]$Y,[single[]]$Heights,[single]$FontSize=18) {
    $width=($Widths | Measure-Object -Sum).Sum
    $height=($Heights | Measure-Object -Sum).Sum
    $owner=$Slide.Shapes.AddTable($Rows.Count,$Widths.Count,48,$Y,$width,$height)
    $owner.Name='Tabela editável'
    $table=$owner.Table
    for ($col=1;$col -le $Widths.Count;$col++) { $table.Columns.Item($col).Width=$Widths[$col-1] }
    for ($row=1;$row -le $Rows.Count;$row++) {
        $table.Rows.Item($row).Height=$Heights[$row-1]
        for ($col=1;$col -le $Widths.Count;$col++) {
            $cell=$table.Cell($row,$col)
            $cell.Shape.Fill.Solid()
            $cell.Shape.Fill.ForeColor.RGB=$white
            for ($border=1;$border -le 4;$border++) { $cell.Borders.Item($border).Visible=0 }
            $cell.Borders.Item(3).Visible=-1
            $cell.Borders.Item(3).ForeColor.RGB=$rule
            $cell.Borders.Item(3).Weight=0.55
            $frame=$cell.Shape.TextFrame
            $frame.MarginLeft=10
            $frame.MarginRight=10
            $frame.MarginTop=7
            $frame.MarginBottom=7
            $frame.VerticalAnchor=3
            $range=$frame.TextRange
            $range.Text=[string]$Rows[$row-1][$col-1]
            $range.Font.Name='Arial'
            $range.Font.Size=$FontSize
            $range.Font.Color.RGB=$ink
            $range.Font.Bold=0
            $range.ParagraphFormat.SpaceBefore=0
            $range.ParagraphFormat.SpaceAfter=0
            $range.ParagraphFormat.SpaceWithin=1.04
            if ($row -eq 1) {
                $cell.Shape.Fill.ForeColor.RGB=$navy
                $range.Font.Color.RGB=$white
                $range.Font.Bold=-1
            }
        }
    }
    return $owner
}

function Node($Slide,[string]$Value,[single]$X,[single]$Y,[single]$W,[single]$H,[bool]$Core=$false,[bool]$Optional=$false,[single]$Size=18) {
    $shape=$Slide.Shapes.AddShape(1,$X,$Y,$W,$H)
    $shape.Name=($Value -split "`n")[0]
    $shape.Fill.Solid()
    $shape.Fill.ForeColor.RGB=$light
    $shape.Line.ForeColor.RGB=$navy
    $shape.Line.Weight=1.25
    if ($Core) { $shape.Fill.ForeColor.RGB=$navy }
    if ($Optional) {
        $shape.Fill.ForeColor.RGB=$white
        $shape.Line.ForeColor.RGB=$optionalColor
        $shape.Line.DashStyle=4
    }
    $frame=$shape.TextFrame
    $frame.MarginLeft=9
    $frame.MarginRight=9
    $frame.MarginTop=8
    $frame.MarginBottom=8
    $frame.WordWrap=-1
    $frame.AutoSize=0
    $frame.VerticalAnchor=3
    $range=$frame.TextRange
    $range.Text=$Value.Replace("`n","`r")
    $range.Font.Name='Arial'
    $range.Font.Size=$Size
    $range.Font.Color.RGB=$ink
    $range.Font.Bold=0
    $range.ParagraphFormat.Alignment=2
    $range.ParagraphFormat.SpaceWithin=1.12
    $range.ParagraphFormat.SpaceAfter=0
    $range.ParagraphFormat.SpaceBefore=0
    $range.Paragraphs(1).Font.Bold=-1
    if ($Core) { $range.Font.Color.RGB=$white }
    return $shape
}

function Segment($Slide,[single]$X1,[single]$Y1,[single]$X2,[single]$Y2,[string]$Arrows='end',[bool]$Dashed=$false) {
    $shape=$Slide.Shapes.AddConnector(1,$X1,$Y1,$X2,$Y2)
    $shape.Line.ForeColor.RGB=$navy
    $shape.Line.Weight=1.5
    $shape.Line.BeginArrowheadStyle=1
    $shape.Line.EndArrowheadStyle=1
    if ($Arrows -eq 'both') { $shape.Line.BeginArrowheadStyle=2; $shape.Line.EndArrowheadStyle=2 }
    if ($Arrows -eq 'end') { $shape.Line.EndArrowheadStyle=2 }
    if ($Dashed) { $shape.Line.DashStyle=4 }
    return $shape
}

$app=New-Object -ComObject PowerPoint.Application
$previousCount=$app.Presentations.Count
$presentation=$app.Presentations.Add(0)
$presentation.PageSetup.SlideWidth=960
$presentation.PageSetup.SlideHeight=540
try {
    # 1. Identificação e fase do trabalho.
    $s=New-Slide ''
    [void]$s.Shapes.AddPicture((Join-Path $workspace 'template_laset\Figuras\logo_ISEP.jpg'),0,-1,60,38,260,(260*153/521))
    [void]$s.Shapes.AddPicture((Join-Path $workspace 'template_laset\Figuras\inesc.jpg'),0,-1,700,45,200,63)
    [void](Text $s "Sistema de escrita e leitura`nmultiprotocolo" 60 185 840 115 44 $navy $true)
    [void](Text $s 'Estado da arte, requisitos e arquitetura' 60 330 840 45 23 $teal)
    [void](Text $s 'Francisco Liquito e Pedro Ribeiro' 60 427 770 30 21 $ink)
    [void](Text $s "Mestrado de Sistemas Autónomos`nLaSET" 60 468 660 47 16 $grey)
    [void](Text $s '23 de outubro de 2026' 700 486 200 25 14 $grey $false 3)
    Notes $s @'
Apresentamos o trabalho desenvolvido até à análise de requisitos e à arquitetura conceptual. O objetivo desta apresentação é explicar o problema, resumir o estado da arte e mostrar as capacidades exigidas ao sistema. A implementação e os ensaios experimentais pertencem à fase seguinte.

Fonte: relatório LaSET atual, capítulos 1 a 4, template_laset/build/Modelo_LaSET.pdf.
Autores: template_laset/Outros/Identificacao.tex.
Logótipos originais do projeto: template_laset/Figuras/logo_ISEP.jpg e template_laset/Figuras/inesc.jpg. Proporções preservadas.
'@

    # 2. Enquadramento.
    $s=New-Slide 'Problema e objetivo'
    [void](Text $s 'Um PC, várias interfaces de comunicação' 48 147 390 100 29 $navy $true)
    [void](Text $s 'Integrar comando, aquisição e atuação sobre dispositivos heterogéneos.' 48 287 390 145 25 $ink)
    [void](Text $s 'Origem e destino identificados' 508 147 404 36 23 $teal $true)
    [void](Text $s 'Preservar o significado dos dados' 508 192 404 55 21 $grey)
    [void](Text $s 'Comunicações concorrentes' 508 272 404 36 23 $teal $true)
    [void](Text $s 'Gerir prioridades e diferenças de taxa' 508 317 404 55 21 $grey)
    [void](Text $s 'Referência temporal comum' 508 397 404 36 23 $teal $true)
    [void](Text $s 'Associar dados e eventos' 508 442 404 40 21 $grey)
    Notes $s @'
O problema combina interfaces diferentes e operações com ritmos distintos. O PC deve conseguir comandar dispositivos, recolher dados e atuar sobre cargas através da unidade embebida. Cada operação tem de identificar origem e destino, preservar o significado da informação e coordenar o acesso a recursos. A referência temporal permite combinar dados com outras fontes. Os limites de carga e desempenho continuam para dimensionamento no projeto.

Fonte: relatório, secções 1.1 e 1.3, problemas P01 a P04, RF08, RF10 a RF14 e RF16.
'@

    # 3. Síntese tecnológica do estado da arte.
    $s=New-Slide 'Estado da arte: tecnologias'
    $rows=@(
        @('Interface','Organização','Implicação no projeto'),
        @('I2C','Barramento local partilhado','Definir papéis e níveis elétricos.'),
        @('RS232','Ligação ponto a ponto','Adequar a interface aos níveis elétricos.'),
        @('RS485','Rede multiponto','Avaliar topologia, terminação e taxa.'),
        @('CAN FD','Barramento com arbitragem','Definir a configuração das duas fases.'),
        @('Ethernet','Rede comutada','Distinguir taxa nominal de débito útil.')
    )
    [void](Native-Table $s $rows @(145,265,454) 132 @(38,59,59,59,59,59) 19)
    [void](Text $s 'A interface física não define o protocolo de aplicação.' 48 478 850 32 21 $teal $true)
    Notes $s @'
A comparação mostra que as tecnologias têm organizações e restrições distintas. I2C permite partilha de um barramento local, RS232 é ponto a ponto e RS485 suporta uma rede multiponto. Em CAN FD importa documentar as fases nominal e de dados. Em Ethernet, 100 Mbit/s é uma capacidade nominal da ligação, sem garantir o mesmo débito útil. Os protocolos de aplicação e os mapeamentos continuam a exigir definição.

Fonte: relatório, secções 2.2 a 2.7 e Tabelas 2.3 e 2.4.
Referências do relatório:
NXP, UM10204: https://www.nxp.com/docs/en/user-guide/UM10204.pdf
Texas Instruments, RS232: https://www.ti.com/lit/an/slla607/slla607.pdf
Texas Instruments, RS485: https://www.ti.com/lit/an/snla049b/snla049b.pdf
CAN in Automation, CAN FD: https://can-cia.org/can-knowledge/can-fd-the-basic-idea
Microchip, Ethernet: https://ww1.microchip.com/downloads/en/AppNotes/01120a.pdf
'@

    # 4. Comparação de soluções já analisadas no relatório.
    $s=New-Slide 'Estado da arte: plataformas'
    $rows=@(
        @('Solução analisada','Contributo','Limitação relevante'),
        @('GoWired','Plataforma programável com CAN, RS485 e Ethernet.','Características anunciadas. Desempenho por verificar.'),
        @('IOT-GATE-iMX7','Plataforma Linux configurável.','A opção CAN substitui RS485.'),
        @('MGate 5105-MB-EIP','Integração de Modbus e EtherNet/IP.','Funções e mapeamento definidos pelos protocolos.'),
        @('Anybus AB7838-F','Troca cíclica CANopen e EtherNet/IP.','Papéis específicos de slave e adapter.')
    )
    [void](Native-Table $s $rows @(205,324,335) 132 @(38,77,65,77,77) 18)
    [void](Text $s 'A seleção da plataforma permanece para a fase de projeto.' 48 485 864 30 20 $teal $true)
    Notes $s @'
O relatório analisa duas plataformas programáveis e dois conversores dedicados. Os exemplos mostram modelos diferentes de integração. No GoWired, as características são anunciadas, sem validação experimental no nosso trabalho. No IOT-GATE-iMX7, a opção CAN substitui RS485. MGate e Anybus integram protocolos e papéis específicos. Esta seleção não demonstra que alguma solução satisfaça todos os requisitos do projeto. Não apresentamos uma nova avaliação comercial ou resultados medidos.

Fonte: relatório, secção 2.8 e Tabela 2.1. Síntese das fontes consultadas no relatório.
GoWired: https://www.crowdsupply.com/domatic/gowired-multiprotocol-gateway
CompuLab: https://www.compulab.com/products/iot-gateways/iot-gate-imx7-nxp-i-mx-7-internet-of-things-gateway/
Manual CompuLab: https://www.compulab.com/wp-content/uploads/2018/05/iot-gate-imx7_reference-guide_2018-05-06.pdf
Moxa: https://www.moxa.com/en/products/industrial-edge-connectivity/protocol-gateways/ethernet-ip-gateways/mgate-5105-mb-eip-series
Anybus: https://www.hms-networks.com/p/ab7838-f-anybus-x-gateway-ethernet-ip-adapter-canopen-slave
'@

    # 5. Sete casos de utilização.
    $s=New-Slide 'Casos de utilização'
    [void](Text $s 'Operações com dispositivos' 48 131 405 36 23 $teal $true)
    [void](Text $s 'UC01. Comando pelo PC' 48 193 405 34 22 $navy $true)
    [void](Text $s 'Selecionar o destino e receber feedback quando previsto.' 48 234 405 55 20 $ink)
    [void](Text $s 'UC02. Aquisição de sensores' 48 301 405 34 22 $navy $true)
    [void](Text $s 'Identificar a origem e disponibilizar dados.' 48 342 405 55 20 $ink)
    [void](Text $s 'UC03. Atuação por PWM' 48 409 405 34 22 $navy $true)
    [void](Text $s 'Comandar um dos três canais protegidos.' 48 450 405 55 20 $ink)
    [void](Text $s 'Execução e disponibilização' 510 131 402 36 23 $teal $true)
    [void](Text $s 'UC04. Operação concorrente' 510 193 402 34 21 $navy $true)
    [void](Text $s 'Prioridades e diferenças de taxa' 510 230 402 35 19 $ink)
    [void](Text $s 'UC05. Sincronização PPS/GPS' 510 278 402 34 21 $navy $true)
    [void](Text $s 'Associação temporal de dados e eventos' 510 315 402 35 19 $ink)
    [void](Text $s 'UC06. Operação elétrica e ambiental' 510 363 402 34 20 $navy $true)
    [void](Text $s 'Entrada entre 5 e 60 V' 510 400 402 32 19 $ink)
    [void](Text $s 'UC07. Disponibilização ou registo' 510 448 402 34 20 $navy $true)
    [void](Text $s 'Envio de dados e opção de microSD' 510 485 402 29 19 $ink)
    Notes $s @'
Os sete casos de utilização cobrem comando, aquisição, atuação e as condições de execução. A aquisição de sensores permanece genérica. A garra, quando usada como exemplo, ocupa um dos três canais PWM. UC04 trata concorrência e prioridades. UC05 relaciona dados no tempo através de PPS e informação GPS. UC06 inclui alimentação e condições de instalação ainda por especificar. Em UC07, o envio de dados é obrigatório e o registo persistente em microSD é opcional.

Fonte: relatório, secção 1.2, UC01 a UC07. A síntese não acrescenta transmissão simultânea no acesso do PC nem requisitos ambientais quantitativos.
'@

    # 6. Quantidades e capacidades confirmadas.
    $s=New-Slide 'Requisitos de comunicação'
    $rows=@(
        @('ID','Interface','Especificação confirmada','Observações'),
        @('RF01','I2C',"2 barramentos independentes`nStandard mode",'Papéis e níveis a definir'),
        @('RF02','RS232',"Operação a 500 kbit/s`nCapacidade até 1 Mbit/s",'Ensaio também a 1 Mbit/s'),
        @('RF03','RS485','Aprox. 16 a 32 nós de referência','Taxa e protocolo em aberto'),
        @('RF04','CAN FD',"3 barramentos`nAté 8 Mbit/s em cada",'Distribuição e fases a definir'),
        @('RF05','Ethernet','Mínimo nominal de 100 Mbit/s','Gigabit desejável')
    )
    [void](Native-Table $s $rows @(73,125,369,297) 125 @(35,55,55,55,55,55) 18)
    [void](Text $s 'A referência RS485 não estabelece um limite rígido de 32 nós.' 48 447 864 29 18 $grey)
    [void](Text $s 'RF09. Acesso bidirecional por RS232, CAN ou Ethernet, sem simultaneidade exigida.' 48 482 864 45 19 $teal $true)
    Notes $s @'
Estas são as quantidades e capacidades confirmadas pelo docente e formalizadas no relatório. I2C exige exatamente dois barramentos independentes em Standard mode. RS232 opera a 500 kbit/s e deve ter capacidade e ensaio a 1 Mbit/s. RS485 usa aproximadamente 16 a 32 nós como referência, sem teto rígido de 32. Existem exatamente três CAN FD no total, cada um até 8 Mbit/s. O valor não fixa os bitrates separados das fases. Ethernet exige pelo menos 100 Mbit/s nominais. O PC dispõe das três alternativas RS232, CAN e Ethernet.

Fonte: relatório, RF01 a RF05, RF09 e Tabela 3.3. As alternativas do PC não impõem simultaneidade, preferência, redundância ou comutação automática. As capacidades indicadas são requisitos, sem resultados experimentais.
'@

    # 7. Requisitos transversais.
    $s=New-Slide 'Atuação, sincronização e operação'
    [void](Text $s 'Atuação PWM' 48 138 260 34 23 $teal $true)
    [void](Text $s '3 canais' 48 199 260 55 34 $navy $true)
    [void](Text $s "50 Hz`n1100 a 1900 µs`nProteção elétrica obrigatória" 48 278 260 139 22 $ink)
    [void](Text $s 'Sincronização' 354 138 280 34 23 $teal $true)
    [void](Text $s 'PPS a 1 Hz' 354 199 280 55 32 $navy $true)
    [void](Text $s "GPS entre impulsos`nResolução da ordem dos µs`nErro absoluto a medir" 354 278 280 139 21 $ink)
    [void](Text $s 'Execução e alimentação' 686 138 226 55 21 $teal $true)
    [void](Text $s '5 a 60 V' 686 199 226 55 32 $navy $true)
    [void](Text $s "RTOS obrigatório`nFreeRTOS candidato`nPlataforma por selecionar" 686 278 226 139 21 $ink)
    [void](Text $s 'Cargas, resolução PWM, tolerâncias e condições de ensaio ficam para projeto.' 48 463 864 52 20 $grey)
    Notes $s @'
RF15 exige exatamente três saídas PWM eletricamente protegidas, a 50 Hz, com largura útil entre 1100 e 1900 microssegundos. Cargas, níveis elétricos, resolução PWM e proteção concreta ficam para o projeto. RF16 usa PPS a 1 Hz e mensagens GPS entre os impulsos para sincronizar o relógio e associar dados com resolução da ordem dos microssegundos. Isto não garante exatidão absoluta de mais ou menos 1 microssegundo. O erro e a incerteza serão medidos. RNF07 exige RTOS, com FreeRTOS apenas como candidato. RNF08 exige a gama de entrada de 5 a 60 V, incluindo os limites.

Fonte: relatório, RF15, RF16, RNF07, RNF08 e DP03, DP12 a DP14. As tolerâncias e a regra de decisão devem ser documentadas antes dos ensaios de conformidade.
Fundamentação PPS: https://www.rfc-editor.org/rfc/rfc2783.html
Incerteza: https://www.bipm.org/en/doi/10.59161/jcgm100-2008e
'@

    # 8. Diagrama funcional editável da arquitetura.
    $s=New-Slide 'Arquitetura de alto nível'
    [void](Segment $s 228 276 340 276 'both')
    [void](Segment $s 620 276 724 276 'both')
    [void](Segment $s 228 161 284 161 'none')
    [void](Segment $s 284 161 284 209 'none')
    [void](Segment $s 284 209 340 209 'end')
    [void](Segment $s 228 459 284 459 'none')
    [void](Segment $s 284 459 284 348 'none')
    [void](Segment $s 284 348 340 348 'end')
    [void](Segment $s 480 380 480 424 'end')
    [void](Segment $s 620 348 671 348 'none' $true)
    [void](Segment $s 671 348 671 459 'none' $true)
    [void](Segment $s 671 459 724 459 'end' $true)
    [void](Node $s "PC`nRS232, CAN`nou Ethernet" 48 227 180 98 $false $false 19)
    [void](Node $s "Referência temporal`nPPS a 1 Hz e GPS" 48 116 180 90 $false $false 18)
    [void](Node $s "Alimentação`nEntrada: 5 a 60 V" 48 424 180 70 $false $false 18)
    [void](Node $s "Unidade embebida`nComunicação`nProcessamento e encaminhamento`nRTOS e relógio" 340 180 280 200 $true $false 20)
    [void](Node $s "Dispositivos externos`n2 I2C independentes`n3 CAN FD no total`nRS232 e RS485`nEthernet" 724 174 188 204 $false $false 18)
    [void](Node $s "3 PWM protegidos`n50 Hz, 1100 a 1900 µs" 340 424 280 70 $false $false 18)
    [void](Node $s "MicroSD`nRegisto opcional" 724 424 188 70 $false $true 18)
    [void](Text $s 'Três CAN FD no total. Papéis, plataforma e componentes por definir.' 48 512 837 24 17 $grey)
    Notes $s @'
A arquitetura é uma decomposição funcional. A unidade concentra comunicação, processamento, encaminhamento e coordenação sobre RTOS, com relógio e associação temporal. O PC usa RS232, CAN ou Ethernet. A representação de papéis separados não acrescenta portas físicas dedicadas: os três CAN FD são o total, incluindo ligações ao PC e aos nós externos. A entrada de alimentação não determina a tensão das cargas PWM. A microSD é uma opção. Os blocos não selecionam um MCU/MPU, um RTOS concreto ou uma tarefa de software por função.

Fonte: relatório, capítulo 4, Figura 4.1 e Tabelas 4.1 e 4.2. As setas indicam os sentidos funcionais, sem impor transmissão simultânea em ambos os sentidos.
'@

    # 9. Percursos obrigatórios e validação planeada.
    $s=New-Slide 'Encaminhamento e validação'
    [void](Text $s 'Percursos de RF17' 48 132 410 34 23 $teal $true)
    foreach ($rowY in @(201,276,351,426)) { [void](Segment $s 213 $rowY 302 $rowY 'both') }
    [void](Node $s 'Ethernet' 48 176 165 275 $true $false 23)
    [void](Node $s 'CAN FD' 302 176 150 50 $false $false 21)
    [void](Node $s 'RS485' 302 251 150 50 $false $false 21)
    [void](Node $s 'RS232' 302 326 150 50 $false $false 21)
    [void](Node $s 'I2C' 302 401 150 50 $false $false 21)
    [void](Text $s "Quatro pares obrigatórios nos dois sentidos`nMapeamentos e protocolos por definir" 48 469 425 51 18 $grey)
    [void](Text $s 'Ensaios previstos' 528 132 384 34 23 $teal $true)
    [void](Text $s 'Comunicações' 528 191 384 29 21 $navy $true)
    [void](Text $s 'Dados conhecidos e percursos RF17' 528 227 384 44 19 $ink)
    [void](Text $s 'PWM e alimentação' 528 276 384 29 21 $navy $true)
    [void](Text $s 'PWM: 3 canais. Entrada: 5 a 60 V' 528 312 384 44 19 $ink)
    [void](Text $s 'Sincronização' 528 361 384 29 21 $navy $true)
    [void](Text $s 'Resolução, erro e incerteza' 528 397 384 44 19 $ink)
    [void](Text $s 'Conformidade' 528 446 384 29 21 $navy $true)
    [void](Text $s 'Tolerâncias e condições a definir' 528 482 384 31 19 $ink)
    Notes $s @'
RF17 estabelece quatro pares bidirecionais: Ethernet com CAN, RS485, RS232 e I2C. Não se infere conversão universal entre todos os pares, nem equivalência semântica entre protocolos. É necessário definir as operações e os respetivos mapeamentos. A validação prevista usa dados conhecidos nas interfaces e em cada percurso, incluindo RS232 a 500 kbit/s e a 1 Mbit/s, e a capacidade de cada CAN FD até 8 Mbit/s. Os ensaios também medem PWM, alimentação e sincronização. As condições, tolerâncias e regras de aceitação têm de estar definidas antes dos ensaios de conformidade. Nesta fase ainda não existem resultados experimentais.

Fonte: relatório, RF17, secções 3.3 e 3.4, Tabelas 3.1 a 3.3 e Figura 4.3.
'@

    # 10. Delimitação da fase e trabalho seguinte.
    $s=New-Slide 'Estado atual e próximos passos'
    [void](Text $s 'Documentado' 48 139 405 36 24 $teal $true)
    [void](Text $s "Estado da arte e limitações`n7 casos de utilização`n17 RF e 8 RNF`nCritérios de ensaio e rastreabilidade`nArquitetura funcional" 48 209 405 206 22 $ink)
    [void](Text $s 'A definir no projeto' 510 139 402 36 24 $teal $true)
    [void](Text $s "Plataforma e RTOS concreto`nProtocolos e mapeamentos`nCargas, proteção e tolerâncias`nDimensionamento e PCB`nMedições de desempenho" 510 209 402 206 22 $ink)
    [void](Text $s 'RNF01 a RNF03 e RNF05 são propostas.' 48 411 405 45 17 $grey)
    [void](Text $s 'MicroSD e PoE opcionais. Gigabit desejável.' 510 411 402 45 17 $grey)
    [void](Text $s 'Próxima etapa: fechar as decisões DP01 a DP17 e preparar a implementação e os ensaios.' 48 475 864 48 20 $navy $true)
    Notes $s @'
Concluímos esta fase com o problema enquadrado, o estado da arte, os sete casos de utilização, os requisitos documentados e a arquitetura conceptual. RNF01 a RNF03 e RNF05 permanecem propostas de qualidade. MicroSD e PoE são opcionais e Gigabit Ethernet é desejável. As 17 definições de projeto reservam a seleção da plataforma, os protocolos, as cargas e o dimensionamento, entre outros aspetos. O próximo passo é fechar essas decisões de forma consistente com os requisitos e preparar a implementação e os ensaios. Não se apresentam protótipo concluído ou resultados medidos.

Fonte: relatório, secções 3.2, 3.5 a 3.7 e capítulo 4. DP01 a DP17.
'@

    # Medições de ajuste no próprio PowerPoint.
    foreach ($slide in $presentation.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTable -eq -1) {
                $table=$shape.Table
                for ($row=1;$row -le $table.Rows.Count;$row++) {
                    for ($col=1;$col -le $table.Columns.Count;$col++) {
                        $cellShape=$table.Cell($row,$col).Shape
                        $available=$cellShape.Height-$cellShape.TextFrame.MarginTop-$cellShape.TextFrame.MarginBottom
                        $bound=$cellShape.TextFrame2.TextRange.BoundHeight
                        if ($bound -gt $available+2) { $fit.Add(@{slide=$slide.SlideIndex;shape=$shape.Name;row=$row;col=$col;bound=$bound;available=$available}) }
                    }
                }
            } elseif ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) {
                $available=$shape.Height-$shape.TextFrame.MarginTop-$shape.TextFrame.MarginBottom
                $bound=$shape.TextFrame2.TextRange.BoundHeight
                if ($bound -gt $available+2) { $fit.Add(@{slide=$slide.SlideIndex;shape=$shape.Name;text=$shape.TextFrame.TextRange.Text;bound=$bound;available=$available}) }
            }
        }
    }
    $fit | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $build 'text-fit.json')
    $presentation.SaveAs($candidate,24)
    $presentation.Close()
    $presentation=$app.Presentations.Open($candidate,-1,0,0)
    for ($index=1;$index -le $presentation.Slides.Count;$index++) {
        $slidePath=Join-Path $preview ('slide-{0:D2}.png' -f $index)
        $presentation.Slides.Item($index).Export($slidePath,'PNG',1600,900)
    }
    $presentation.SaveAs((Join-Path $build 'previsualizacao.pdf'),32)
    Write-Output ('Slides: '+$presentation.Slides.Count+'. Problemas de ajuste de texto: '+$fit.Count)
    Write-Output $candidate
} finally {
    if ($null -ne $presentation) { $presentation.Close() }
    if ($previousCount -eq 0 -and $app.Presentations.Count -eq 0) { $app.Quit() }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($app)
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
