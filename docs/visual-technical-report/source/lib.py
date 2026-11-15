import textwrap, html, os, re
OUT="/home/claude/rp"
C=dict(navy="#0B1226",navy2="#141E3F",ink="#1B2540",blue="#3B82F6",violet="#8B5CF6",cyan="#06B6D4",teal="#14B8A6",
       green="#16A34A",amber="#D97706",rose="#E11D48",grey="#64748B",line="#CBD5E1",soft="#F1F5F9")
WARN=[]
def esc(t): return html.escape(str(t),quote=False)
def _wrap(t,cw,width):
    n=max(3,int(width/cw)); out=[]
    for part in str(t).split("\n"): out+=textwrap.wrap(part,n,break_long_words=False) or [""]
    return out
class Svg:
    def __init__(s,w,h,dark=False,name=""):
        s.w,s.h,s.dark,s.name=w,h,dark,name; s.el=[]; s.cols=set()
        s.fg="#E6ECFF" if dark else C['ink']; s.mut="#9FB0D8" if dark else C['grey']
    def raw(s,x): s.el.append(x)
    def text(s,x,y,t,size=12,fill=None,anchor="start",weight=400,wrap=None,lh=1.28,mono=False,italic=False):
        lines=_wrap(t,size*(0.6 if weight>=600 else 0.56),wrap) if wrap else str(t).split("\n")
        fam=' font-family="DejaVu Sans Mono,monospace"' if mono else ''
        it=' font-style="italic"' if italic else ''
        for i,l in enumerate(lines):
            s.el.append(f'<text x="{x}" y="{y+i*size*lh:.1f}" font-size="{size}" fill="{fill or s.fg}" text-anchor="{anchor}" font-weight="{weight}"{fam}{it}>{esc(l)}</text>')
        return len(lines)*size*lh
    def box(s,x,y,w,h,title,sub=None,color=None,dashed=False,tsize=12.5,ssize=10,op=None,rx=10,tcolor=None):
        color=color or C['blue']; op=op or (0.22 if s.dark else 0.09)
        d=' stroke-dasharray="5 4"' if dashed else ''
        if s.dark: s.el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="none" stroke="{color}" stroke-width="6" stroke-opacity="0.18"/>')
        s.el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{color}" fill-opacity="{op}" stroke="{color}" stroke-width="1.6"{d}/>')
        tl=_wrap(title,tsize*0.6,w-12); sl=_wrap(sub,ssize*0.54,w-12) if sub else []
        th=len(tl)*tsize*1.22; sh=len(sl)*ssize*1.26; gap=3 if sl else 0
        if th+gap+sh>h-2: WARN.append(f"overflow {s.name}: {title}")
        y0=y+(h-(th+gap+sh))/2+tsize*0.9
        for i,l in enumerate(tl): s.el.append(f'<text x="{x+w/2}" y="{y0+i*tsize*1.22:.1f}" font-size="{tsize}" font-weight="700" fill="{tcolor or s.fg}" text-anchor="middle">{esc(l)}</text>')
        for i,l in enumerate(sl): s.el.append(f'<text x="{x+w/2}" y="{y0+th+gap+i*ssize*1.26+ssize*0.2:.1f}" font-size="{ssize}" fill="{s.mut}" text-anchor="middle">{esc(l)}</text>')
        return (x,y,w,h)
    def arrow(s,pts,color=None,label=None,dashed=False,seg=None,width=1.8,lsize=9.5,lside=0):
        color=color or (C['cyan'] if s.dark else C['grey']); s.cols.add(color)
        d="M"+" L".join(f"{x:.1f},{y:.1f}" for x,y in pts)
        da=' stroke-dasharray="6 4"' if dashed else ''
        if s.dark: s.el.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width+4}" stroke-opacity="0.15"/>')
        s.el.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da} marker-end="url(#ah{color[1:]})"/>')
        if label:
            if seg is None: seg=max(range(len(pts)-1),key=lambda i:abs(pts[i+1][0]-pts[i][0])+abs(pts[i+1][1]-pts[i][1]))
            (x1,y1),(x2,y2)=pts[seg],pts[seg+1]; mx,my=(x1+x2)/2,(y1+y2)/2+lside
            wd=len(label)*lsize*0.54+10
            bg=C['navy'] if s.dark else "#FFFFFF"
            s.el.append(f'<rect x="{mx-wd/2:.1f}" y="{my-lsize*0.95:.1f}" width="{wd:.1f}" height="{lsize*1.45:.1f}" rx="4" fill="{bg}" fill-opacity="0.92"/>')
            s.el.append(f'<text x="{mx:.1f}" y="{my+lsize*0.28:.1f}" font-size="{lsize}" fill="{color if not s.dark else "#BFD0FF"}" text-anchor="middle" font-weight="600">{esc(label)}</text>')
    def line(s,x1,y1,x2,y2,color=None,dashed=False,w=1.2):
        d=' stroke-dasharray="4 4"' if dashed else ''
        s.el.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color or (C["line"] if not s.dark else "#33406B")}" stroke-width="{w}"{d}/>')
    def badge(s,x,y,n,color=None,r=10):
        color=color or C['violet']
        s.el.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/><text x="{x}" y="{y+3.7}" font-size="{r*1.0:.0f}" fill="#fff" text-anchor="middle" font-weight="700">{esc(n)}</text>')
    def pill(s,x,y,t,color=None,size=9.5,anchor="start"):
        color=color or C['blue']; wd=len(t)*size*0.58+14
        x0=x if anchor=="start" else x-wd/2
        s.el.append(f'<rect x="{x0:.1f}" y="{y-size-1}" width="{wd:.1f}" height="{size+7}" rx="{(size+7)/2}" fill="{color}" fill-opacity="0.16" stroke="{color}" stroke-width="1"/><text x="{x0+wd/2:.1f}" y="{y+3}" font-size="{size}" fill="{color if not s.dark else "#DCE6FF"}" text-anchor="middle" font-weight="600">{esc(t)}</text>')
        return wd
    def zone(s,x,y,w,h,label,color=None):
        color=color or C['grey']
        s.el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{color}" fill-opacity="{0.07 if s.dark else 0.05}" stroke="{color}" stroke-opacity="0.55" stroke-width="1.2" stroke-dasharray="3 5"/>')
        s.text(x+12,y+17,label,10.5,fill=color if not s.dark else "#A9BBEA",weight=700)
    def legend(s,x,y,items,size=10):
        for lab,col in items:
            s.el.append(f'<rect x="{x}" y="{y-9}" width="12" height="12" rx="3" fill="{col}" fill-opacity="0.35" stroke="{col}" stroke-width="1.4"/>')
            s.text(x+18,y+1,lab,size,fill=s.mut); x+=len(lab)*size*0.56+36
    def title(s,t,sub=None):
        s.text(20,26,t,15,weight=700)
        if sub: s.text(20,43,sub,10.5,fill=s.mut)
    def render(s,standalone=False):
        defs='<defs>'
        defs+='<linearGradient id="bgd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0B1226"/><stop offset="1" stop-color="#16214A"/></linearGradient>'
        for c in s.cols: defs+=f'<marker id="ah{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
        defs+='</defs>'
        bg=f'<rect width="{s.w}" height="{s.h}" rx="14" fill="{"url(#bgd)" if s.dark else "#FFFFFF"}" stroke="{"#24315F" if s.dark else C["line"]}"/>'
        dim=f'width="{s.w}" height="{s.h}"' if standalone else 'style="width:100%;height:auto;display:block"'
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s.w} {s.h}" {dim} font-family="Inter,DejaVu Sans,Arial,sans-serif">{defs}{bg}{"".join(s.el)}</svg>'

FIGN=[0]; TABN=[0]
def fig(s,title,tag=None,note=None,land=False):
    FIGN[0]+=1; n=FIGN[0]
    slug=re.sub(r'[^a-z0-9]+','_',title.lower())[:40].strip('_')
    open(f"{OUT}/diagrams/fig_{n:02d}_{slug}.svg","w").write(s.render(True))
    tg={"c":('Conceptual / illustrative','cn'),"w":('Conceptual wireframe — not a screenshot','cn'),"a":('Architecture','ar'),"h":('Hypothetical example data','cn')}.get(tag)
    tgh=f'<span class="b {tg[1]}">{tg[0]}</span> ' if tg else ''
    nt=f'<div class="note">{note}</div>' if note else ''
    return f'<figure class="{"landfig" if land else ""}">{s.render()}<figcaption><b>Figure {n}.</b> {esc(title)} {tgh}</figcaption>{nt}</figure>'

def chain(s,x,y,items,bw,bh,gap,vertical=False,arrows=True,labels=None,tsize=12,ssize=9.5,color=None):
    pos=[]
    for i,it in enumerate(items):
        t,sub,col=(list(it)+[None,None])[:3]
        bx,by=(x,y+i*(bh+gap)) if vertical else (x+i*(bw+gap),y)
        s.box(bx,by,bw,bh,t,sub,col or color,tsize=tsize,ssize=ssize); pos.append((bx,by))
    if arrows:
        for i in range(len(items)-1):
            (x1,y1),(x2,y2)=pos[i],pos[i+1]
            lab=labels[i] if labels and i<len(labels) else None
            if vertical: s.arrow([(x1+bw/2,y1+bh),(x2+bw/2,y2)],label=lab)
            else: s.arrow([(x1+bw,y1+bh/2),(x2,y2+bh/2)],label=lab)
    return pos

def seq(lanes,msgs,w,dark=False,row=34,top=62,name="seq",lsize=10,title=None,sub=None):
    n=len(lanes); m=34; sp=(w-2*m)/n; xs=[m+sp*(i+.5) for i in range(n)]
    h=top+row*len(msgs)+30; s=Svg(w,h,dark,name)
    if title: s.title(title,sub)
    hy=(50 if title else 14)
    for i,(nm,col) in enumerate(lanes):
        s.box(xs[i]-sp/2+4,hy,sp-8,38,nm,None,col,tsize=10.5 if sp>80 else 9.5)
        s.line(xs[i],hy+38,xs[i],h-14,dashed=True)
    y=hy+38+row*0.75
    for k,mg in enumerate(msgs):
        a,b,lab=mg[0],mg[1],mg[2]; kind=mg[3] if len(mg)>3 else "req"
        col=C['cyan'] if kind=="req" else (C['violet'] if kind=="res" else C['amber'])
        if not dark: col={"req":C['blue'],"res":C['violet'],"note":C['amber']}.get(kind,C['blue'])
        if a==b:
            s.arrow([(xs[a],y-8),(xs[a]+26,y-8),(xs[a]+26,y+6),(xs[a]+3,y+6)],col)
            s.text(xs[a]+32,y+1,lab,lsize,fill=s.fg)
        else:
            s.arrow([(xs[a],y),(xs[b],y)],col,label=lab,dashed=(kind=="res"),lsize=lsize,lside=-10)
        s.badge(18 if a>0 or True else 0,y,str(k+1),col,8)
        y+=row
    return s
