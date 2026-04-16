# 📍 CAP Italia API

Dato un CAP italiano restituisce comune, provincia, regione, coordinate GPS e timezone.

**Live su RapidAPI:** *(link dopo il deploy)*

---

## Endpoints

| Metodo | Path | Descrizione |
|--------|------|-------------|
| GET | `/status` | Health check |
| GET | `/cap/{cap}` | Lookup singolo CAP |
| POST | `/cap/bulk` | Lookup fino a 50 CAP |
| GET | `/search?q=...` | Cerca per nome comune |

### Esempio — `GET /cap/20121`

```json
{
  "cap": "20121",
  "comune": "Milano",
  "provincia": "Milano",
  "provincia_sigla": "MI",
  "regione": "Lombardia",
  "lat": 45.4643,
  "lon": 9.1895,
  "timezone": "Europe/Rome"
}
```

### Esempio — `POST /cap/bulk`

```json
// Request
{ "caps": ["20121", "00196", "80100"] }

// Response
{
  "results": [...],
  "found": 3,
  "not_found": 0,
  "total": 3
}
```

### Esempio — `GET /search?q=milano&limit=5`

Restituisce tutti i CAP il cui comune contiene "milano".

---

## Database

- **4.735 CAP** unici
- **20 regioni**, **107 province**
- Fonte: GeoNames + ISTAT (open data)
- Caricato in memoria all'avvio per latenza minima

---

## Run in locale

```bash
# Installa dipendenze
pip install -r requirements.txt

# Avvia
uvicorn main:app --reload

# Documentazione interattiva
http://localhost:8000/docs
```

---

## Deploy (Railway)

1. Fork o push su GitHub
2. Vai su [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Railway legge il `Dockerfile` automaticamente
4. Copia l'URL pubblico generato

---

## Stack

- **Python 3.12**
- **FastAPI** — genera OpenAPI automaticamente
- **Uvicorn** — server ASGI
- **Deploy**: Railway
- **Marketplace**: RapidAPI

---

## Licenza

MIT
