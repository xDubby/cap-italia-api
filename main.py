"""
CAP Italia API
--------------
Dato un CAP italiano, restituisce comune, provincia, regione,
coordinate GPS e timezone.

Autore: tu
Stack: Python + FastAPI
Deploy: Railway / Render
"""

import json
import os
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


# ── Costanti ──────────────────────────────────────────────
API_VERSION = "1.0.0"
DATA_PATH   = Path(__file__).parent / "data" / "cap_db.json"


# ── Modelli di risposta (documentano automaticamente l'API) ──
class CapResponse(BaseModel):
    cap:             str
    comune:          str
    provincia:       str
    provincia_sigla: str
    regione:         str
    lat:             Optional[float]
    lon:             Optional[float]
    timezone:        str

    class Config:
        json_schema_extra = {
            "example": {
                "cap":             "20121",
                "comune":          "Milano",
                "provincia":       "Milano",
                "provincia_sigla": "MI",
                "regione":         "Lombardia",
                "lat":             45.4654,
                "lon":             9.1859,
                "timezone":        "Europe/Rome"
            }
        }

class BulkRequest(BaseModel):
    caps: List[str]

    class Config:
        json_schema_extra = {"example": {"caps": ["20121", "00100", "80100"]}}

class BulkItem(BaseModel):
    cap:   str
    found: bool
    data:  Optional[CapResponse] = None

class BulkResponse(BaseModel):
    results:    List[BulkItem]
    found:      int
    not_found:  int
    total:      int

class ErrorResponse(BaseModel):
    error:   str
    message: str

class StatusResponse(BaseModel):
    status:   str
    version:  str
    total_cap: int


# ── App ───────────────────────────────────────────────────
app = FastAPI(
    title        = "CAP Italia API",
    description  = """
## 📍 CAP Italia API

Dato un CAP (Codice di Avviamento Postale) italiano, questa API restituisce:

- **Comune** di riferimento
- **Provincia** (nome completo e sigla)
- **Regione**
- **Coordinate GPS** (latitudine e longitudine)
- **Timezone** (sempre `Europe/Rome`)

### Casi d'uso
- Autocompletamento form di registrazione / checkout
- Validazione indirizzi di spedizione
- Logistica e zone di consegna
- App e-commerce italiane

### Autenticazione
Tutti gli endpoint richiedono un header `X-RapidAPI-Key` (gestito da RapidAPI).

### Rate limiting
Dipende dal piano sottoscritto. Vedi i piani su RapidAPI.
    """,
    version      = API_VERSION,
    contact      = {"name": "Support", "email": "support@example.com"},
    license_info = {"name": "MIT"},
)

# CORS — permette chiamate da browser (utile per demo/playground)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Carica il database in memoria all'avvio ───────────────
# In produzione potresti usare Redis o SQLite per dataset più grandi
_db: dict = {}

@app.on_event("startup")
def load_database():
    global _db
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        _db = json.load(f)
    print(f"[startup] Caricati {len(_db)} CAP in memoria")


# ── Endpoints ─────────────────────────────────────────────

@app.get(
    "/status",
    response_model=StatusResponse,
    summary="Health check",
    tags=["Utility"],
)
def get_status():
    """Controlla che l'API sia online e restituisce la versione."""
    return {"status": "ok", "version": API_VERSION, "total_cap": len(_db)}


@app.get(
    "/cap/{cap}",
    response_model=CapResponse,
    responses={
        404: {"model": ErrorResponse, "description": "CAP non trovato"},
        422: {"description": "Formato CAP non valido"},
    },
    summary="Lookup singolo CAP",
    tags=["CAP"],
)
def get_cap(
    cap: str,
    # RapidAPI invia questo header automaticamente — non serve gestirlo,
    # ma documentarlo aiuta gli utenti
    x_rapidapi_key: Optional[str] = Header(None, include_in_schema=False),
):
    """
    Restituisce i dati geografici di un singolo CAP italiano.

    - **cap**: 5 cifre, es. `20121` per Milano centro
    """
    # Normalizza: rimuovi spazi, padding a 5 cifre
    cap = cap.strip().zfill(5)

    if len(cap) != 5 or not cap.isdigit():
        raise HTTPException(
            status_code=422,
            detail={"error": "INVALID_FORMAT", "message": "Il CAP deve essere composto da 5 cifre numeriche"}
        )

    result = _db.get(cap)
    if not result:
        raise HTTPException(
            status_code=404,
            detail={"error": "CAP_NOT_FOUND", "message": f"CAP '{cap}' non trovato nel database"}
        )

    return result


@app.post(
    "/cap/bulk",
    response_model=BulkResponse,
    summary="Lookup multiplo (bulk)",
    tags=["CAP"],
)
def get_cap_bulk(body: BulkRequest):
    """
    Riceve una lista di CAP e restituisce i dati per ciascuno.

    - Massimo **50 CAP** per richiesta
    - I CAP non trovati sono inclusi nella risposta con `found: false`
    - Utile per validare liste di indirizzi o import massivi
    """
    if len(body.caps) > 50:
        raise HTTPException(
            status_code=400,
            detail={"error": "TOO_MANY_CAPS", "message": "Massimo 50 CAP per richiesta bulk"}
        )

    results = []
    for raw_cap in body.caps:
        cap = raw_cap.strip().zfill(5)
        data = _db.get(cap)
        results.append(BulkItem(
            cap=cap,
            found=data is not None,
            data=CapResponse(**data) if data else None,
        ))

    found     = sum(1 for r in results if r.found)
    not_found = len(results) - found

    return BulkResponse(results=results, found=found, not_found=not_found, total=len(results))


@app.get(
    "/search",
    response_model=List[CapResponse],
    summary="Cerca per nome comune",
    tags=["CAP"],
)
def search_by_comune(
    q: str = Query(..., min_length=2, description="Nome del comune (parziale)"),
    limit: int = Query(10, ge=1, le=50, description="Numero massimo di risultati"),
):
    """
    Cerca CAP per nome del comune (ricerca parziale, case-insensitive).

    Esempio: `?q=mil` trova tutti i CAP di Milano e comuni simili.
    """
    q_lower = q.lower()
    matches = [
        v for v in _db.values()
        if q_lower in v["comune"].lower()
    ][:limit]

    if not matches:
        return []

    return matches
