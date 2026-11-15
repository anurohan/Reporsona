from doc import *
def ch01():
    h=OPEN(1,"Introduction to RePersona","An evidence-grounded research and conversation system — not a generic chatbot.")
    h+=P("RePersona lets a user search for a public or historical person, build a documented profile from available source material, inspect the evidence and derived knowledge, and ask questions through a <b>clearly labelled persona simulation</b>. It does not claim to recreate a person's consciousness: it builds a <i>limited simulation from collected material</i>, and every answer is intended to be traceable to retrieved evidence.")
    h+=H2("The problem it solves")
    h+=P("A plain chatbot answers from opaque model memory, can invent quotations, and has no notion of what a person could have known during their lifetime. RePersona addresses this by retrieving evidence first, applying temporal safeguards, and returning the answer together with sources, limitations and a reasoning trace.")
    s=Svg(680,330,dark=True,name="eco"); s.title("RePersona ecosystem overview","Who and what interacts with the system")
    s.box(20,70,120,60,"User","browser",C['cyan']); s.box(20,200,120,60,"Uploads","text · PDF · image · audio · video",C['teal'],ssize=8.5)
    s.box(200,100,170,130,"RePersona","Next.js frontend\n+ FastAPI backend",C['violet'],tsize=14)
    s.box(450,48,200,50,"Public sources","Wikipedia · Wikimedia · Wikiquote",C['green'],ssize=8.5)
    s.box(450,112,200,50,"Optional providers","Tavily · SerpAPI · YouTube · NewsAPI",C['amber'],ssize=8.5)
    s.box(450,176,200,50,"Storage","SQL DB · files / S3 · vector index",C['blue'],ssize=8.5)
    s.box(450,240,200,50,"Answer generator","Ollama / Llama · compatible API · offline",C['rose'],ssize=8.5)
    s.arrow([(140,100),(200,140)],label="questions"); s.arrow([(200,200),(140,225)],label=None,dashed=True); s.arrow([(140,230),(200,200)],label="evidence")
    for yy in (73,137,201,265): s.arrow([(370,165),(450,yy)] ,dashed=(yy==137))
    s.legend(20,318,[("Required / default",C['green']),("Optional",C['amber']),("Core",C['violet'])])
    h+=fig(s,"RePersona ecosystem overview",tag="a")
    h+=H2("Traditional chatbot vs RePersona")
    s=Svg(680,330,name="cmp"); 
    s.box(20,20,300,36,"Generic chatbot",None,C['grey'],tsize=13)
    s.box(360,20,300,36,"RePersona",None,C['violet'],tsize=13)
    rows=[("Question → model memory → text","Question → retrieval of evidence → guarded prompt → text"),("Sources not shown","EvidenceItem objects with provenance and citations"),("May invent quotations","Generated text labelled SIMULATED_PERSONA_RESPONSE; never marked a verified quote"),("No time awareness","Knowledge boundary from documented death date/year"),("Failure = broken chat","Provider failure → safe offline answer, provider named in response")]
    for i,(a,b) in enumerate(rows):
        y=70+i*52; s.box(20,y,300,44,a,None,C['grey'],tsize=10,op=.05); s.box(360,y,300,44,b,None,C['violet'],tsize=10,op=.1); s.arrow([(322,y+22),(358,y+22)],C['cyan'])
    h+=fig(s,"Traditional chatbot versus RePersona",tag="a")
    h+=H2("Core features")
    h+=UL(["Identity resolution before ingestion, so the wrong person is not built.","Ingestion of pasted text, text/Markdown, PDF, image (OCR), audio and video (transcription).","A 15-stage persona build with persistent, streamed progress.","Derived profile, topics, insights, timeline, coverage estimate and knowledge graph.","Four response modes: evidence, persona simulation, historical, current context.","Evidence panel, citations, warnings and reasoning trace on every answer.","Runs fully offline in demo mode using a bundled <b>synthetic</b> demonstration corpus (not authentic transcripts)."])
    s=Svg(680,230,dark=True,name="hl"); s.title("High-level system overview")
    chain(s,20,70,[("Next.js frontend",None,C['cyan']),("FastAPI backend",None,C['violet']),("Services",None,C['blue']),("Data & AI stores",None,C['teal'])],140,56,32,labels=["REST + SSE","calls","reads / writes"])
    s.text(20,170,"Persistence · SQLite (default) or PostgreSQL · local or S3-compatible files · per-persona vector index",10.5,fill="#9FB0D8")
    s.text(20,190,"Generation · Ollama / OpenAI-compatible / offline demo composer",10.5,fill="#9FB0D8")
    h+=fig(s,"High-level two-tier architecture",tag="a")+END(); return h

def ch02():
    h=OPEN(2,"Complete System Architecture","A two-tier design: a Next.js UI over a FastAPI service layer.")
    h+=P("The frontend never talks to Wikipedia, Ollama or other providers. It talks only to the RePersona FastAPI API, which calls external providers when the configured workflow requires it. This keeps the REST contract stable while allowing models and providers to be replaced.")
    def LFIG():
        s=Svg(1000,560,dark=True,name="sys"); s.title("Figure — complete system architecture: request path and response path","Numbers follow one request from user click to rendered answer")
        s.zone(20,60,960,100,"FRONTEND TIER · Next.js 14 / React 18 / TypeScript",C['cyan']); s.zone(20,175,960,110,"BACKEND TIER · Python / FastAPI",C['violet']); s.zone(20,300,960,200,"DATA & AI RESOURCES",C['teal'])
        s.box(40,85,150,60,"User","browser",C['cyan']); s.box(260,85,200,60,"Next.js pages + components","App Router · ChatPanel · EvidencePanel",C['cyan'],ssize=9); s.box(530,85,200,60,"Typed API layer","lib/api.ts · types.ts",C['cyan'])
        s.box(40,205,170,60,"FastAPI app","main.py · middleware · CORS",C['violet'],ssize=9); s.box(260,205,200,60,"API routers (/api)","personas · jobs · chat · conversations · uploads · providers · health",C['violet'],ssize=8.5); s.box(530,205,230,60,"Services (business logic)","job_manager · rag_engine · persona_reasoner · ingest …",C['violet'],ssize=8.5)
        for i,(t,sub,c) in enumerate([("SQL database","SQLite / PostgreSQL",C['blue']),("File storage","local / S3-compatible",C['blue']),("Embeddings","Sentence Transformers / hashing",C['teal']),("Vector store","FAISS / in-memory",C['teal']),("LLM","Ollama · compatible · demo",C['rose'])]):
            s.box(40+i*186,350,166,64,t,sub,c,ssize=9)
        s.box(40,435,920,44,"Optional external providers","Tavily · SerpAPI · YouTube Data API · NewsAPI · Wikipedia/Wikimedia/Wikiquote (no key)",C['amber'],ssize=9.5)
        s.arrow([(190,115),(260,115)],label="1 click"); s.arrow([(460,115),(530,115)],label="2 fetch"); s.arrow([(630,145),(630,175),(125,175),(125,205)],label="3 HTTP+JSON",seg=1)
        s.arrow([(210,235),(260,235)],label="4"); s.arrow([(460,235),(530,235)],label="5"); s.arrow([(645,265),(645,300),(123,300),(123,350)],label="6 read/write",seg=1)
        s.arrow([(880,235),(960,235),(960,125),(730,125)],C['violet'],label="7 structured response",dashed=True,seg=1)
        s.arrow([(530,100),(460,100)],C['violet'],dashed=True)
        s.arrow([(260,100),(190,100)],C['violet'],label="8 render",dashed=True,lside=-8)
        s.legend(40,538,[("Request",C['cyan']),("Response",C['violet']),("Optional integration",C['amber'])])
        return LAND(fig(s,"Complete system architecture",tag="a",land=True))
    h+=H2("Responsibility of every major component")
    h+=TBL(["Component","Responsibility"],[["Next.js pages / components","Routing, rendering, interaction; chat, evidence, progress, timeline, coverage, 3D graph."],["Typed API layer (<code>lib/api.ts</code>)","Single fetch layer: JSON headers, base URL (<code>NEXT_PUBLIC_API_BASE</code>), <code>ApiError</code> conversion."],["FastAPI <code>main.py</code>","Creates the app, initialises the DB at startup, middleware, mounts routers under <code>/api</code>."],["Routers","HTTP route modules; one per resource group."],["Services","Business logic, ingestion, retrieval, analysis, reasoning, generation."],["SQL database","Personas, sources, chunks, profiles, insights, graph, jobs, chat history."],["Vector store","Per-persona similarity index (separate from the relational DB)."],["LLM / composer","Natural-language expression of retrieved evidence."]],"Responsibilities of major components",["30%","70%"])
    s=Svg(680,300,name="fe"); s.title("Frontend component architecture","Pages compose components; components use lib/ modules")
    s.zone(14,55,652,60,"App Router pages (src/app)",C['cyan'])
    for i,t in enumerate(["page.tsx","explore","build/[jobId]","[personaId]","…/chat","…/sources","…/knowledge","…/insights","settings"]): s.box(22+i*71,76,66,30,t,None,C['cyan'],tsize=8.5)
    s.zone(14,125,652,100,"Reusable components (src/components)",C['violet'])
    for i,t in enumerate(["ChatPanel","EvidencePanel","PipelineStages","ActivityFeed","Timeline","Coverage","PersonaImage","EthicalNotice"]): s.box(22+i*80,150,74,34,t,None,C['violet'],tsize=8.5)
    s.box(22,192,300,26,"three/KnowledgeGraph3D · three/ReconstructionScene","Three.js · React Three Fiber · Drei",C['teal'],tsize=8.5,ssize=7.5); 
    s.zone(14,235,652,55,"Libraries (src/lib)",C['blue'])
    for i,(t) in enumerate(["api.ts","types.ts","useJobStream.ts"]): s.box(22+i*150,252,140,28,t,None,C['blue'],tsize=10)
    s.arrow([(340,225),(340,235)],label=None)
    h+=fig(s,"Frontend component architecture",tag="a")
    s=Svg(680,330,name="be"); s.title("Backend service architecture and module dependencies","Dependencies point from caller to callee")
    s.box(20,55,640,36,"routers: personas · jobs · chat · conversations · uploads · providers · health",None,C['violet'],tsize=10.5)
    sv=[("job_manager",C['violet']),("source_discovery",C['green']),("identity",C['green']),("ingest",C['teal']),("media",C['teal']),("nlp",C['blue']),("embeddings",C['blue']),("vector_store",C['blue']),("rag_engine",C['violet']),("persona_reasoner",C['violet']),("persona_analysis",C['blue']),("current_context",C['amber']),("llm_provider",C['rose']),("temporal",C['rose']),("question_classifier",C['rose']),("timeline / coverage",C['blue']),("storage",C['teal'])]
    s.zone(14,105,652,160,"services/",C['blue'])
    for i,(t,c) in enumerate(sv): s.box(22+(i%6)*106,128+(i//6)*44,100,36,t,None,c,tsize=9)
    s.box(20,276,310,40,"models.py · schemas.py","SQLAlchemy · Pydantic",C['grey'],ssize=9); s.box(350,276,310,40,"config.py","environment-driven settings",C['grey'],ssize=9)
    s.arrow([(340,91),(340,105)]); s.arrow([(175,265),(175,276)])
    h+=fig(s,"Backend service architecture",tag="a",note="Service grouping by colour is an editorial aid; module-to-module call edges beyond those described in the report are not specified.")
    s=Svg(680,240,name="infra"); s.title("Infrastructure at a glance","Same code, different runtime choices (see Chapter 17)")
    s.box(20,60,200,150,"Local zero-config","SQLite · hashing vectors + memory store · demo composer · no keys",C['green'],ssize=9.5)
    s.box(240,60,200,150,"Docker Compose","PostgreSQL 16 · FastAPI · Next.js · memory store · demo provider",C['blue'],ssize=9.5)
    s.box(460,60,200,150,"Production-style","PostgreSQL · FAISS or external vector DB · Ollama / hosted model · S3 · optional Redis workers",C['violet'],ssize=9.5)
    h+=fig(s,"Infrastructure options",tag="a")+LFIG()+END(); return h

def ch03():
    h=OPEN(3,"Frontend Deep Dive","How the Next.js interface turns backend data into a research experience.")
    h+=P("The frontend uses Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Framer Motion, Lucide icons, Three.js, React Three Fiber and Drei. Page components never build URLs themselves; they call functions in <code>lib/api.ts</code> and render typed results.")
    s=Svg(680,170,dark=True,name="journey"); s.title("Visual journey through the application")
    chain(s,12,60,[("Landing","page.tsx",C['cyan']),("Search","explore",C['cyan']),("Identity pick","resolve",C['violet']),("Build progress","build/[jobId]",C['violet']),("Dashboard","[personaId]",C['blue']),("Sources / Knowledge","…/sources …/knowledge",C['teal']),("Chat","…/chat",C['rose'])],80,70,15,tsize=10,ssize=7.5)
    s.text(20,160,"Answer + EvidencePanel render inside the chat screen",10,fill="#9FB0D8")
    h+=fig(s,"Frontend user journey (route map)",tag="a")
    h+=P("The four wireframes below are <b>conceptual interface illustrations</b> of the screens the report describes. They are not screenshots and do not reproduce the real visual design.")
    s=Svg(680,520,name="wf")
    def frame(x,y,t,body):
        s.box(x,y,320,230,t,None,C['grey'],op=.04,tsize=10,rx=8); body(x,y)
    def w1(x,y):
        s.box(x+60,y+55,200,26,"Search a person…",None,C['cyan'],tsize=9); s.box(x+60,y+95,95,22,"Resolve",None,C['violet'],tsize=8.5)
        s.text(x+60,y+140,"Candidates (name · profession · years)",8.5); [s.box(x+60,y+148+i*24,200,20,f"Candidate {i+1}",None,C['grey'],tsize=8) for i in range(2)]
    def w2(x,y):
        for i in range(15): s.raw(f'<rect x="{x+14+i*20}" y="{y+50}" width="17" height="10" rx="2" fill="{C["violet"] if i<7 else C["line"]}"/>')
        s.text(x+14,y+82,"PipelineStages — 15 segments",8.5); s.box(x+14,y+95,170,110,"ActivityFeed","entries from real stage changes",C['teal'],tsize=9,ssize=8); s.box(x+196,y+95,110,110,"Stats","from backend job",C['blue'],tsize=9,ssize=8)
    def w3(x,y):
        s.box(x+12,y+42,80,60,"Portrait",None,C['cyan'],tsize=8.5); s.box(x+100,y+42,208,60,"Profile summary",None,C['violet'],tsize=9)
        for i,t in enumerate(["Timeline","Coverage","KnowledgeGraph3D"]): s.box(x+12+i*100,y+112,94,90,t,None,C['blue'],tsize=8.5)
    def w4(x,y):
        s.box(x+10,y+40,190,150,"ChatPanel","messages · mode · input",C['rose'],tsize=9,ssize=8); s.box(x+208,y+40,102,150,"EvidencePanel","sources · limitations",C['green'],tsize=8.5,ssize=7.5); s.box(x+10,y+196,190,24,"Type a question…",None,C['grey'],tsize=8)
    frame(10,10,"1 · Landing / Search",w1); frame(350,10,"2 · Build progress",w2); frame(10,260,"3 · Persona dashboard",w3); frame(350,260,"4 · Chat + evidence",w4)
    h+=fig(s,"Conceptual UI wireframes of four key screens",tag="w")
    h+=H2("How data reaches the screen")
    h+=UL(["<b>Typed fetch layer</b> — <code>api.ts</code> sends JSON requests and converts failures into <code>ApiError</code>; <code>types.ts</code> mirrors the Pydantic schemas.","<b>Chat</b> — <code>ChatPanel</code> calls <code>sendChat()</code>; the typed <code>ChatResponse</code> carries the answer, evidence, citations, warnings and reasoning. <code>EvidencePanel</code> renders the supporting material.","<b>Build progress</b> — <code>useJobStream</code> opens an <code>EventSource</code> on the job stream and updates React state; it falls back to polling.","<b>3D</b> — <code>KnowledgeGraph3D</code> and <code>ReconstructionScene</code> live under <code>components/three</code>, are dynamically loaded, quality-scaled and respect reduced-motion preferences.","<b>Motion</b> — Framer Motion handles interface animation."])
    h+=TBL(["Component","Role"],[["ChatPanel","Chat interaction and response presentation"],["EvidencePanel","Evidence, sources, provenance, limitations"],["PipelineStages","Build-stage progress"],["ActivityFeed","Source, document, embedding and milestone activity"],["Timeline","Documented timeline"],["Coverage","Coverage estimates and gaps"],["KnowledgeGraph3D","Interactive knowledge graph"],["ReconstructionScene","Visual persona reconstruction scene"],["EthicalNotice","Simulation and source-use notice"]],"Notable frontend components",["28%","72%"])
    h+=CALL("info","Internal implementation of React state variables inside each component is <b>not specified</b> in the source report, so it is not diagrammed here.")+END(); return h
