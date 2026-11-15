from lib import *
CSS="""
@page{size:A4;margin:18mm 15mm 19mm}
@page land{size:A4 landscape;margin:15mm 11mm 14mm}
*{box-sizing:border-box}
html{font-family:Inter,'DejaVu Sans',Arial,sans-serif;color:#1B2540;font-size:9.8pt;line-height:1.5}
body{margin:0}
.land{page:land}
section.land figure.landfig svg{max-height:470px;margin:0 auto}
section.land figure:not(.landfig){max-width:720px}
section.land .opener{padding:12px 20px;margin-bottom:8px}
section.land table{font-size:8.6pt}
h1,h2,h3{font-weight:700;color:#0B1226;margin:0}
h2{font-size:15pt;margin:20px 0 6px;padding-left:10px;border-left:4px solid #06B6D4;break-after:avoid}
h3{font-size:11pt;margin:14px 0 4px;color:#3B3FD8;break-after:avoid}
p{margin:6px 0}
ul{margin:4px 0 6px 18px;padding:0}li{margin:2px 0}
code{font-family:'DejaVu Sans Mono',monospace;font-size:8.2pt;background:#EEF2FF;padding:0 3px;border-radius:3px;color:#3730A3}
.cover{page-break-after:always;height:263mm;margin:-17mm -15mm -19mm;padding:34mm 22mm;color:#E6ECFF;background:radial-gradient(circle at 80% 12%,#2B2F8F 0,#0B1226 48%),#0B1226;position:relative;overflow:hidden}
.cover .k{letter-spacing:.35em;font-size:9pt;color:#22D3EE;font-weight:700}
.cover h1{font-size:46pt;line-height:1.05;margin:14px 0 10px;color:#fff;letter-spacing:-.02em}
.cover h1 span{background:linear-gradient(90deg,#22D3EE,#8B5CF6);-webkit-background-clip:text;color:transparent}
.cover .sub{font-size:14pt;color:#B8C6F2;max-width:140mm}
.cover .meta{position:absolute;left:22mm;bottom:26mm;font-size:9pt;color:#9FB0D8;line-height:1.7}
.cover svg{position:absolute;right:-10mm;bottom:40mm;width:150mm;opacity:.95}
.toc h2{border:none;padding:0;font-size:22pt}
.toc a{display:flex;gap:8px;color:#1B2540;text-decoration:none;padding:3.2px 0;border-bottom:1px dotted #CBD5E1;font-size:10pt}
.toc a b{color:#06B6D4;width:26px}.toc a span{flex:1}.toc a i{font-style:normal;color:#64748B}
section.ch{break-before:page}
.opener{margin:0 0 14px;padding:20px 22px;border-radius:14px;color:#E6ECFF;background:linear-gradient(120deg,#0B1226,#1B2A6B 70%,#4C1D95)}
.opener .cnum{font-size:9pt;letter-spacing:.3em;color:#22D3EE;font-weight:700}
.opener h1{font-size:23pt;color:#fff;margin:4px 0 4px;letter-spacing:-.01em}
.opener p{color:#B8C6F2;margin:0;font-size:10pt}
figure{margin:12px 0;break-inside:avoid}
figcaption{font-size:8.6pt;color:#475569;margin-top:5px}
figure .note{font-size:8.4pt;color:#64748B;margin-top:2px}
.landfig{margin:0 0 4px}
.b{display:inline-block;font-size:7.4pt;font-weight:700;padding:1px 7px;border-radius:99px;letter-spacing:.02em;vertical-align:1px;white-space:nowrap}
.impl{background:#DCFCE7;color:#166534}.opt{background:#FEF3C7;color:#92400E}.fut{background:#FFE4E6;color:#9F1239}
.un{background:#E2E8F0;color:#334155}.cn{background:#EDE9FE;color:#5B21B6}.ar{background:#DBEAFE;color:#1E40AF}.part{background:#FFEDD5;color:#9A3412}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:8.4pt;break-inside:auto}
th{background:#0B1226;color:#E6ECFF;text-align:left;padding:5px 7px;font-weight:600}
td{padding:4px 7px;border-bottom:1px solid #E2E8F0;vertical-align:top}
tr{break-inside:avoid}tr:nth-child(even) td{background:#F8FAFC}
.tcap{font-size:8.6pt;color:#475569;margin:10px 0 -4px}
.call{border-radius:10px;padding:8px 12px;margin:9px 0;font-size:9pt;border-left:4px solid;break-inside:avoid}
.call.info{background:#EFF6FF;border-color:#3B82F6}.call.warn{background:#FFFBEB;border-color:#D97706}.call.rule{background:#F5F3FF;border-color:#8B5CF6}
.wwh{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:8px 0;break-inside:avoid}
.wwh div{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:9px;padding:6px 8px;font-size:8.3pt}
.wwh div b{display:block;font-size:7.2pt;letter-spacing:.08em;color:#6D28D9;text-transform:uppercase;margin-bottom:1px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.stage{break-inside:avoid;border:1px solid #E2E8F0;border-radius:10px;margin:6px 0;overflow:hidden}
.stage .hd{background:linear-gradient(90deg,#0B1226,#25328A);color:#fff;font-weight:700;padding:4px 10px;font-size:9.4pt}
.stage .bd{display:grid;grid-template-columns:repeat(3,1fr);gap:0}
.stage .bd div{padding:4px 9px;font-size:8.1pt;border-right:1px solid #EEF2F7;border-top:1px solid #EEF2F7}
.stage .bd b{display:block;font-size:6.9pt;letter-spacing:.08em;color:#6D28D9;text-transform:uppercase}
.gl dt{font-weight:700;color:#3730A3;float:left;clear:left;width:36mm;font-size:8.8pt}.gl dd{margin:0 0 3px 38mm;font-size:8.8pt}
.small{font-size:8.5pt;color:#475569}
"""
def B(k,t=None):
    d={"impl":"Implemented","opt":"Optional","fut":"Future work","un":"Unspecified in report","cn":"Conceptual","part":"Partial"}
    return f'<span class="b {k}">{t or d[k]}</span>'
def OPEN(n,title,tag,land=False):
    return f'<section class="ch{" land" if land else ""}" id="c{n:02d}"><div class="opener"><div class="cnum">CHAPTER {n:02d}</div><h1>{esc(title)}</h1><p>{tag}</p></div>'
def P(t): return f'<p>{t}</p>'
def H2(t): return f'<h2>{t}</h2>'
def H3(t): return f'<h3>{t}</h3>'
def UL(items): return '<ul>'+''.join(f'<li>{i}</li>' for i in items)+'</ul>'
def CALL(k,t): return f'<div class="call {k}">{t}</div>'
def TBL(head,rows,cap,widths=None):
    TABN[0]+=1
    w=''.join(f'<col style="width:{x}">' for x in widths) if widths else ''
    return (f'<div class="tcap"><b>Table {TABN[0]}.</b> {esc(cap)}</div><table><colgroup>{w}</colgroup><thead><tr>'+''.join(f'<th>{h}</th>' for h in head)+'</tr></thead><tbody>'
        +''.join('<tr>'+''.join(f'<td>{c}</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table>')
def WWH(what,why,how,inp,proc,out,nxt):
    cells=[("What is it?",what),("Why required?",why),("How in RePersona?",how),("Enters",inp),("Processing",proc),("Output",out),("Used next by",nxt)]
    return '<div class="wwh">'+''.join(f'<div><b>{a}</b>{b}</div>' for a,b in cells)+'<div style="background:none;border:none"></div></div>'
def LAND(*parts): return '<div class="land">'+''.join(parts)+'</div>'
def END(): return '</section>'

def NL(*p): return ''.join(p)
