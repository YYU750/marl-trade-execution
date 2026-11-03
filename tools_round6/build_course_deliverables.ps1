param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)
$ErrorActionPreference = 'Stop'
$sourceDeck = Join-Path $Root 'deliverables\round5_course_slides.pptx'
$sourceDoc = Join-Path $Root 'deliverables\round5_course_report.docx'
$outputDeck = Join-Path $Root 'deliverables\round6_course_slides.pptx'
$outputDoc = Join-Path $Root 'deliverables\round6_course_report.docx'
Copy-Item -LiteralPath $sourceDeck -Destination $outputDeck -Force
Copy-Item -LiteralPath $sourceDoc -Destination $outputDoc -Force

function Get-Rgb([int]$r, [int]$g, [int]$b) { return ($r + 256 * $g + 65536 * $b) }
function Add-TextBox($slide, [string]$text, [single]$left, [single]$top, [single]$width, [single]$height, [single]$size, [int]$color, [bool]$bold = $false) {
    $shape = $slide.Shapes.AddTextbox(1, $left, $top, $width, $height)
    $shape.Line.Visible = 0
    $shape.Fill.Visible = 0
    $shape.TextFrame.MarginLeft = 0
    $shape.TextFrame.MarginRight = 0
    $shape.TextFrame.MarginTop = 0
    $shape.TextFrame.MarginBottom = 0
    $shape.TextFrame.WordWrap = -1
    $range = $shape.TextFrame.TextRange
    $range.Text = $text
    $range.Font.Name = 'Microsoft YaHei'
    $range.Font.Size = $size
    $range.Font.Color.RGB = $color
    $range.Font.Bold = [int]$bold
    return $shape
}
function Add-EditableTable($slide, [string[]]$headers, [object[]]$rows, [single]$left, [single]$top, [single]$width, [single]$height, [single]$fontSize) {
    $t = $slide.Shapes.AddTable($rows.Count + 1, $headers.Count, $left, $top, $width, $height).Table
    $headerFill = Get-Rgb 231 239 240
    $ink = Get-Rgb 23 46 56
    for ($c = 1; $c -le $headers.Count; $c++) {
        $cell = $t.Cell(1, $c)
        $cell.Shape.Fill.ForeColor.RGB = $headerFill
        $cell.Shape.TextFrame.MarginLeft = 7
        $cell.Shape.TextFrame.MarginRight = 7
        $cell.Shape.TextFrame.MarginTop = 4
        $cell.Shape.TextFrame.MarginBottom = 4
        $cell.Shape.TextFrame.TextRange.Text = $headers[$c - 1]
        $cell.Shape.TextFrame.TextRange.Font.Name = 'Microsoft YaHei'
        $cell.Shape.TextFrame.TextRange.Font.Size = $fontSize
        $cell.Shape.TextFrame.TextRange.Font.Bold = -1
        $cell.Shape.TextFrame.TextRange.Font.Color.RGB = $ink
    }
    for ($r = 0; $r -lt $rows.Count; $r++) {
        for ($c = 1; $c -le $headers.Count; $c++) {
            $cell = $t.Cell($r + 2, $c)
            $cell.Shape.Fill.ForeColor.RGB = Get-Rgb 255 255 255
            $cell.Shape.TextFrame.MarginLeft = 7
            $cell.Shape.TextFrame.MarginRight = 7
            $cell.Shape.TextFrame.MarginTop = 4
            $cell.Shape.TextFrame.MarginBottom = 4
            $cell.Shape.TextFrame.TextRange.Text = [string]$rows[$r][$c - 1]
            $cell.Shape.TextFrame.TextRange.Font.Name = 'Microsoft YaHei'
            $cell.Shape.TextFrame.TextRange.Font.Size = $fontSize
            $cell.Shape.TextFrame.TextRange.Font.Color.RGB = $ink
        }
    }
    return $t
}

$teal = Get-Rgb 0 132 139
$ink = Get-Rgb 23 46 56
$muted = Get-Rgb 82 112 126
$green = Get-Rgb 56 124 89
$red = Get-Rgb 184 65 59
$p = New-Object -ComObject PowerPoint.Application
$p.Visible = -1
$deck = $p.Presentations.Open($outputDeck, $false, $false, $false)
if ($deck.Slides.Count -ne 10) { throw "Expected 10 Round 5 slides, found $($deck.Slides.Count)" }

$s = $deck.Slides.Add(11, 12)
Add-TextBox $s '10 · 双边学习' 50 24 820 24 12 $teal $true | Out-Null
Add-TextBox $s '同一快照决策，两张 Q 表分别更新' 50 57 860 50 27 $ink $true | Out-Null
Add-TextBox $s '训练第 1 个 episode 的第 23 步：双方同时请求零股，环境按各自剩余订单分别补足。' 52 111 850 38 15 $muted $false | Out-Null
$caseRows = [object[]]::new(2)
$caseRows[0] = [string[]]@('A', '剩 7 步；64,009 股', '0 / 4,009 / 4,009 股', '-86.4200', '0 → -25.9260')
$caseRows[1] = [string[]]@('B', '剩 7 步；70,000 股', '0 / 10,000 / 10,000 股', '-215.5650', '0 → -64.6695')
Add-EditableTable $s ([string[]]@('学习器', '当步状态', '请求 / 强制 / 成交', '各自奖励', 'Q 更新（alpha=0.3）')) $caseRows 52 158 856 125 12 | Out-Null
Add-TextBox $s '更新使用各自奖励与各自 Q 表；非终止步的 next_max_q 均为 0，因此 Q_new = 0 + 0.3 × (reward + 0 − 0)。强制成交没有记到策略请求量里。' 55 304 850 58 14 $ink $false | Out-Null
$summaryRows = [object[]]::new(2)
$summaryRows[0] = [string[]]@('G0：TWAP / TWAP', '7.4144', '7.4144', '本轮共同测试基准')
$summaryRows[1] = [string[]]@('G2：IQL / IQL', '8.8928', '8.8713', 'A 85.998%、B 90.094% 成交来自强制补足')
Add-EditableTable $s ([string[]]@('测试场景', 'A 成本 bp', 'B 成本 bp', '行为核对')) $summaryRows 52 379 856 91 12 | Out-Null
Add-TextBox $s '双方均为 100% 完成，但这主要由环境约束保证；IQL 没有胜过 TWAP。' 55 486 820 27 14 $red $true | Out-Null
Add-TextBox $s '双机构交易执行模拟 · 第六轮' 52 520 420 16 9 $muted $false | Out-Null
Add-TextBox $s '11 / 12' 850 520 60 16 9 $muted $false | Out-Null

$s = $deck.Slides.Add(12, 12)
Add-TextBox $s '11 · 成本与对手切换' 50 24 820 24 12 $teal $true | Out-Null
Add-TextBox $s '双边学习未降低成本；对手变化会改变 A 的表现' 50 57 870 50 26 $ink $true | Out-Null
Add-TextBox $s '每行均为同一组 100 个测试 seed 的均值。成本单位是 bp，越低越好。' 52 111 850 28 14 $muted $false | Out-Null
$compareRows = [object[]]::new(5)
$compareRows[0] = [string[]]@('G0 · TWAP / TWAP', '7.4144', '7.4144', '基准')
$compareRows[1] = [string[]]@('G1 · 第五轮 Q / TWAP', '9.4122', '6.4594', 'A 比 G0 高 1.9978 [1.1521, 2.8435]')
$compareRows[2] = [string[]]@('G2 · IQL / IQL', '8.8928', '8.8713', 'A +1.4784；B +1.4569 bp vs G0')
$compareRows[3] = [string[]]@('G3 · 冻结 IQL-A / TWAP-B', '9.3323', '6.4626', 'A 比 G2 高 0.4395 [0.3367, 0.5423]')
$compareRows[4] = [string[]]@('G3 · 冻结 IQL-A / 前置-B', '9.6180', '5.6478', 'A 比 G2 高 0.7252 [0.6356, 0.8148]')
Add-EditableTable $s ([string[]]@('测试场景', 'A 成本 bp', 'B 成本 bp', 'A 配对差及 95% 区间 / 说明')) $compareRows 52 151 856 221 11.5 | Out-Null
Add-TextBox $s '配对差的完整区间：G2 A − G0 A 为 [0.6435, 2.3133] bp；G2 B − G0 B 为 [0.6074, 2.3064] bp；G3 两项区间如表。均为仿真 seeds 的描述性 t 区间。' 55 388 850 50 12.5 $ink $false | Out-Null
Add-TextBox $s '结论：两张 Q 表确实分别更新并可冻结复测；但动作仍高度依赖完单补足。成本优势、收敛和均衡均未得到证明。' 55 457 850 48 15 $red $true | Out-Null
Add-TextBox $s '双机构交易执行模拟 · 第六轮' 52 520 420 16 9 $muted $false | Out-Null
Add-TextBox $s '12 / 12' 850 520 60 16 9 $muted $false | Out-Null
$deck.Save()
$deck.Close()
$p.Quit()

$w = New-Object -ComObject Word.Application
$w.Visible = $false
$doc = $w.Documents.Open($outputDoc, $false, $false, $false)
$sel = $w.Selection
$sel.EndKey(6) | Out-Null
$sel.InsertBreak(7)
function Add-DocParagraph($selection, $document, [string]$text, [string]$style = 'Normal') {
    $selection.Style = $document.Styles.Item($style)
    $selection.ParagraphFormat.SpaceBefore = 0
    $selection.ParagraphFormat.SpaceAfter = 3
    $selection.ParagraphFormat.LineSpacingRule = 0
    $selection.TypeText($text)
    $selection.TypeParagraph()
}
Add-DocParagraph $sel $doc '第六轮：双机构独立 Q-learning' '标题 1'
Add-DocParagraph $sel $doc '本轮把第五轮的单学习者实验扩展为 A、B 同时学习。双方使用独立 Q 表，在同一市场快照下分别选动作，环境再统一执行联合行动并按各自成交结果更新。两方都只读取自身订单状态与当期公开市场变量。' '正文'
Add-DocParagraph $sel $doc '实验采用 300 个训练 episode、100 个共同测试 seed。训练 seed 为 20263103–20263402，测试 seed 为 20263403–20263502；A、B 的探索随机数种子分别为 20261101、20261102。每方训练 9,000 步，测试前冻结 Q 表且不更新。沿用第五轮参数：alpha=0.30、gamma=1、epsilon 从 0.25 衰减到 0.02，动作倍率为 0、0.5、1、1.5、2；本轮未用测试集调参。' '正文'
Add-DocParagraph $sel $doc '共同测试结果' '标题 2'
$sel.Collapse(0)
$table = $doc.Tables.Add($sel.Range, 6, 4)
$table.Borders.Enable = 1
$headers = @('场景', 'A 成本 bp', 'B 成本 bp', 'A 请求 / 强制补足股数')
$values = @(
    @('G0 TWAP / TWAP', '7.4144', '7.4144', '100,000 / 0'),
    @('G1 第五轮冻结 Q / TWAP', '9.4122', '6.4594', '8,984 / 91,016'),
    @('G2 IQL / IQL', '8.8928', '8.8713', '14,002 / 85,998'),
    @('G3 冻结 IQL-A / TWAP-B', '9.3323', '6.4626', '11,203 / 88,797'),
    @('G3 冻结 IQL-A / 前置-B', '9.6180', '5.6478', '12,972 / 87,028')
)
for ($c=1; $c -le 4; $c++) { $table.Cell(1,$c).Range.Text = $headers[$c-1]; $table.Cell(1,$c).Range.Bold = 1 }
for ($r=0; $r -lt $values.Count; $r++) { for ($c=0; $c -lt 4; $c++) { $table.Cell($r+2,$c+1).Range.Text = $values[$r][$c] } }
$table.Range.Font.Name = 'Microsoft YaHei'
$table.Range.Font.Size = 9
$table.Rows.Item(1).HeadingFormat = -1
$table.Columns.Item(1).Width = 150
$table.Columns.Item(2).Width = 80
$table.Columns.Item(3).Width = 80
$table.Columns.Item(4).Width = 200
$table.Range.Select()
$sel.EndKey(6) | Out-Null
Add-DocParagraph $sel $doc '对手切换与行为' '标题 2'
Add-DocParagraph $sel $doc '按相同 seed 配对，G1 A−G0 A 为 +1.9978 bp（95% 区间 [1.1521, 2.8435]）；G2 A−G0 A 为 +1.4784 [0.6435, 2.3133]，B−G0 B 为 +1.4569 [0.6074, 2.3064]。冻结 G2-A 后，更换对手为 TWAP、前置买入时，A 成本相对自博弈分别增加 0.4395 [0.3367, 0.5423]、0.7252 [0.6356, 0.8148] bp。区间为仿真 seed 的描述性 t 区间。' '正文'
Add-DocParagraph $sel $doc 'G2 测试中，A、B 分别有 93.17%、94.77% 请求零倍配速；平均成交中 85.998%、90.094% 来自环境强制补足。100% 完成由硬约束保证。' '正文'
Add-DocParagraph $sel $doc '训练 episode 1 第 23 步，A 尚余 64,009 股、B 尚余 70,000 股；双方同一快照下都请求零股。A 被补足 4,009 股、奖励 -86.4200；B 被补足 10,000 股、奖励 -215.5650。非终止步的 next_max_q 均为 0，Q_A=0+0.3×(-86.4200)=-25.9260，Q_B=0+0.3×(-215.5650)=-64.6695。' '正文'
Add-DocParagraph $sel $doc '双表同步更新、各自奖励、测试冻结、成本手算和模型保存恢复测试通过；但 IQL 未降低相对 TWAP 的成本，状态覆盖稀疏，成交仍受完单约束支配。自博弈的非平稳性与有限训练不能证明收敛或均衡。' '正文'
$doc.Save()
$doc.Close()
$w.Quit()
Write-Output "ROUND6_PPTX=$outputDeck"
Write-Output "ROUND6_DOCX=$outputDoc"
