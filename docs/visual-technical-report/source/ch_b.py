from doc import *
def storyboard(comps,frames,title,sub,w=1000,band=52,dark=True,name="sb"):
    n=len(comps); h=62+band*len(frames)+10; s=Svg(w,h,dark,name); s.title(title,sub)
    cw=(w-50-300-(n-1)*8)/n; x0=50
    cx=lambda i:x0+i*(cw+8)
    for k,(a,b,cap) in enumerate(frames):
        y=58+k*band
        s.badge(26,y+22,str(k+1),C['violet'],11)
        for i,c in enumerate(comps):
            act=i in (a,b)
            s.box(cx(i),y+4,cw,36,c,None,C['cyan'] if act else C['grey'],tsize=9.5,op=.5 if act else .07,tcolor="#fff" if act else None)
        if a!=b:
            xa=cx(a)+cw/2; xb=cx(b)+cw/2
            s.arrow([(xa,y+46),(xb,y+46)],C['amber'],width=1.6)
            s.raw(f'<circle cx="{(xa+xb)/2:.1f}" cy="{y+46}" r="8" fill="{C["amber"]}" fill-opacity=".25"/><circle cx="{(xa+xb)/2:.1f}" cy="{y+46}" r="4.5" fill="{C["amber"]}"/>')
        s.text(w-290,y+19,cap,10.5,wrap=275,fill="#E6ECFF")
    return s
def ch04():
    h=OPEN(4,"Frontend to Backend Communication","The complete life of one API request — from a click to a re-rendered screen.",land=True)
    h+=P("Every user action that needs data follows the same path: a React event handler calls a function in the typed API layer, which sends an HTTP request to FastAPI; a router validates the input with Pydantic and hands it to a service; the service reads or writes the database and may call an AI provider; the structured result travels back as JSON and React re-renders.")
    lanes=[("User",C['cyan']),("Browser",C['cyan']),("React component",C['cyan']),("API layer (api.ts)",C['blue']),("FastAPI",C['violet']),("Router",C['violet']),("Service layer",C['violet']),("Database / vectors",C['teal']),("AI provider",C['rose'])]
    msgs=[(0,1,"click “Send”"),(1,2,"onClick handler"),(2,3,"sendChat(...)"),(3,3,"build JSON body"),(3,4,"POST /api/chat (HTTP)"),(4,5,"match endpoint"),(5,5,"Pydantic validation"),(5,6,"persona_reasoner.reason()"),(6,7,"load persona · persist msgs · retrieve"),(6,8,"guarded prompt"),(8,6,"answer text","res"),(6,5,"ChatResponse","res"),(5,3,"JSON response (HTTP)","res"),(3,2,"parsed typed result","res"),(2,0,"UI updates (answer + evidence)","res")]
    s=seq(lanes,msgs,1000,dark=True,row=31,top=62,name="seq4",title="Frontend-to-backend sequence — POST /api/chat",sub="Solid = request path · dashed = response path")
    h+=NL(fig(s,"Frontend-to-backend sequence diagram (chat request)",tag="a",land=True,note="Lanes follow the report's chat flow (§14). Which provider answers depends on LLM_PROVIDER; with the demo provider the composer runs inside the backend and no external call is made."))
    h+=H2("The 14 steps mapped to RePersona")
    h+=TBL(["#","Step","In RePersona"],[["1–2","User clicks; React handler runs","<code>ChatPanel</code> captures the typed question"],["3","Frontend API function","<code>sendChat()</code> in <code>lib/api.ts</code>"],["4","JSON request created","Common JSON headers; base URL from <code>NEXT_PUBLIC_API_BASE</code>"],["5","HTTP request sent","<code>POST /api/chat</code>"],["6–7","FastAPI receives; router matches","<code>routers/chat.py</code> under <code>/api</code>"],["8","Pydantic validates","Request contract in <code>schemas.py</code> (field list unspecified)"],["9","Service executes","Persona and session loaded; user message persisted; <code>persona_reasoner.reason()</code>"],["10","DB / AI accessed","Vector retrieval, optional current-context search, LLM or demo composer"],["11–12","Response built and returned","Assistant message persisted; typed <code>ChatResponse</code> as JSON"],["13–14","Frontend parses; React updates","<code>ChatPanel</code> renders answer; <code>EvidencePanel</code> renders evidence"]],"Request lifecycle mapped to project components",["8%","32%","60%"])
    fr=[(0,0,"User clicks Send."),(1,1,"ChatPanel captures the question."),(2,2,"API layer builds the JSON body."),(2,3,"Request travels to FastAPI."),(3,3,"Router receives /api/chat."),(3,4,"Persona Reasoner starts."),(4,5,"Database and vector retrieval are accessed."),(4,6,"LLM / composer generates the answer."),(3,2,"JSON response travels back."),(1,1,"Frontend displays answer + evidence.")]
    s=storyboard(["User","ChatPanel","api.ts","FastAPI /api/chat","Persona Reasoner","DB + vector store","LLM provider"],fr,"Animation storyboard — one chat request","Highlighted chips are active; the amber packet shows the data in motion",name="sb4")
    h+=NL(fig(s,"Animation storyboard: ten frames of the chat request",tag="a",land=True))
    h+=H2("Protocol concepts in this project")
    h+=TBL(["Concept","Explanation","RePersona use"],[["GET","Read-only; no body","Lists and detail views: <code>/api/personas</code>, <code>/api/personas/{id}/timeline</code>, <code>/api/health</code>"],["POST","Sends a JSON (or file) body to create or compute","<code>/api/chat</code>, <code>/api/personas/create</code>, <code>/api/personas/resolve</code>, uploads"],["PATCH / DELETE","Rename or remove","<code>/api/conversations/{id}</code>"],["JSON","Structured text format","Request/response bodies; mirrored in <code>types.ts</code>"],["Status codes","General HTTP semantics (2xx success, 4xx client error, 5xx server error)","Exact codes returned per route are <b>unspecified</b> in the report; failures surface as <code>ApiError</code>"],["Async","Long work does not block the response","Create returns persona + job; the build runs as an async task (Chapter 14)"],["Errors","Explicit, never faked","Missing OCR/PDF/transcription dependency → explicit API error"]],"HTTP concepts and how RePersona applies them",["16%","40%","44%"])
    s=Svg(680,200,name="http"); s.title("Anatomy of one exchange (conceptual)")
    s.box(20,55,300,125,"HTTP request","POST /api/chat\nHeaders: JSON content type\nBody: JSON question payload\n(field names unspecified)",C['blue'],ssize=10); s.box(360,55,300,125,"HTTP response","Status line (2xx on success)\nHeaders\nBody: JSON ChatResponse — answer, evidence, citations, warnings, reasoning",C['violet'],ssize=10)
    s.arrow([(322,100),(358,100)],label="→")
    h+=fig(s,"HTTP request and response anatomy",tag="c")+END(); return h

def ch05():
    h=OPEN(5,"Identity Resolution and Source Discovery","Choosing the right person, then finding material through official public APIs.")
    s=Svg(680,300,dark=True,name="ident"); s.title("From a typed name to collected source material")
    pos=chain(s,14,62,[("Search input","user types a name",C['cyan']),("POST /personas/resolve","identity.py",C['violet']),("Candidates","name · profession · years · portrait · summary",C['blue']),("User selects","avoid wrong person",C['cyan'])],150,78,16,tsize=10.5,ssize=8)
    chain(s,14,185,[("POST /personas/create","Persona(building) + Job(pending)",C['violet']),("Source discovery","source_discovery.py adapters",C['green']),("Validation","candidate checks",C['teal']),("Collected sources","rows in sources table",C['blue'])],150,78,16,tsize=10.5,ssize=8)
    s.arrow([(89,140),(89,152),(89,185)] if False else [(535,140),(535,162),(89,162),(89,185)],label="selected identity",seg=1)
    h+=fig(s,"Identity resolution and source discovery flow",tag="a")
    h+=P("Identity resolution is performed <i>before</i> deep ingestion so the user can avoid building a profile for the wrong person. The default live adapter uses <b>official public APIs</b> and does not bypass authentication, paywalls, robots restrictions or platform protections. If live discovery fails, the application can fall back to the bundled demo adapter.")
    h+=TBL(["Provider","Status","Actual role"],[["Wikipedia Action API","%s"%B("impl","Default · no key"),"Resolve titles, search names, article extracts"],["Wikimedia REST summary","%s"%B("impl","Default · no key"),"Concise summary and portrait/thumbnail URL"],["Wikiquote Action API","%s"%B("impl","Default · no key"),"Documented quotation pages when available"],["Tavily","%s"%B("opt","Optional"),"Supplementary authorised web sources; current-context search (<code>SEARCH_PROVIDER=tavily</code> + key)"],["SerpAPI","%s"%B("opt","Optional"),"Alternative web/news search and current context"],["YouTube Data API v3","%s"%B("opt","Optional"),"Discover interviews/talks; metadata is <b>not</b> treated as a transcript"],["NewsAPI","%s"%B("opt","Optional"),"Independent news view for current-context answers"],["Bundled demo adapter","%s"%B("impl","Fallback"),"Synthetic Osho demonstration corpus; works offline"]],"External providers — required versus optional",["24%","22%","54%"])
    h+=CALL("rule","<b>Rule:</b> a provider that is not configured is reported as such and skipped — never simulated as a successful result.")
    s=Svg(680,190,name="adapter"); s.title("Adapter design with fallback")
    s.box(20,60,180,80,"source_discovery","adapter-style interface",C['violet'],ssize=9); s.box(260,50,190,50,"Live adapter","Wikipedia · Wikiquote · Wikimedia",C['green'],ssize=9); s.box(260,115,190,50,"Demo adapter","bundled, synthetic, offline",C['blue'],ssize=9); s.box(500,50,160,50,"Optional providers","Tavily · SerpAPI · YouTube · News",C['amber'],ssize=8.5)
    s.arrow([(200,90),(260,75)]); s.arrow([(200,110),(260,140)],label="live fails",dashed=True,seg=0); s.arrow([(450,75),(500,75)],dashed=True)
    h+=fig(s,"Source-discovery adapters and fallback",tag="a")+END(); return h

def ch06():
    h=OPEN(6,"Multimodal Data Ingestion Pipeline","Six input types, one converged path into searchable evidence.")
    def LFIG():
        s=Svg(1000,560,dark=True,name="ingest"); s.title("Multimodal ingestion: every path ends as text, then chunks, embeddings and a vector index","Uploads use POST /api/personas/{id}/sources/upload or /sources/text")
        rows=[("A · Text",[("Clean","whitespace / noise"),("Split","sentences"),("Chunk","with overlap")],C['cyan']),
              ("B · Markdown",[("Read file","text / .md"),("Clean",""),("Chunk","")],C['cyan']),
              ("C · PDF",[("pypdf","extract text"),("Clean",""),("Chunk","")],C['blue']),
              ("D · Image",[("Pillow","load image"),("Tesseract OCR","text"),("Clean",""),("Chunk","")],C['teal']),
              ("E · Audio",[("Whisper-compat.","transcribe"),("Text",""),("Chunk","")],C['violet']),
              ("F · Video",[("FFmpeg","media processing"),("Audio extract",""),("Transcribe","Whisper-compat."),("Text processing","")],C['rose'])]
        for i,(lab,steps,col) in enumerate(rows):
            y=68+i*74; s.box(20,y,92,52,lab,None,col,tsize=11)
            for k,(t,sub) in enumerate(steps): s.box(136+k*128,y,112,52,t,sub or None,col,tsize=10,ssize=8.5)
            s.arrow([(112,y+26),(136,y+26)])
            for k in range(len(steps)-1): s.arrow([(248+k*128,y+26),(264+k*128,y+26)])
            xe=136+len(steps)*128-16; s.line(xe,y+26,690,y+26,col,True,1.4)
        s.line(690,94,690,464,C['cyan'],False,2)
        for k,(t,sub,col) in enumerate([("Source records","SHA-256 dedupe · storage.py",C['green']),("Chunks","with page / media timestamps",C['blue']),("Embeddings","normalised vectors",C['teal']),("Vector index","per-persona FAISS / memory",C['violet'])]):
            s.box(760,70+k*112,200,64,t,sub,col,ssize=9.5)
            if k: s.arrow([(860,70+(k-1)*112+64),(860,70+k*112)])
        s.arrow([(690,102),(760,102)],C['cyan'],label="converge")
        return LAND(fig(s,"Multimodal ingestion pipeline",tag="a",land=True,note="PDF extraction uses pypdf; image OCR uses Pillow + Tesseract; audio/video use Whisper-compatible packages and FFmpeg. If an optional dependency is missing, the API returns an explicit error instead of pretending extraction succeeded. Exact intermediate steps inside each library are not specified."))
    h+=H2("Stage-by-stage, in plain language")
    h+=UL(["<b>Storage & dedupe</b> — files are saved through <code>storage.py</code> (local or S3-compatible); a SHA-256 content hash prevents duplicate sources.","<b>Extraction</b> — turns a file into text. For images this is OCR (Pillow/Tesseract), not neural image understanding.","<b>Cleaning</b> — removes whitespace, wiki markup, reference artifacts and malformed fragments.","<b>Chunking</b> — groups whole sentences into overlapping pieces so context is not lost at boundaries.","<b>Embedding & indexing</b> — chunks become vectors and enter the persona's index."])
    S=["Stillness is not the absence of thought.","It is the quality of attention that remains when thinking slows.","Many traditions describe it as a skill that is practised, not merely believed.","Daily repetition is said to matter more than long, occasional sessions.","Writers often compare it to listening to a river without trying to stop the water."]
    s=Svg(680,330,name="chunk"); s.title("Worked example: one paragraph becomes overlapping chunks","Hypothetical text and illustrative parameters (2 sentences per chunk, 1 overlap). Real sizes are unspecified in the report.")
    cols=[C['blue'],C['violet'],C['teal'],C['amber'],C['rose']]
    for i,t in enumerate(S): s.box(20,60+i*34,640,28,f"S{i+1}  {t}",None,cols[i],tsize=9.5,op=.12)
    for k in range(4):
        x=20+k*162; s.box(x,246,150,62,f"Chunk {k+1}",f"S{k+1} + S{k+2}",cols[k],tsize=11,ssize=9.5)
        s.arrow([(x+75,230),(x+75,246)],dashed=True)
    s.text(20,324,"Overlap: each sentence after the first appears in two chunks, so boundary context survives retrieval.",9.5,fill=C['grey'])
    h+=fig(s,"Chunking example",tag="h")+LFIG()+END(); return h

def ch07():
    h=OPEN(7,"The 15-Stage Persona Build Pipeline","Coordinated by job_manager.py as an asynchronous task with persisted state.",land=True)
    s=Svg(1000,570,dark=True,name="p15"); s.title("The 15-stage persona build pipeline","Each stage emits a named SSE event and updates progress, current stage, statistics and errors")
    st=["Discover sources","Validate source candidates","Collect source data","Process documents","Process audio","Transcribe speech","Run OCR","Clean text","Run NLP analysis","Generate embeddings","Build vector index","Analyze communication & personality patterns","Construct persona profile","Validate evidence","Mark persona ready"]
    ph=[0,0,0,1,1,1,1,2,2,3,3,4,4,4,5]; pc=[C['green'],C['teal'],C['blue'],C['cyan'],C['violet'],C['rose']]; pn=["ACQUIRE","EXTRACT","PREPARE","INDEX","ANALYZE","FINISH"]
    cw,chh=170,100; pts=[]
    for i,t in enumerate(st):
        r,c=divmod(i,5); x=15+c*(cw+30); y=62+r*175
        s.box(x,y,cw,chh,t,pn[ph[i]],pc[ph[i]],tsize=11,ssize=8.5); s.badge(x+14,y+14,str(i+1),pc[ph[i]],10); pts.append((x,y))
    for i in range(14):
        (x1,y1),(x2,y2)=pts[i],pts[i+1]
        if (i+1)%5: s.arrow([(x1+cw,y1+chh/2),(x2,y2+chh/2)])
        else: s.arrow([(x1+cw/2,y1+chh),(x1+cw/2,y1+chh+37),(x2+cw/2,y1+chh+37),(x2+cw/2,y2)])
    s.legend(20,548,[(p,c) for p,c in zip(pn,pc)])
    h+=NL(fig(s,"Full 15-stage pipeline",tag="a",land=True,note="Phase grouping is an editorial aid; the report lists the stages but does not define phases."))
    h+=P("The pipeline does real work at each stage: it creates database source rows, chunks text, generates vectors, builds the per-persona index and derives analysis outputs. Where the report does not name the exact service or storage location, this chapter says <b>unspecified</b> rather than guessing.")
    U=B("un")
    D=[("Discover sources","Selected identity","Query the live adapter and any configured optional providers","<code>source_discovery.py</code>","Source candidate list","Persistence of candidates "+U,"Live failure → bundled demo adapter; unconfigured providers skipped and reported"),
    ("Validate source candidates","Candidate list","Checks before collection; criteria "+U+"; policy: no bypass of auth, paywalls or robots","Presumed <code>source_discovery.py</code> "+U,"Accepted candidates","—","Failure handling "+U),
    ("Collect source data","Validated candidates","Fetch summary, portrait URL, article text, sections as separate sources, Wikiquote quotations","<code>source_discovery.py</code>","Source records","<code>sources</code> rows; SHA-256 hash for dedupe","Fallback to demo adapter; unrecoverable errors recorded on the Job (FAILED)"),
    ("Process documents","Text / Markdown / PDF sources","Read text files; extract PDF text with pypdf","<code>ingest.py</code>","Raw text","Source + extraction metadata","Missing dependency → explicit error"),
    ("Process audio","Audio / video files","Media processing with FFmpeg to prepare audio","<code>ingest.py</code> / <code>media.py</code> (split "+U+")","Audio ready for transcription","File via <code>storage.py</code>","Missing FFmpeg → explicit error"),
    ("Transcribe speech","Prepared audio","Whisper-compatible transcription","<code>ingest.py</code> / <code>media.py</code>","Transcript text","Source text; media timestamps on chunks where available","Missing package → explicit error"),
    ("Run OCR","Image files","Pillow + Tesseract OCR","<code>media.py</code>","Text from images","Source text","Missing Tesseract/Pillow → explicit error"),
    ("Clean text","All extracted text","Remove noise, wiki markup, reference artifacts, malformed fragments","<code>nlp.py</code>","Cleaned text","Unspecified","Unspecified"),
    ("Run NLP analysis","Cleaned text","Sentence splitting, overlapping chunking, tokenization, keyword / keyphrase extraction","<code>nlp.py</code>","Chunks (+ keywords)","<code>chunks</code> rows","Unspecified"),
    ("Generate embeddings","Chunks","Sentence Transformers, else deterministic hashing / bag-of-words; normalised vectors","<code>embeddings.py</code>","Vectors","Held for the index; SQL persistence "+U,"Fallback to hashing vectorizer"),
    ("Build vector index","Vectors","FAISS if installed, else in-memory store; one index per persona","<code>vector_store.py</code> (<code>index_registry</code>)","Persona vector index","FAISS or memory; cached, rebuilt lazily","Fallback to in-memory store"),
    ("Analyze communication & personality patterns","Chunks","Topics, concepts, themes, viewpoints, style, co-occurrence graph","<code>persona_analysis.py</code>","Topics, graph nodes/edges, candidate insights","Topic, KnowledgeNode/Edge rows (presumed)","Unspecified"),
    ("Construct persona profile","Analysis outputs","Assemble profile and evidence-linked insights; timeline from lifespan and dated sources","<code>persona_analysis.py</code>, <code>timeline.py</code> "+U,"PersonaProfile, PersonaInsight","Database","Unspecified"),
    ("Validate evidence","Insights + supporting chunk refs","Documented claim without evidence is downgraded","<code>persona_analysis.py</code>","Validated insight classes DOCUMENTED / OBSERVED / INFERRED / UNKNOWN","Insight rows updated","Downgrade rather than fail"),
    ("Mark persona ready","Completed stages","Set final status; emit COMPLETED","<code>job_manager.py</code>","Ready persona + completed Job","<code>personas</code>, <code>jobs</code> (status names beyond pending "+U+")","Job FAILED event on error")]
    for i,d in enumerate(D):
        lab=["Enters","Processing","Service","Output","Stored","If it fails"]
        h+=f'<div class="stage"><div class="hd">{i+1:02d} · {d[0]}</div><div class="bd">'+''.join(f'<div><b>{lab[k]}</b>{d[k+1]}</div>' for k in range(6))+'</div></div>'
    s=Svg(680,230,name="job"); s.title("Job state lifecycle","Job rows are persisted, so late subscribers and polling clients recover the latest snapshot")
    s.box(20,70,120,50,"pending","Job created",C['grey']); s.box(190,70,150,50,"in progress","name unspecified · stage events",C['blue'],ssize=8.5); s.box(400,40,120,45,"COMPLETED","persona ready",C['green']); s.box(400,110,120,45,"FAILED","error stored",C['rose'])
    s.arrow([(140,95),(190,95)],label="start"); s.arrow([(340,85),(400,62)]); s.arrow([(340,105),(400,132)])
    s.arrow([(265,120),(265,170),(265,170)],dashed=True) if False else None
    s.text(20,190,"Each stage updates: progress · current stage · statistics · errors",10.5,fill=C['grey']); s.text(20,208,"Persona status: building → ready (name of failure state unspecified)",10.5,fill=C['grey'])
    h+=fig(s,"Job state lifecycle",tag="a")
    s=Svg(680,230,name="fb"); s.title("Error and fallback paths")
    for i,(a,b,c) in enumerate([("Live discovery fails","→ bundled demo adapter",C['green']),("Sentence Transformers unavailable","→ hashing / bag-of-words vectors",C['teal']),("FAISS unavailable","→ in-memory vector store",C['blue']),("OCR / PDF / transcription package missing","→ explicit API error, no fake text",C['rose']),("Optional provider not configured","→ skipped and reported",C['amber'])]):
        s.box(20,52+i*35,300,30,a,None,c,tsize=9.5); s.box(350,52+i*35,310,30,b,None,c,tsize=9.5); s.arrow([(322,67+i*35),(348,67+i*35)])
    h+=fig(s,"Fallback behaviours documented in the report",tag="a")+END(); return h
