param([string]$Path, [string[]]$Needles, [int]$Before = 200, [int]$After = 500, [int]$Max = 10)
Add-Type -TypeDefinition @"
using System; using System.IO; using System.Collections.Generic; using System.Text;
public static class Ctx {
  public static List<string> Find(string path, string[] needles, int before, int after, int max) {
    var outp = new List<string>(); var pats = new List<byte[]>(); foreach (var n in needles) pats.Add(Encoding.ASCII.GetBytes(n));
    var counts = new int[needles.Length];
    var buf = new byte[1<<24]; int keep = before+after+64; long basePos = 0;
    using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1<<20)) {
      int carry = 0; int read;
      while ((read = fs.Read(buf, carry, buf.Length - carry)) > 0) {
        int len = carry + read;
        for (int k=0;k<pats.Count;k++){ var p=pats[k]; if (counts[k]>=max) continue;
          for (int i=Math.Min(before,carry);i<=len-p.Length-after && counts[k]<max;i++){ int j=0; while(j<p.Length && buf[i+j]==p[j]) j++; if(j==p.Length){
            var sb = new StringBuilder(); for (int q=Math.Max(0,i-before);q<i+p.Length+after;q++){ byte c=buf[q]; sb.Append(c>=32&&c<127?(char)c:'.'); }
            outp.Add("["+needles[k]+"] "+(basePos+i-carry)+": "+sb.ToString()); counts[k]++; i+=p.Length; } } }
        carry = Math.Min(keep, len); Buffer.BlockCopy(buf, len-carry, buf, 0, carry); basePos += read;
      }
    }
    return outp;
  }
}
"@
[Ctx]::Find($Path, $Needles, $Before, $After, $Max) | ForEach-Object { ($_ -replace '\.{3,}', ' | ') -replace '(\| [^|]{0,6} )+', '| ' }
