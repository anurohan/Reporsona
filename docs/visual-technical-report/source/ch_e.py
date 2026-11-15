from doc import *
def ch17():
    h=OPEN(17,"Deployment and Infrastructure","From a one-click local run to a production-style topology.")
    s=Svg(680,330,dark=True,name="compose"); s.title("Docker Compose architecture (docker-compose.yml)")
    s.zone(14,55,652,250,"docker compose network",C['blue'])
    s.box(30,90,170,90,"db","postgres:16-alpine · :5432 · health check · pgdata volume",C['blue'],ssize=8.5); s.box(255,90,180,90,"backend","Python 3.11 FastAPI · :8000 · LLM_PROVIDER=demo · VECTOR_DB=memory",C['violet'],ssize=8.5); s.box(480,90,170,90,"frontend","Next.js 14 production image · :3000 · 3-stage build",C['cyan'],ssize=8.5)
    s.box(30,215,170,60,"redis (commented out)","redis:7-alpine · :6379 · future Celery/RQ",C['amber'],dashed=True,ssize=8.5)
    s.arrow([(255,135),(200,135)],label="waits healthy"); s.arrow([(480,135),(435,135)],label="HTTP/JSON")
    s.text(255,215,"Default stack is deterministic: no Ollama or heavy neural packages.",9.5,fill="#9FB0D8",wrap=400)
    s.text(255,250,"OCR and Whisper system dependencies are NOT installed by default.",9.5,fill="#F5C26B",wrap=400)
    h+=fig(s,"Docker Compose architecture",tag="a")
    h+=TBL(["Mode","Database","Embeddings / vectors","Generation","Keys"],[["Local zero-config","SQLite","Hashing + memory store","Demo (or Ollama if installed)","None"],["Local enhanced","SQLite / PostgreSQL","Sentence Transformers + FAISS","Ollama / Llama","Optional"],["Docker Compose default","PostgreSQL","Memory store","Demo composer","None"],["Production-style","PostgreSQL","FAISS or external vector DB","Ollama / hosted compatible / other","As required"]],"Runtime choices by mode",["22%","16%","24%","24%","14%"])
    s=Svg(680,300,name="deploy"); s.title("Local versus production-style deployment")
    s.zone(10,50,320,235,"LOCAL",C['green']); s.zone(350,50,320,235,"PRODUCTION-STYLE (intended topology)",C['violet'])
    for i,(t,c) in enumerate([("Browser → Next.js dev/prod",C['cyan']),("FastAPI (venv)",C['violet']),("SQLite + local files",C['blue']),("hashing/FAISS · demo/Ollama",C['teal'])]): s.box(30,76+i*50,280,38,t,None,c,tsize=10)
    for i,(t,c) in enumerate([("Frontend: Vercel or Node host",C['cyan']),("Backend: container / Python host",C['violet']),("PostgreSQL · S3-compatible files",C['blue']),("FAISS / vector DB · model service",C['teal']),("Optional workers: Celery/RQ + Redis",C['amber'])]): s.box(370,70+i*42,280,34,t,None,c,tsize=10,dashed=(i==4))
    h+=fig(s,"Local and production-style deployment",tag="a",note="Production topology is the report's intended direction; worker queues are future architecture.")
    s=Svg(680,230,name="env"); s.title("Environment-variable flow","Names only — never values or secrets")
    s.box(14,60,150,80,"backend/.env","SOURCE_MODE · DEMO_MODE · DATABASE_URL · LLM_* · EMBEDDING_MODEL · VECTOR_DB · SEARCH_* · NEWS_API_KEY · YOUTUBE_API_KEY · CORS_ORIGINS",C['violet'],ssize=7.5); s.box(210,70,120,60,"config.py","settings",C['blue']); s.box(380,60,130,36,"Services","use settings",C['teal']); s.box(380,104,130,36,"/api/providers","status only",C['amber'])
    s.box(14,160,150,44,"frontend/.env.local","NEXT_PUBLIC_API_BASE",C['cyan'],ssize=8); s.box(210,165,120,34,"api.ts",None,C['cyan'])
    s.arrow([(164,100),(210,100)]); s.arrow([(330,95),(380,78)]); s.arrow([(330,110),(380,122)]); s.arrow([(164,182),(210,182)])
    s.text(540,90,"Keys stay server-side;",9.5,fill=C['grey']); s.text(540,104,"status endpoint exposes",9.5,fill=C['grey']); s.text(540,118,"configured / not configured.",9.5,fill=C['grey'])
    h+=fig(s,"Environment-variable flow",tag="a")+END(); return h

def ch18():
    h=OPEN(18,"Security, Ethics and Reliability","Provenance, labelling and honest failure.")
    s=Svg(680,380,dark=True,name="trust"); s.title("Trust and safety architecture")
    L=[("Evidence provenance","every EvidenceItem keeps source, URL, dates",C['green']),("Simulation labelling","UI notice + SIMULATED_PERSONA_RESPONSE",C['violet']),("Historical safeguard","knowledge boundary from death date/year",C['rose']),("No fabricated quotes","only source-quoted text is a quote",C['amber']),("Honest failure","unconfigured / failed providers reported, never faked",C['teal']),("Fallback generation","safe offline answer if the LLM fails",C['blue'])]
    s.box(250,160,180,60,"Answer","with evidence + limits",C['cyan'],tsize=14)
    pos=[(20,60),(250,60),(480,60),(20,270),(250,270),(480,270)]
    for (t,sub,c),(x,y) in zip(L,pos): s.box(x,y,180,66,t,sub,c,ssize=8.5)
    for (x,y) in pos: s.arrow([(x+90,y+66 if y<150 else y),(340,190)],dashed=True) if False else None
    for i,(x,y) in enumerate(pos): s.arrow([(x+90,y+66),(340,160)] if y<150 else [(x+90,y),(340,220)],C['cyan'],dashed=True)
    h+=fig(s,"Security and evidence-provenance architecture",tag="a")
    h+=TBL(["Concern","Documented handling"],[["Source traceability","Source records keep title, type, URL, publication date, content hash, extraction metadata; insights link to supporting chunks"],["Claims vs interpretation","Insights classed DOCUMENTED / OBSERVED / INFERRED / UNKNOWN; unsupported DOCUMENTED claims downgraded"],["Upload errors","Missing OCR / PDF / transcription dependency → explicit error"],["Current-context reliability","No provider → facts unavailable; provider errors surfaced; empty results stay empty; snippets keep URL, title, domain, date, retrieval time"],["Access restrictions","No bypass of authentication, paywalls, robots restrictions or platform protections"],["Secrets","Provider keys are server-side; <code>/api/providers</code> reports status without secrets"],["Account access","Authentication / authorization are <b>not implemented</b> — required before public exposure"]],"Safety measures and their documented basis",["26%","74%"])
    h+=CALL("warn","The bundled Osho demonstration corpus is synthetic, paraphrased material to exercise the flow. It is not authentic speech and must not be cited as such.")+END(); return h

def ch19():
    h=OPEN(19,"Testing and Validation","What exists today — and what is only suggested.")
    s=Svg(680,230,name="tests"); s.title("Existing backend test categories (backend/tests, run with pytest)")
    for i,t in enumerate(["API behavior","Source discovery","Demo pipeline","RAG retrieval","Persona reasoning","Question classification","Temporal safeguards","Upload handling"]): s.box(14+(i%4)*167,55+(i//4)*70,155,56,t,None,C['green'],tsize=11)
    s.text(20,205,"Regression test: offline composer selects the meditation sentence, not an unrelated fear sentence. Suite passed after that change.",9.5,fill=C['grey'],wrap=640)
    h+=fig(s,"Tested capability areas",tag="a")
    h+=TBL(["Area","Command"],[["Backend","<code>cd backend && pytest</code>"],["Frontend lint","<code>cd frontend && npm run lint</code>"],["Frontend build","<code>cd frontend && npm run build</code>"]],"Validation commands",["30%","70%"])
    h+=TBL(["Tested today","Suggested future tests"],[["Backend categories listed above","Browser-level frontend tests"],["Frontend lint / build commands","Accessibility audits"],["—","Retrieval quality evaluation; BLEU/ROUGE-style benchmarking (not implemented)"]],"Separation of existing and suggested validation",["50%","50%"])
    h+=CALL("warn","No coverage percentage, accuracy score or latency benchmark is reported in the source, so none is given here.")+END(); return h

def ch20():
    h=OPEN(20,"Computer Vision and NLP Academic Mapping","What the project demonstrates — and what it does not.")
    def matrix(name,title,cols,w=1000):
        pass
    s=Svg(680,420,name="cv"); s.title("Computer Vision syllabus mapping")
    s.text(20,60,"IMPLEMENTED",11,fill=C['green'],weight=700)
    for i,t in enumerate(["Image upload","OCR pipeline (Pillow / Tesseract)","Image-to-text evidence processing"]): s.box(20+i*215,70,205,46,t,None,C['green'],tsize=10)
    s.text(20,150,"NOT CURRENTLY IMPLEMENTED",11,fill=C['rose'],weight=700)
    for i,t in enumerate(["CNN training","ResNet / EfficientNet fine-tuning","Transfer learning","YOLO / SSD detection","Segmentation (U-Net, DeepLab)","Vision Transformers","VAE / GAN generation","CLIP retrieval","Grad-CAM / saliency"]): s.box(20+(i%3)*215,160+(i//3)*58,205,46,t,None,C['rose'],tsize=10,op=.07)
    s.text(20,372,"OCR converts pixels to text via a library; it is not custom CNN-based computer vision. Pixel-level preprocessing is indirect (library-internal).",9.5,fill=C['grey'],wrap=640)
    h+=fig(s,"Computer Vision syllabus mapping",tag="a")
    s=Svg(680,470,name="nlp2"); s.title("NLP syllabus mapping")
    s.text(20,60,"IMPLEMENTED",11,fill=C['green'],weight=700)
    for i,t in enumerate(["Text cleaning","Tokenization","Stop-word filtering","Chunking with overlap","Dense embeddings","Hashing / BoW fallback","Vector retrieval","Rule-based question classification","Persona-conditioned generation","Temporal reasoning"]): s.box(20+(i%4)*165,70+(i//4)*50,155,42,t,None,C['green'],tsize=9.5)
    s.text(20,200,"PARTIAL / THROUGH PRETRAINED MODELS",11,fill=C['amber'],weight=700)
    for i,t in enumerate(["Normalisation (no stemming/lemmatization)","BoW-style (no separate TF-IDF)","Transformers used via Ollama/Sentence Transformers"]): s.box(20+i*215,210,205,48,t,None,C['amber'],tsize=9.5)
    s.text(20,288,"NOT CURRENTLY IMPLEMENTED",11,fill=C['rose'],weight=700)
    for i,t in enumerate(["Word2Vec / GloVe","PCA / t-SNE","RNN / LSTM / GRU","Deep sentiment models","BLEU / ROUGE","Custom transformer training","Fine-tuning","Seq2seq + attention"]): s.box(20+(i%4)*165,298+(i//4)*50,155,42,t,None,C['rose'],tsize=9.5,op=.07)
    h+=fig(s,"NLP syllabus mapping",tag="a")
    s=Svg(680,300,dark=True,name="ext"); s.title("Actual capability versus potential extensions")
    s.box(20,60,300,200,"Actual today","OCR → text → NLP/RAG\nTranscription → text → NLP/RAG\nEmbeddings + retrieval\nClassification (rules)\nLLM generation + safeguards",C['green'],ssize=10.5); s.box(360,60,300,200,"Potential extensions (future)","Pretrained image classifier\nYOLO detection with boxes in evidence\nU-Net segmentation\nCLIP image-text retrieval\nGrad-CAM overlays in EvidencePanel",C['violet'],ssize=10.5)
    s.arrow([(322,160),(358,160)],dashed=True)
    h+=fig(s,"Capabilities versus proposed extensions",tag="a")
    h+=CALL("rule","The project does <b>not</b> implement every syllabus topic. Its strength is NLP/RAG; computer vision enters only as OCR-driven ingestion.")+END(); return h

def ch21():
    h=OPEN(21,"Limitations and Future Roadmap","A strong local/demo foundation; items below are proposals, not existing features.",land=True)
    s=Svg(1000,430,dark=True,name="road"); s.title("Roadmap (future work labelled as such)")
    cols=[("Current foundation",C['green'],["Offline demo mode","Evidence + provenance","Streamed 15-stage build","Temporal guardrails","Pluggable providers"]),("Short-term",C['cyan'],["Authentication & authorization","Rate limiting + request limits","Secure secret management","Frontend tests + accessibility"]),("Medium-term",C['violet'],["Worker queue (Celery/RQ + Redis)","Hybrid retrieval (BM25)","Reranking + citation alignment","Observability"]),("Long-term",C['amber'],["Contradiction detection","Source-quality scoring + review","Multilingual ingestion","Current-context verification"])]
    for i,(t,c,it) in enumerate(cols):
        x=20+i*243; s.box(x,60,225,40,t,None,c,tsize=12.5)
        for k,m in enumerate(it): s.box(x,112+k*58,225,48,m,None,c,tsize=10,op=.1,dashed=(i>0))
        if i: s.arrow([(x-18,80),(x,80)])
    s.legend(20,415,[("Existing",C['green']),("Proposed (dashed)",C['violet'])])
    h+=NL(fig(s,"Roadmap",tag="a",land=True,note="The assignment of items to short/medium/long term is an editorial suggestion; the report lists the improvements without time horizons."))
    h+=TBL(["Documented limitation / improvement","Status"],[["Authentication and authorization before public exposure",B("fut")],["Durable worker queue for horizontal scale",B("fut")],["Hybrid retrieval (explicit BM25 or search engine)",B("fut")],["Reranking models, answer-level citation alignment",B("fut")],["Contradiction detection across sources",B("fut")],["Source-quality scoring, human review",B("fut")],["Multilingual ingestion and semantic retrieval",B("fut")],["Tracing, metrics, alerting",B("fut")],["Gateway rate limiting and size limits (app middleware exists)",B("part","Partial")],["Browser-level frontend tests, accessibility audits",B("fut")],["Production secret manager and configuration",B("fut")],["Stronger current-context verification and freshness policy",B("fut")]],"Limitations from the source report",["78%","22%"])+END(); return h

def ch22():
    h=OPEN(22,"Final Technical Summary","One diagram for the whole system.",land=True)
    s=Svg(1000,560,dark=True,name="master"); s.title("Complete project master architecture")
    A=[("INPUT SOURCES","wiki · uploads · optional APIs",C['green']),("MULTIMODAL INGESTION","text · PDF · image · audio · video",C['teal']),("TEXT EXTRACTION","pypdf · OCR · transcription",C['teal']),("NLP PROCESSING","clean · tokenize · stop-words",C['blue']),("CHUNKING","sentence-bounded, overlap",C['blue']),("EMBEDDINGS","Sentence Transformers / hashing",C['violet']),("VECTOR INDEX","FAISS / memory per persona",C['violet']),("PERSONA ANALYSIS","topics · profile · graph",C['violet'])]
    B2=[("QUESTION CLASSIFICATION","rule-based",C['rose']),("RAG RETRIEVAL","top-K + rerank + diversity",C['cyan']),("TEMPORAL REASONING","historical reality guard",C['rose']),("LLM GENERATION","Ollama · compatible · demo",C['rose']),("EVIDENCE VALIDATION","citations · limits",C['green']),("STRUCTURED RESPONSE","JSON ChatResponse",C['cyan']),("NEXT.JS FRONTEND","ChatPanel · EvidencePanel",C['cyan'])]
    s.zone(14,52,972,220,"BUILD PATH (15 stages, async, streamed over SSE)",C['violet']); s.zone(14,290,972,200,"QUESTION PATH (POST /api/chat)",C['cyan'])
    for i,(t,sub,c) in enumerate(A):
        x=24+(i%4)*240; y=78+(i//4)*100; s.box(x,y,200,70,t,sub,c,tsize=11,ssize=9)
        if i%4<3: s.arrow([(x+200,y+35),(x+240,y+35)])
    s.arrow([(824,148),(824,165),(124,165),(124,178)])
    for i,(t,sub,c) in enumerate(B2):
        x=24+(i%4)*240; y=318+(i//4)*85; s.box(x,y,200,66,t,sub,c,tsize=10.5,ssize=9)
        if i%4<3 and i<6: s.arrow([(x+200,y+33),(x+240,y+33)])
    s.arrow([(824,384),(824,396),(124,396),(124,403)]) if False else s.arrow([(824,318+66),(824,402),(124,402),(124,403)]) if False else None
    s.arrow([(824,318+66),(824,393),(124,393),(124,403)])
    s.box(24,500,200,0,"",None) if False else None
    s.text(20,512,"Persistence: SQL database (records, history, jobs) · vector index (embeddings) · file/S3 storage. Index built in the build path feeds retrieval in the question path.",10,fill="#9FB0D8",wrap=950)
    s.arrow([(500,272),(500,290)],C['violet'],label="index + profile",dashed=True)
    h+=NL(fig(s,"Complete project master architecture",tag="a",land=True))
    h+=H2("Conclusion")
    h+=P("RePersona is best understood as a <b>source-aware persona research system</b>, not a generic chatbot. Its value is the whole chain: extraction, cleaning, chunking and indexing; profile and knowledge analysis; question classification; evidence retrieval; temporal and ethical guardrails; controlled generation; and an answer that always carries evidence, limits and an explanation. It runs offline for demonstration, degrades gracefully when optional components are missing, and keeps a clear line between documented evidence and generated simulation. The principal gaps before public deployment are authentication, durable workers and broader testing — all identified in Chapter 21.")+END(); return h

GL=[("RAG","Retrieval-Augmented Generation: retrieve evidence, then generate from it."),("Embedding","Normalised numeric vector representing a text chunk."),("Chunk","Sentence-bounded, overlapping piece of a source."),("FAISS","Library for similarity search over vectors."),("Ollama","Local runtime serving Llama models over HTTP."),("Llama","Language-model family (default llama3.2:3b)."),("SSE","Server-Sent Events: one-way server-to-browser event stream."),("EvidenceItem","Retrieved chunk plus provenance."),("Knowledge boundary","Cut-off derived from documented death date/year."),("Hashing vectorizer","Deterministic bag-of-words fallback embedder."),("OCR","Optical character recognition (Tesseract)."),("Pydantic","Python request/response validation (schemas.py).")]
AB=[("API","Application Programming Interface"),("CORS","Cross-Origin Resource Sharing"),("ER","Entity-Relationship"),("LLM","Large Language Model"),("NLP","Natural Language Processing"),("OCR","Optical Character Recognition"),("REST","Representational State Transfer"),("SSE","Server-Sent Events"),("UI","User Interface")]
def back():
    h='<section class="ch" id="gl"><div class="opener"><div class="cnum">REFERENCE</div><h1>Glossary, Abbreviations and References</h1><p>Terms used throughout this document.</p></div><h2>Glossary</h2><dl class="gl">'+''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in GL)+'</dl><h2>Abbreviations</h2><dl class="gl">'+''.join(f'<dt>{a}</dt><dd>{b}</dd>' for a,b in AB)+'</dl>'
    h+='<h2>References</h2>'+UL(["RePersona Project Report (supplied source of truth) and the repository files it cites: <code>README.md</code>, <code>ARCHITECTURE.md</code>, <code>SETUP.md</code>.","General background concepts (HTTP semantics, SSE, vector search) are standard and carry no project-specific claims."])+'</section>'
    return h
