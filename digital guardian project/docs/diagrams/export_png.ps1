param(
    [Parameter(Mandatory = $true)]
    [string]$SvgPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [Parameter(Mandatory = $true)]
    [int]$Width,

    [Parameter(Mandatory = $true)]
    [int]$Height
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$resolvedSvg = (Resolve-Path $SvgPath).Path
$resolvedOut = $OutputPath
$svgMarkup = Get-Content $resolvedSvg -Raw

$html = @"
<html>
<body style="margin:0;background:white;overflow:hidden;">
  $svgMarkup
</body>
</html>
"@

$form = New-Object System.Windows.Forms.Form
$form.Width = $Width + 20
$form.Height = $Height + 20
$form.ShowInTaskbar = $false
$form.StartPosition = "Manual"
$form.Location = New-Object System.Drawing.Point(-32000, -32000)

$browser = New-Object System.Windows.Forms.WebBrowser
$browser.Dock = "Fill"
$browser.ScrollBarsEnabled = $false
$browser.ScriptErrorsSuppressed = $true
$form.Controls.Add($browser)

$script:done = $false

$browser.Add_DocumentCompleted({
    if ($script:done) { return }
    Start-Sleep -Milliseconds 1800
    $bitmap = New-Object System.Drawing.Bitmap $Width, $Height
    $browser.DrawToBitmap($bitmap, (New-Object System.Drawing.Rectangle 0, 0, $Width, $Height))
    $bitmap.Save($resolvedOut, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    $script:done = $true
    $form.Close()
})

$browser.DocumentText = $html
$form.Show()

while (-not $script:done) {
    [System.Windows.Forms.Application]::DoEvents()
    Start-Sleep -Milliseconds 100
}
