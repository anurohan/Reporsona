from doc import *
from ch_b import storyboard
def ent(s,x,y,w,name,fields,color,dashed=False):
    h=26+15*len(fields)+8
    s.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#fff" stroke="{color}" stroke-width="1.6"/><path d="M{x},{y+26} L{x},{y+8} Q{x},{y} {x+8},{y} L{x+w-8},{y} Q{x+w},{y} {x+w},{y+8} L{x+w},{y+26} Z" fill="{color}"/>')
    s.text(x+10,y+17,name,11.5,fill="#fff",weight=700)
    for i,f in enumerate(fields): s.text(x+10,y+42+i*15,f,9,fill=C['ink'])
    return h
def ch13():
    h=OPEN(13,"Database and Data Persistence","Relational records are stored in SQL; vectors live in a separate index.",land=True)
    h+=P("<code>models.py</code> (SQLAlchemy) holds the entities below. JSON columns store portable lists and structured metadata; foreign-key indexes and source content hashes support lookup, deduplication and caching. <b>Only attributes and relationships stated in the report are drawn</b>; dashed lines are links the report implies but does not detail.")
    s=Svg(1000,580,name="er"); s.title("Database ER diagram (report-documented attributes only)")
    ent(s,390,60,220,"Persona",["profile metadata","dates (life span)","knowledge cutoff","status","demo flag"],C['violet'])
    ent(s,30,60,220,"Source",["title","type","URL","publication date","content hash (SHA-256)","extraction metadata"],C['blue'])
    ent(s,30,230,220,"Chunk",["searchable text","page","media timestamps"],C['teal'])
    ent(s,30,400,220,"PersonaInsight",["claim / observation","class: DOCUMENTED · OBSERVED","· INFERRED · UNKNOWN","supporting chunk refs"],C['rose'])
    ent(s,390,230,220,"ChatSession",["conversation (per persona)","title (renamable)"],C['green'])
    ent(s,390,330,220,"ChatMessage",["message content","generated-answer metadata"],C['green'])
    ent(s,390,430,220,"Job",["status","progress","current stage","statistics · errors"],C['amber'])
    ent(s,750,60,220,"Topic",["topic information","weights"],C['cyan'])
    ent(s,750,150,220,"PersonaProfile",["communication style","known domains · concepts","viewpoints","uncertainties"],C['violet'])
    ent(s,750,290,220,"KnowledgeNode",["graph node"],C['teal'])
    ent(s,750,365,220,"KnowledgeEdge",["graph relationship"],C['teal'])
    ent(s,750,450,220,"User",["reserved for account-level","expansion (no links described)"],C['grey'])
    s.arrow([(390,100),(250,100)],C['violet'],label="1 : N"); s.arrow([(140,190),(140,230)],C['blue'],label="1 : N")
    s.arrow([(140,400),(140,313)],C['rose'],label="evidence refs",dashed=False); s.arrow([(500,175),(500,230)],C['green'],label="1 : N"); s.arrow([(500,296),(500,330)],C['green'],label="1 : N")
    s.arrow([(610,150),(700,150),(700,490),(610,490)],C['amber'],dashed=True,label="build progress (link unspecified)",seg=1,lside=0)
    for yy in (95,130,170): pass
    s.arrow([(610,100),(750,90)],C['grey'],dashed=True); s.arrow([(610,120),(750,185)],C['grey'],dashed=True); s.arrow([(610,140),(750,310)],C['grey'],dashed=True)
    s.arrow([(860,365),(860,330)],C['teal'],dashed=True,label="edge ↔ node")
    s.legend(30,560,[("Documented link",C['violet']),("Implied / presumed (dashed)",C['grey'])])
    h+=NL(fig(s,"Entity-relationship diagram",tag="a",land=True,note="Column names are not given in the report; entries are descriptive attribute groups, not literal column names."))
    s=Svg(680,300,name="life"); s.title("Data lifecycle: how a persona is stored")
    chain(s,10,60,[("create",None,C['cyan']),("Persona + Job",None,C['violet']),("Sources",None,C['blue']),("Chunks",None,C['teal']),("Topics · Profile · Insights · Graph",None,C['rose'])],118,64,20,tsize=10)
    s.box(20,170,300,50,"Relational DB (SQLite / PostgreSQL)","records, history, job state",C['blue'],ssize=9); s.box(360,170,300,50,"Vector index (FAISS / memory)","embeddings only — rebuilt lazily",C['violet'],ssize=9)
    s.text(20,255,"Chat: user message persisted → reasoner runs → assistant message persisted (with answer metadata).",10,fill=C['grey'])
    s.text(20,273,"Files: local storage or S3-compatible via storage.py; content-hash dedupe.",10,fill=C['grey'])
    h+=fig(s,"Persistence lifecycle",tag="a")+END(); return h

def ch14():
    h=OPEN(14,"Real-Time SSE Communication","Streaming build progress without inventing it.")
    h+=P("<b>Server-Sent Events</b> keep one HTTP response open so the server can push text events to the browser. A normal response returns once and closes; SSE streams many events over one connection in one direction (server → client). RePersona uses it because a persona build is long-running and the user should watch real stage changes.")
    lanes=[("useJobStream",C['cyan']),("EventSource",C['cyan']),("GET /jobs/{id}/stream",C['violet']),("Job manager",C['violet']),("Build stage",C['teal'])]
    msgs=[(0,1,"open stream"),(1,2,"GET (SSE)"),(2,3,"read persisted Job"),(3,2,"state","res"),(2,1,"SNAPSHOT","res"),(4,3,"stage change"),(3,2,"named stage event","res"),(2,1,"event: stage","res"),(1,0,"state update","res"),(2,1,"PING keep-alive","res"),(2,1,"COMPLETED / FAILED","res"),(0,0,"navigate or show error")]
    s=seq(lanes,msgs,680,row=30,name="seqsse",title="SSE communication sequence")
    h+=fig(s,"Server-Sent Events sequence",tag="a")
    fr=[(0,1,"EventSource opens the stream."),(1,2,"Backend sends a SNAPSHOT of persisted state."),(3,2,"Stage 1 starts; named event streamed."),(2,0,"Frontend updates progress and activity feed."),(3,2,"Further stage events … stage 15."),(2,0,"COMPLETED received; UI navigates to persona.")]
    s=storyboard(["useJobStream","EventSource","SSE endpoint","Job manager"],fr,"SSE storyboard","Packets show events moving toward the browser",w=680,band=54,name="sbsse",dark=True)
    h+=fig(s,"SSE animation storyboard",tag="a")
    s=Svg(680,330,dark=True,name="bars"); s.title("Progress bar across the 15 stages","Three conceptual moments in one build")
    for r,(lab,n) in enumerate([("Early (stage 3 active)",3),("Mid (stage 9 active)",9),("Done (COMPLETED)",15)]):
        y=70+r*80; s.text(20,y,lab,10.5,fill="#9FB0D8")
        for i in range(15):
            col=C['green'] if i<n-1 or n==15 else (C['cyan'] if i==n-1 else "#33406B")
            s.raw(f'<rect x="{20+i*42}" y="{y+10}" width="38" height="22" rx="5" fill="{col}" fill-opacity="{0.9 if col!="#33406B" else 0.6}"/>'); s.text(39+i*42,y+25,str(i+1),9,anchor="middle",fill="#fff")
    h+=fig(s,"Progress visualisation",tag="c")
    h+=TBL(["Event","Meaning"],[["SNAPSHOT","Current persisted state; lets late subscribers recover"],["Named stage events","One per pipeline stage; update progress, stage and statistics"],["PING","Keep-alive so the connection is not closed as idle"],["COMPLETED","Build finished; UI navigates to the ready persona"],["FAILED","Build failed; error shown"]],"SSE event types",["26%","74%"])
    h+=H2("Honest progress")
    h+=P("<code>useJobStream</code> derives activity-feed entries <b>only</b> from actual backend stat changes and stage transitions. If SSE is unavailable or fails before completion, it falls back to polling <code>GET /api/jobs/{id}</code>; the persisted job state keeps both paths consistent. Polling interval is <span class=\"b un\">unspecified</span>.")+END(); return h

def ch15():
    h=OPEN(15,"API Architecture and Endpoint Reference","Every documented route, its purpose and its frontend consumer.")
    h+=P("Request and response <b>schemas are defined in <code>schemas.py</code> but their fields are not reproduced in the source report</b>, so only overviews are given. “Frontend use” marked * is presumed from the page descriptions.")
    R=[("/api/personas/resolve","POST","Find candidate identities","Name in → candidate list (name, profession, years, portrait, summary)","Identity step (<code>api.ts</code> resolve)"),
    ("/api/personas/create","POST","Create persona, start async build","Selection in → persona summary + job","Search/identity flow"),
    ("/api/personas","GET","List personas","List of persona summaries","explore page*"),
    ("/api/personas/{id}","GET","Completed profile and summary","Profile data","Persona overview page"),
    ("/api/personas/{id}","DELETE","Delete persona (router lists delete)","—","<span class='b un'>Unspecified</span>"),
    ("/api/personas/{id}/sources","GET","Source records and provenance","Source list","sources page"),
    ("/api/personas/{id}/sources/text","POST","Add pasted evidence","Text in → new source","sources page"),
    ("/api/personas/{id}/sources/upload","POST","Upload text/MD/PDF/image/audio/video","File in → source or explicit error","sources page"),
    ("/api/personas/{id}/topics","GET","Topics and weights","Topic list","knowledge page*"),
    ("/api/personas/{id}/insights","GET","Evidence-linked insights","Insight list with class","insights page"),
    ("/api/personas/{id}/knowledge-graph","GET","Nodes and relationships","Graph data","<code>KnowledgeGraph3D</code>"),
    ("/api/personas/{id}/timeline","GET","Documented life/source events","Timeline events","<code>Timeline</code>"),
    ("/api/personas/{id}/coverage","GET","Coverage estimate and gaps","Facet estimates + suggestions","<code>Coverage</code>"),
    ("/api/chat","POST","Ask a question","Question in → answer, evidence, citations, warnings, reasoning","<code>ChatPanel</code> via <code>sendChat()</code>"),
    ("/api/conversations","GET","List a persona's conversations","Session list","chat page*"),
    ("/api/conversations/{id}","GET","One conversation with messages","Session + messages","chat page*"),
    ("/api/conversations/{id}","PATCH / DELETE","Rename / delete","—","conversation management"),
    ("/api/jobs/{id}","GET","Poll build status","Job snapshot","<code>useJobStream</code> fallback"),
    ("/api/jobs/{id}/stream","GET (SSE)","Stream build events","SNAPSHOT, stage events, PING, COMPLETED/FAILED","<code>useJobStream</code>"),
    ("/api/providers","GET","Provider configured / not configured (no secrets)","Status list","settings page"),
    ("/api/health","GET","Backend, LLM, embedding, vector-store state","Status","Health display*"),
    ("/api/ethical-notice","GET","Simulation and source-use notice","Notice text","<code>EthicalNotice</code>*")]
    h+=TBL(["Endpoint","Method","Purpose","Request / response overview","Used in frontend"],[[f"<code>{a}</code>",b,c,d,e] for a,b,c,d,e in R],"Documented RePersona endpoints",["25%","9%","20%","26%","20%"])
    s=Svg(680,260,name="apigrp"); s.title("API router groups under /api")
    G=[("personas.py","resolve · create · list · detail · sources · topics · insights · graph · timeline · coverage",C['violet']),("uploads.py","sources/text · sources/upload",C['teal']),("jobs.py","job · job stream (SSE)",C['amber']),("chat.py","chat",C['rose']),("conversations.py","list · detail · rename · delete",C['green']),("providers.py · health.py","providers · health (+ ethical notice)",C['blue'])]
    for i,(t,sub,c) in enumerate(G): s.box(14+(i%3)*220,55+(i//3)*100,208,86,t,sub,c,ssize=8.5)
    h+=fig(s,"API communication map",tag="a",note="The router that serves /api/ethical-notice is not named in the report.")+END(); return h

def ch16():
    h=OPEN(16,"Complete End-to-End User Scenario","Twenty steps from opening the app to reading a cited answer.",land=True)
    s=Svg(1000,570,dark=True,name="e2e"); s.title("End-to-end user journey: exploring a historical personality")
    T=[("Open RePersona","landing page"),("Search for a personality","explore"),("Resolve identity","POST /personas/resolve"),("Start persona build","POST /personas/create"),("Backend creates a Job","Persona(building) · Job(pending)"),("SSE starts streaming","GET /jobs/{id}/stream"),("Sources are collected","discovery adapters"),("Documents are processed","ingest · OCR · transcription"),("NLP and embeddings run","nlp.py · embeddings.py"),("FAISS index is built","vector_store.py"),("Persona profile constructed","persona_analysis"),("Evidence is validated","unsupported claims downgraded"),("Persona becomes ready","COMPLETED → navigate"),("User asks a question","ChatPanel → POST /api/chat"),("RAG retrieves evidence","top-K + rerank"),("Reasoner checks time","temporal.py · classifier"),("LLM generates response","Ollama · compatible · demo"),("Backend returns response","structured ChatResponse"),("Frontend displays answer","ChatPanel"),("EvidencePanel shows sources","evidence · limitations")]
    cw,chh=225,78; pts=[]
    for i,(t,sub) in enumerate(T):
        r,c=divmod(i,4); x=12+c*(cw+25); y=58+r*101
        col=C['cyan'] if i<4 else (C['violet'] if i<13 else (C['rose'] if i<17 else C['green']))
        s.box(x,y,cw,chh,t,sub,col,tsize=11.5,ssize=9); s.badge(x+16,y+16,f"{i+1:02d}",col,11); pts.append((x,y))
    for i in range(19):
        (x1,y1),(x2,y2)=pts[i],pts[i+1]
        if (i+1)%4: s.arrow([(x1+cw,y1+chh/2),(x2,y2+chh/2)])
        else: s.arrow([(x1+cw/2,y1+chh),(x1+cw/2,y1+chh+11),(x2+cw/2,y1+chh+11),(x2+cw/2,y2)])
    s.legend(20,552,[("Discover",C['cyan']),("Build (steps 5–13)",C['violet']),("Reason & generate",C['rose']),("Deliver",C['green'])])
    h+=NL(fig(s,"End-to-end user journey",tag="a",land=True))
    h=h.replace("</div>","</div>",1)
    h+=P("Steps 07–12 correspond to pipeline stages 3–14 described in Chapter 7. Steps 15–17 are the RAG, temporal and generation stages of Chapters 10–12. The scenario works offline using the bundled synthetic demo persona.")+END(); return h
