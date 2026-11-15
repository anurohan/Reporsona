import sys,io,re,shutil
sys.path.insert(0,"/home/claude/rp")
from doc import *
import lib
from ch_a import ch01,ch02,ch03
from ch_b import ch04,ch05,ch06,ch07
from ch_c import ch08,ch09,ch10,ch11,ch12
from ch_d import ch13,ch14,ch15,ch16
from ch_e import ch17,ch18,ch19,ch20,ch21,ch22,back
from playwright.sync_api import sync_playwright
from pypdf import PdfReader,PdfWriter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DJ","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
TITLES=["Introduction to RePersona","Complete System Architecture","Frontend Deep Dive","Frontend to Backend Communication","Identity Resolution and Source Discovery","Multimodal Data Ingestion Pipeline","The 15-Stage Persona Build Pipeline","NLP Processing and Embeddings","Vector Database and FAISS","RAG Architecture — Complete Internal Working","Persona Reasoner and Temporal Intelligence","LLM and Ollama Architecture","Database and Data Persistence","Real-Time SSE Communication","API Architecture and Endpoint Reference","Complete End-to-End User Scenario","Deployment and Infrastructure","Security, Ethics and Reliability","Testing and Validation","Computer Vision and NLP Academic Mapping","Limitations and Future Roadmap","Final Technical Summary"]
def cover():
    import random; random.seed(7); g=''
    pts=[(random.randint(20,480),random.randint(20,330)) for _ in range(34)]
    for i,(x,y) in enumerate(pts):
        for (a,b) in pts[i+1:]:
            if (x-a)**2+(y-b)**2<7000: g+=f'<line x1="{x}" y1="{y}" x2="{a}" y2="{b}" stroke="#22D3EE" stroke-opacity=".35"/>'
    for x,y in pts: g+=f'<circle cx="{x}" cy="{y}" r="{random.choice([3,4,6])}" fill="{random.choice(["#22D3EE","#8B5CF6","#3B82F6"])}"/>'
    return f'<div class="cover"><svg viewBox="0 0 500 350">{g}</svg><div class="k">VISUAL TECHNICAL DOCUMENTATION</div><h1>Re<span>Persona</span></h1><div class="sub">An evidence-grounded AI research and conversation system — architecture, pipelines and reasoning explained visually.</div><div class="meta">Complete Visual Technical Report<br>Source of truth: RePersona Project Report<br>22 chapters · diagrams in SVG · companion interactive HTML</div></div>'
def toc(pages):
    t='<section class="toc"><h2>Contents</h2>'
    for i,n in enumerate(TITLES,1): t+=f'<a href="#c{i:02d}"><b>{i:02d}</b><span>{esc(n)}</span><i>{pages.get(i,"00")}</i></a>'
    t+='<a href="#gl"><b></b><span>Glossary, Abbreviations and References</span><i>%s</i></a>'%pages.get('gl','00')
    t+='<h2 style="font-size:13pt;margin-top:22px;border-left:4px solid #06B6D4;padding-left:10px">How to read the status badges</h2><p>'+' '.join([B('impl','Implemented'),B('opt','Optional'),B('part','Partial'),B('fut','Future work'),B('un'),B('cn','Conceptual')])+'</p>'
    t+=UL(["<b>Implemented</b> — described as present in the source report.","<b>Optional</b> — works only when configured or installed.","<b>Future work</b> — proposed, not existing.","<b>Conceptual / hypothetical</b> — illustrative data or wireframes; never real outputs or screenshots.","<b>Unspecified</b> — the source report does not state this detail, so it is not guessed."])
    t+='<p class="small">Companion file: <code>RePersona_Interactive_Architecture.html</code> animates the chat lifecycle, RAG, the 15-stage build and SSE progress. Chapter openers are compact banners rather than blank divider pages.</p></section>'
    return t
def page(pages):
    body=cover()+toc(pages)+''.join(f() for f in [ch01,ch02,ch03,ch04,ch05,ch06,ch07,ch08,ch09,ch10,ch11,ch12,ch13,ch14,ch15,ch16,ch17,ch18,ch19,ch20,ch21,ch22])+back()
    return f'<!doctype html><html><head><meta charset="utf-8"><title>RePersona — Complete Visual Technical Report</title><style>{CSS}</style></head><body>{body}</body></html>'
def render(html_s,path):
    open(OUT+"/report.html","w").write(html_s)
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(); pg.goto("file://"+OUT+"/report.html"); pg.wait_for_timeout(500)
        pg.pdf(path=path,prefer_css_page_size=True,print_background=True); b.close()
def find(path):
    r=PdfReader(path); res={}
    for i,pgx in enumerate(r.pages):
        t=pgx.extract_text() or ""
        for n in range(1,23):
            if f"CHAPTER {n:02d}" in t and n not in res and i>=2: res[n]=i+1
        if "REFERENCE" in t and "Glossary" in t and 'gl' not in res and i>=2: res['gl']=i+1
    return res,len(r.pages)
def stamp(src,dst,pages):
    r=PdfReader(src); w=PdfWriter(); N=len(r.pages); starts=sorted((v,k) for k,v in pages.items() if k!='gl')
    for i,pg in enumerate(r.pages):
        W,H=float(pg.mediabox.width),float(pg.mediabox.height)
        if i>0:
            buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(W,H)); c.setFont("DJ",7.5); c.setFillColorRGB(.4,.45,.55)
            ch=""
            for s,k in starts:
                if s<=i+1: ch=f"{k:02d} · {TITLES[k-1]}"
            if pages.get('gl') and i+1>=pages['gl']: ch="Glossary & References"
            c.drawString(40,H-30,"RePersona — Visual Technical Report"); c.drawRightString(W-40,H-30,ch)
            c.setStrokeColorRGB(.8,.85,.92); c.line(40,H-36,W-40,H-36); c.drawCentredString(W/2,22,f"{i+1} / {N}")
            c.save(); buf.seek(0); pg.merge_page(PdfReader(buf).pages[0])
        w.add_page(pg)
    for v,k in starts: w.add_outline_item(f"{k:02d} {TITLES[k-1]}",v-1)
    w.add_metadata({"/Title":"RePersona — Complete Visual Technical Report"})
    w.write(dst)
if __name__=="__main__":
    render(page({}),OUT+"/p1.pdf"); pages,n=find(OUT+"/p1.pdf"); print(pages,n)
    FIG=lib.FIGN[0]; 
    lib.FIGN[0]=0; lib.TABN[0]=0
    render(page(pages),OUT+"/p2.pdf"); pages2,n2=find(OUT+"/p2.pdf"); print(pages2==pages,n2)
    stamp(OUT+"/p2.pdf","/mnt/user-data/outputs/RePersona_Complete_Visual_Technical_Report.pdf",pages2)
    print("figs",FIG,"warn",lib.WARN)
