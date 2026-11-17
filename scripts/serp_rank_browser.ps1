param([string[]]$qs,[string]$match='ashrafkhetran|fefbbf|eeopbh|jmhhkf|hjrs-journal-checker|ai-tell-checker|gbp-audit|local-pack-exporter|forms-whatsapp|sheets-urdu',[string]$gl='',[ValidateSet('google','bing')][string]$engine='bing',[int]$start=0)
# Rank check via real browser (Google=Chrome Default, Bing=Edge). Copies SERP text, lists our URLs.
Add-Type -AssemblyName System.Windows.Forms
Add-Type 'using System;using System.Runtime.InteropServices;public class FG{[DllImport("user32.dll")]public static extern IntPtr GetForegroundWindow();[DllImport("user32.dll")]public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);}'
function FgProc{$pid2=0;[void][FG]::GetWindowThreadProcessId([FG]::GetForegroundWindow(),[ref]$pid2);(Get-Process -Id $pid2).ProcessName}
$ws=New-Object -ComObject WScript.Shell
$proc= if($engine -eq 'google'){'chrome'}else{'msedge'}
foreach($q in $qs){
  $e=[uri]::EscapeDataString($q)
  $u= if($engine -eq 'google'){"https://www.google.com/search?hl=en&q=$e"+$(if($gl){"&gl=$gl"})+$(if($start){"&start=$start"})}else{"https://www.bing.com/search?setlang=en&q=$e"+$(if($start){"&first=$($start+1)"})}
  if((FgProc) -ne $proc){$null=$ws.AppActivate((Get-Process $proc|?{$_.MainWindowTitle}|select -First 1).Id); Start-Sleep -m 800}
  if((FgProc) -ne $proc){"== $q : ABORT, foreground is $(FgProc) not $proc"; break}
  [System.Windows.Forms.SendKeys]::SendWait("^l"); Start-Sleep -m 400
  Set-Clipboard $u; [System.Windows.Forms.SendKeys]::SendWait("^v{ENTER}"); Start-Sleep 7
  Set-Clipboard "x"; [System.Windows.Forms.SendKeys]::SendWait("^a^c"); Start-Sleep -m 800
  $t=Get-Clipboard -Raw
  $l=$t -split "`r?`n" | %{$_.Trim()} | ?{$_ -match '^(https?://)\S+'}
  $seen=@(); foreach($x in $l){ if($seen.Count -eq 0 -or $seen[-1] -ne $x){$seen+=$x} }
  $n=$start; $hits=@(); foreach($s in $seen){$n++; if($s -match $match){$hits+="#$n $s"}}
  "== $engine | $q (results $($seen.Count)): " + $(if($seen.Count -eq 0){'COPY FAILED'}elseif($hits){$hits -join ' ; '}else{'not found'})
}



