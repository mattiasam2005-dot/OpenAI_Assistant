import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Estrazione e controllo immediato della chiave
OPENAI_KEY = os.getenv("OPENAI_KEY")
if not OPENAI_KEY:
    print("ERRORE: La variabile OPENAI_KEY non è presente nel file .env!")
    sys.exit(1)

# Inizializzazione standard senza l'uso di parametri v1 interni
client = OpenAI(
    api_key=OPENAI_KEY,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

# Test preliminare: se questo fallisce, la chiave o l'account hanno problemi di permessi
try:
    print("Verifica della chiave API in corso...")
    client.models.list()
    print("Connessione a OpenAI riuscita!")
except Exception as e:
    print(f"Errore di autenticazione o connessione: {e}")
    sys.exit(1)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Invia al cliente un'email di benvenuto quando fornisce nome e indirizzo email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nome del cliente"},
                    "email": {"type": "string", "description": "Indirizzo email del cliente"},
                },
                "required": ["name", "email"],
            },
        },
    },
    {
        "type": "file_search",
    },
]

def create_new_assistant():
    print("Creazione dell'assistente...")
    assistant = client.beta.assistants.create(
        name="CinePass Italia Customer Assistant",
        instructions="""
Il tuo nome è Dudù.
Sei l'assistente virtuale di CinePass Italia.
Rispondi in italiano in modo chiaro, cordiale e sintetico.
Usa la knowledge base collegata tramite file_search per rispondere alle domande specifiche.
""",
        tools=TOOLS,
        model="gpt-4o",
    )

    print("Creazione del Vector Store...")
    vector_store = client.beta.vector_stores.create(
        name="CinePass Italia Knowledge Base"
    )

    file_paths = ["./kb/cinepass_info.txt", "./kb/more_info.txt"]
    
    # Verifica preventiva dell'esistenza dei file per prevenire sub-errori 404
    for path in file_paths:
        if not os.path.exists(path):
            print(f"ATTENZIONE: Il file {path} non esiste. Crealo prima di procedere.")
            sys.exit(1)

    file_streams = [open(path, "rb") for path in file_paths]

    try:
        client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams,
        )
    finally:
        for file_stream in file_streams:
            file_stream.close()

    # Colleghiamo il vector store all'assistente
    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id]
            }
        },
    )

    return assistant

if __name__ == "__main__":
    assistant = create_new_assistant()
    print("Successo! Assistant ID:", assistant.id)
