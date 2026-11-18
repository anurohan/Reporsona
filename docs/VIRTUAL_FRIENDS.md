# Virtual Friends

Virtual Friends are private, evidence-grounded simulations built from user-provided conversation history. They are not recreations of a person's mind and must not be presented as the person's actual opinions. The staged importer accepts WhatsApp TXT/ZIP, Instagram JSON/HTML, Telegram JSON/HTML, and Facebook Messenger JSON/HTML exports.

## Flow

1. An export is uploaded to `/imports/preview` and held as a staged normalized record.
2. The platform parser extracts sender, timestamp, text/attachment markers, conversation ID, participants, and source metadata.
3. The UI shows a participant preview. Confirmation requires an explicit target speaker and either a new friend name or an existing friend ID.
4. System messages and duplicates are removed. Platform imports use conversation-aware chunks that preserve message order.
5. Sources and chunks are stored under the linked persona. The existing embedding service and vector registry provide retrieval; the existing LLM provider supplies generation.
6. Lightweight analysis creates `DOCUMENTED`, `OBSERVED`, and clearly qualified inferred profile entries with chunk references.
7. Chat retrieves only that friend's persona chunks, reranks them, requires a lexical evidence anchor, and abstains with the exact insufficient-evidence message when coverage is not defensible.

## API

All endpoints are under `/api/virtual-friends`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/` | Create a friend |
| GET | `/` or `/{friend_id}` | List or inspect friends |
| DELETE | `/{friend_id}` | Delete the friend, linked persona, transcripts, memories, chunks, and index |
| POST | `/{friend_id}/transcripts/upload` | Upload `.txt`, `.json`, or `.csv` |
| POST | `/{friend_id}/transcripts/text` | Add pasted transcript text |
| GET/DELETE | `/{friend_id}/transcripts` and `/{transcript_id}` | Manage imports |
| POST | `/{friend_id}/transcripts/{transcript_id}/reprocess` | Rebuild derived data from the private upload |
| POST | `/chat` | Generate a grounded virtual-friend response |
| GET/DELETE | `/{friend_id}/memories` and `/{memory_id}` | Inspect or remove extracted memories |
| GET/DELETE | `/{friend_id}/conversations` and `/{session_id}` | Manage chat sessions |

## Configuration and limitations

The feature uses the existing `DATABASE_URL`, `VECTOR_DB`, embedding, and LLM settings. No new secret is required. Neural embeddings are preferred when installed; the existing hashing fallback remains available. Authentication is still inherited from the host application's current deployment configuration; the local app currently exposes these routes without a user-auth middleware, so production deployments should place the API behind the project's authentication boundary before handling private transcripts.

Raw upload text is retained only to support explicit reprocessing and is deleted with its transcript/friend. Source ownership is stored by source ID, so deleting one import cannot remove another import with the same filename.
