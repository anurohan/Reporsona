from doc import *
from ch_b import storyboard
def ch08():
    h=OPEN(8,"NLP Processing and Embeddings","From raw text to normalised numerical vectors.")
    h+=WWH("Turning messy text into clean, comparable pieces.","Source text contains markup, noise and variable length; retrieval needs consistent units.","<code>nlp.py</code> cleans, splits sentences, tokenizes, filters stop-words, extracts keywords and builds overlapping chunks.","Extracted text","Clean → split → tokenize → chunk","Chunks (+ keywords)","<code>embeddings.py</code>")
    s=Svg(680,260,name="nlp"); s.title("NLP processing pipeline","Hypothetical example sentence")
    items=[("Raw","“Stillness!! [1] is not the absence of thought.”",C['grey']),("Cleaned","Stillness is not the absence of thought.",C['blue']),("Tokens","stillness · is · not · the · absence · of · thought",C['violet']),("Stop-words removed","stillness · absence · thought",C['teal']),("Chunk","whole sentences + overlap",C['cyan'])]
    chain(s,12,60,items,120,100,12,tsize=10.5,ssize=8.5)
    s.text(20,195,"Stop-word lists are shared by keyword extraction, lexical embeddings and retrieval reranking.",10,fill=C['grey'])
    s.text(20,212,"Stemming / lemmatization: not implemented (normalisation only).",10,fill=C['rose'])
    h+=fig(s,"NLP processing pipeline with example",tag="h")
    h+=H2("Embeddings")
    h+=P("An <b>embedding</b> is a list of numbers that represents the meaning (or, for the fallback, the word content) of a text. Computers compare numbers, not meaning, so converting chunks to vectors makes <i>similarity</i> measurable. <code>embeddings.py</code> first tries <b>Sentence Transformers</b> (dense neural vectors); if the package or model is unavailable it uses a <b>deterministic hashing / bag-of-words</b> vectorizer. Both return <b>normalised</b> vectors through the same interface, so nothing downstream changes. The specific model named by <code>EMBEDDING_MODEL</code> and the vector dimension are not stated in the report.")
    s=Svg(680,230,dark=True,name="embgen"); s.title("Embedding generation with fallback")
    s.box(20,80,110,60,"Chunk text",None,C['cyan']); s.box(190,60,190,44,"Sentence Transformers","dense neural vectors",C['violet'],ssize=9); s.box(190,120,190,44,"Hashing / bag-of-words","deterministic fallback",C['amber'],ssize=9); s.box(450,80,110,60,"Normalise","unit-length",C['teal']); s.box(590,80,80,60,"Vector",None,C['green'])
    s.arrow([(130,100),(190,82)],label="try first"); s.arrow([(130,120),(190,142)],label="if missing",dashed=True); s.arrow([(380,82),(450,100)]); s.arrow([(380,142),(450,120)]); s.arrow([(560,110),(590,110)])
    s.text(20,205,"Hashing also represents unseen tokens deterministically (out-of-vocabulary handling by design).",10,fill="#9FB0D8")
    h+=fig(s,"Embedding generation and fallback",tag="a")
    s=Svg(680,330,dark=True,name="space"); s.title("Conceptual embedding space (2D)","Illustrative only — not real model output; real vectors have many more dimensions")
    import random; random.seed(3)
    cl=[("Meditation / attention",(170,170),C['cyan']),("Love / relationships",(470,130),C['violet']),("Society / politics",(430,250),C['amber'])]
    for n,(cx,cy),c in cl:
        s.raw(f'<ellipse cx="{cx}" cy="{cy}" rx="95" ry="58" fill="{c}" fill-opacity="0.08" stroke="{c}" stroke-dasharray="4 4"/>')
        for k in range(6): s.raw(f'<circle cx="{cx+random.randint(-70,70)}" cy="{cy+random.randint(-38,38)}" r="5" fill="{c}"/>')
        s.text(cx,cy+78,n,10.5,fill=c,anchor="middle",weight=700)
    s.raw(f'<circle cx="215" cy="150" r="8" fill="#fff" stroke="{C["green"]}" stroke-width="3"/>'); s.text(228,128,"question vector",10,fill="#fff",weight=700)
    s.text(20,318,"Semantically related chunks sit closer together; a question embedded nearby retrieves its neighbours.",10,fill="#9FB0D8")
    h+=fig(s,"Conceptual embedding-space illustration",tag="c")+END(); return h

def ch09():
    h=OPEN(9,"Vector Database and FAISS","Similarity search over chunk embeddings, one index per persona.")
    h+=P("Keyword search finds exact words; a question such as “how do I quiet my mind?” may never contain the word used in the source. Vector search compares <i>meaning-bearing numbers</i>, so related passages are found even with different wording. RePersona then adds a lexical rerank so exact topical overlap is not lost (Chapter 10).")
    s=Svg(680,300,dark=True,name="faiss"); s.title("FAISS retrieval in RePersona")
    chain(s,14,60,[("Persona documents",None,C['cyan']),("Chunk embeddings",None,C['teal']),("Index (FAISS / memory)","one per persona",C['violet'])],190,70,35,tsize=11,ssize=8.5)
    chain(s,14,180,[("User question → embedding",None,C['cyan']),("Similarity search",None,C['violet']),("Top-K chunks","K unspecified",C['green'])],190,70,35,tsize=11,ssize=8.5)
    s.arrow([(399,130),(399,155),(399,180)],label="query",dashed=True) if False else s.arrow([(309,130),(309,180)],label="searched by",dashed=True)
    h+=fig(s,"FAISS retrieval flow",tag="a")
    h+=TBL(["Concept","Meaning","Where it lives"],[["Original source","Whole document or article section","<code>sources</code> table"],["Chunk","Sentence-bounded piece of a source","<code>chunks</code> table"],["Embedding","Normalised vector of a chunk","Vector store input"],["Vector index","Searchable structure over all embeddings of one persona","FAISS or in-memory store; cached in <code>index_registry</code>, rebuilt lazily"],["Retrieved evidence","Chunk returned for a question, wrapped as an <code>EvidenceItem</code> with provenance","Part of the response"]],"Five related but different things",["20%","44%","36%"])
    h+=CALL("rule","The relational database and the vector index are <b>separate</b>: SQL stores records and history; the vector store only answers “which chunks are nearest to this query?”. FAISS is preferred when installed; otherwise a pure-Python in-memory store is used.")
    s=Svg(680,230,name="rank"); s.title("Conceptual similarity ranking","Bar length = relative similarity (illustrative, no real scores)")
    for i,(t,w) in enumerate([("Chunk about quieting the mind",430),("Chunk about attention and awareness",350),("Chunk about daily practice",250),("Chunk about economics",90)]):
        s.text(20,78+i*38,t,10.5); s.raw(f'<rect x="250" y="{62+i*38}" width="{w}" height="20" rx="5" fill="{C["violet"] if i<3 else C["line"]}" fill-opacity="{0.85-i*0.12}"/>')
    s.text(20,215,"Top-K keeps the highest-ranked chunks; the rest are discarded for this question.",10,fill=C['grey'])
    h+=fig(s,"Conceptual similarity ranking",tag="c")+END(); return h

def ch10():
    h=OPEN(10,"RAG Architecture — Complete Internal Working","Retrieve evidence first, then let the generator express it.")
    def LFIG():
        s=Svg(1000,470,dark=True,name="rag"); s.title("Complete RAG architecture (rag_engine.py + persona_reasoner.py)","Evidence is retrieved before any text is generated")
        st=[("User question","ChatPanel",C['cyan']),("Question embedding","embeddings.py",C['teal']),("Top-K vector search","vector_store.py",C['blue']),("Lexical reranking","exact topic overlap",C['blue']),("Source diversity","prefer varied sources",C['blue']),("EvidenceItems","with provenance",C['green'])]
        for i,(t,sub,c) in enumerate(st):
            s.box(20+i*162,80,142,70,t,sub,c,ssize=9); 
            if i: s.arrow([(20+(i-1)*162+142,115),(20+i*162,115)])
        s2=[("Persona-conditioned prompt","system rules · profile · evidence · history · language · mode",C['violet']),("LLM / offline composer","Ollama · compatible · demo",C['rose']),("Structured answer","answer + coverage + limitations",C['green']),("Citations & warnings","labels, reasoning trace",C['amber']),("Frontend display","ChatPanel + EvidencePanel",C['cyan'])]
        for i,(t,sub,c) in enumerate(s2):
            s.box(20+i*195,260,175,80,t,sub,c,ssize=8.5)
            if i: s.arrow([(20+(i-1)*195+175,300),(20+i*195,300)])
        s.arrow([(1000-85,150),(1000-85,205),(107,205),(107,260)],label="evidence handed to prompt",seg=1)
        s.box(20,380,960,60,"Safeguards around generation","Prompt forbids invented quotations, dates and events · says when evidence does not cover the question · generated text labelled SIMULATED_PERSONA_RESPONSE",C['rose'],ssize=10)
        return LAND(fig(s,"Full RAG architecture",tag="a",land=True))
    lanes=[("Frontend",C['cyan']),("POST /api/chat",C['violet']),("persona_reasoner",C['violet']),("rag_engine",C['blue']),("Vector store",C['teal']),("LLM provider",C['rose'])]
    msgs=[(0,1,"question"),(1,2,"reason()"),(2,3,"retrieve"),(3,4,"embed + top-K"),(4,3,"chunks","res"),(3,3,"rerank + diversity"),(3,2,"EvidenceItems","res"),(2,5,"guarded prompt"),(5,2,"text","res"),(2,1,"labels · citations · warnings","res"),(1,0,"ChatResponse","res")]
    s=seq(lanes,msgs,680,row=30,name="seqrag",title="RAG sequence diagram")
    h+=fig(s,"RAG sequence diagram",tag="a")
    h+=H2("Worked example (hypothetical data)")
    h+=P("<b>Hypothetical question:</b> “What does the persona say about meditation?” — the chunks below are invented for illustration only.")
    s=Svg(680,330,name="ragex"); s.title("Retrieval walk-through","All chunk texts and ranks are hypothetical")
    s.box(20,55,640,32,"Q: What does the persona say about meditation?",None,C['cyan'],tsize=11)
    ch=[("A · Source 1","“…attention that remains when thinking slows…”","rank 1 → kept",C['green']),("B · Source 1","“…listening to a river…”","rank 2 → dropped for diversity",C['amber']),("C · Source 2","“…daily practice matters more…”","rank 3 → kept",C['green']),("D · Source 3","“…markets and trade…”","low rank → discarded",C['grey'])]
    for i,(a,b,c,col) in enumerate(ch): s.box(20,108+i*52,200,44,a,None,col,tsize=10); s.box(235,108+i*52,260,44,b,None,col,tsize=9.5,op=.06); s.box(510,108+i*52,150,44,c,None,col,tsize=9,op=.12)
    s.box(20,320-18,0,0,"",None) if False else None
    s.text(20,322,"Kept evidence (A, C) feeds the prompt; the answer cites both and states limits.",10,fill=C['grey'])
    h+=fig(s,"Hypothetical retrieval and reranking example",tag="h")
    s=Svg(680,300,dark=True,name="ctx"); s.title("Prompt construction and context window","Conceptual layout of what the generator receives")
    s.zone(20,55,640,225,"CONTEXT WINDOW",C['violet'])
    for i,(t,sub,c) in enumerate([("System instructions","no literal identity · no invented quotes",C['rose']),("Persona profile","style · domains · concepts",C['violet']),("Retrieved evidence","EvidenceItem texts + provenance",C['green']),("Conversation history","recent turns",C['blue']),("Language + mode rules","English / Hindi / Hinglish · mode guardrails",C['amber']),("Current question",None,C['cyan'])]):
        s.box(35+(i%3)*205,80+(i//3)*95,190,78,t,sub,c,ssize=9)
    s.text(35,272,"Ordering and size limits of the real prompt are unspecified in the report.",9.5,fill="#9FB0D8")
    h+=fig(s,"Prompt and context-window illustration",tag="c")+LFIG()+END(); return h

def ch11():
    h=OPEN(11,"Persona Reasoner and Temporal Intelligence","A reasoning layer above basic RAG (persona_reasoner.py).")
    s=Svg(680,350,dark=True,name="reasoner"); s.title("Persona Reasoner — ten stages")
    L=["Detect intent","Classify question","Analyze temporal context","Retrieve persona evidence","Map worldview concepts","Choose answer mode","Retrieve current context if needed","Generate answer","Quotation & temporal safeguards","Reasoning trace & citations"]
    cs=[C['cyan'],C['cyan'],C['rose'],C['green'],C['violet'],C['violet'],C['amber'],C['rose'],C['rose'],C['green']]
    for i,t in enumerate(L):
        r,c=divmod(i,5); x=14+c*132; y=70+r*120
        s.box(x,y,116,76,t,None,cs[i],tsize=10.5); s.badge(x+12,y+12,str(i+1),cs[i],9)
        if i%5<4: s.arrow([(x+116,y+38),(x+132,y+38)])
    s.arrow([(14+4*132+58,146),(14+4*132+58,170),(14+58,170),(14+58,190)])
    s.text(20,330,"Output: answer + evidence + coverage + limitations + provider + category + current-context status + citations + warnings + cutoff + worldview concepts + reasoning object",9.5,fill="#9FB0D8",wrap=640)
    h+=fig(s,"Persona Reasoner architecture",tag="a")
    h+=TBL(["Question categories (rule-based classifier)","Examples of markers"],[["small talk · identity & biography · factual · quotation · historical · opinion","—"],["current politics / news / society / generic current events","“today”, “now”, “latest”, “currently”, “recent”, near-present years; Hinglish “aaj kal”, “abhi”"]],"Question classifier — rule-based, not deep learning",["50%","50%"])
    s=Svg(680,230,name="modes"); s.title("The four response modes")
    for i,(t,sub,c) in enumerate([("evidence","answer strictly from retrieved material",C['green']),("persona_simulation","first-person documented-perspective simulation",C['violet']),("historical","stay inside the historical period; ignore post-cutoff information",C['blue']),("current_context","fresh current facts + clearly labelled simulated worldview",C['amber'])]):
        s.box(14+i*165,60,155,110,t,sub,c,tsize=11,ssize=9)
    s.text(20,200,"Exact mode-selection rules are not specified beyond classification and temporal analysis.",10,fill=C['grey'])
    h+=fig(s,"Response modes",tag="a")
    h+=H2("Historical Reality Guard")
    h+=P("<code>temporal.py</code> derives a <b>knowledge boundary</b> from the documented death date or year. A question about an event after that boundary cannot be answered as historical memory; the system switches to a current-context or simulated-perspective path and says so.")
    s=Svg(680,300,dark=True,name="guard"); s.title("Historical Reality Guard timeline","Conceptual dates")
    s.line(40,150,640,150,C['cyan'],False,3)
    for x,t,c in [(60,"Birth",C['green']),(300,"Death = knowledge boundary",C['rose']),(600,"Present day",C['cyan'])]:
        s.raw(f'<circle cx="{x}" cy="150" r="8" fill="{c}"/>'); s.text(x,180,t,10.5,anchor="middle",weight=700)
    s.raw(f'<rect x="60" y="132" width="240" height="14" rx="7" fill="{C["green"]}" fill-opacity=".5"/>'); s.text(180,126,"Documented lifetime",10,anchor="middle",fill=C['green'])
    s.raw(f'<rect x="300" y="132" width="300" height="14" rx="7" fill="{C["amber"]}" fill-opacity=".35"/>'); s.text(450,126,"Beyond documented knowledge",10,anchor="middle",fill="#F5C26B")
    s.box(380,50,220,50,"Question about a post-lifetime event",None,C['amber'],tsize=10); s.arrow([(490,100),(490,128)],C['amber'])
    s.box(40,210,280,60,"Allowed","historical evidence inside the lifetime",C['green'],ssize=9); s.box(350,210,290,60,"Required path","current-context facts + generated perspective, labelled as NOT something the person knew or said",C['rose'],ssize=9)
    h+=fig(s,"Historical Reality Guard timeline",tag="c")
    h+=CALL("rule","<b>Why labels matter:</b> generated text is tagged <code>SIMULATED_PERSONA_RESPONSE</code> and is never marked as a verified historical quotation. Only evidence that comes from a quote source or is visibly quoted in the source material is identified as a quote.")+END(); return h

def ch12():
    h=OPEN(12,"LLM and Ollama Architecture","One frontend, interchangeable generators.")
    h+=TBL(["Term","Meaning"],[["LLM","A large neural language model that predicts text; here it <i>expresses</i> retrieved evidence, it is not the source of facts."],["Llama","The model <b>family</b> (default <code>llama3.2:3b</code>, set by <code>LLM_MODEL</code>)."],["Ollama","The local <b>runtime</b> that serves a Llama model over HTTP (normally <code>http://127.0.0.1:11434</code>)."]],"Llama versus Ollama",["18%","82%"])
    s=Svg(680,380,dark=True,name="llm"); s.title("LLM provider abstraction (llm_provider.py)")
    s.box(20,160,130,70,"Persona Reasoner","complete()",C['violet']); s.box(210,150,130,90,"Provider selector","LLM_PROVIDER",C['cyan'])
    for i,(t,sub,c) in enumerate([("demo","deterministic offline composer",C['green']),("ollama","local Llama model",C['blue']),("openai_compatible","hosted or local endpoint",C['amber']),("auto","probe Ollama, else fallback",C['teal'])]):
        s.box(420,60+i*75,240,58,t,sub,c,ssize=9); s.arrow([(340,195),(420,89+i*75)],dashed=(i==3))
    s.arrow([(150,195),(210,195)],label="prompt")
    s.text(20,345,"The frontend only sees a ChatResponse; the provider that actually produced the text is named in it.",10,fill="#9FB0D8")
    s.text(20,362,"If a provider fails, complete() returns a safe offline answer instead of crashing.",10,fill="#9FB0D8")
    h+=fig(s,"Same application, interchangeable providers",tag="a")
    h+=H2("What is sent to the model")
    h+=UL(["System instructions: not claim literal identity or consciousness; no invented quotations, dates or events; say when evidence is insufficient.","Persona profile, retrieved evidence, recent conversation history.","Language instruction: English, Hindi or Hinglish.","Response-mode guardrails (evidence / persona simulation / historical / current context)."])
    h+=CALL("info","Llama/Ollama is <b>not required</b>. With <code>LLM_PROVIDER=demo</code> the offline composer answers from retrieved evidence; with <code>auto</code> the system uses Ollama if reachable, else returns a <code>demo(no-llm)</code> answer. The offline composer selects sentences that match the actual question rather than returning the first chunk.")+END(); return h
