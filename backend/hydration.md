PHASE 1: HYDRATION (Write Data)
-------------------------------
[providers.csv]  (Raw Data Source)
       │
       ▼
[ingest.py]  (The Worker Script)
       │
       ├── ← uses [fraud_engine.py] (Calculates Risk %)
       │
       ▼
[models.py]  (Defines Table Structure)
       │
       ▼
[database.py] (Opens Connection)
       │
       ▼
 [[ fraud.db ]]  (The SQLite File)


PHASE 2: SERVING (Read Data)
----------------------------
 [[ fraud.db ]]  (The SQLite File)
       │
       ▼
[database.py] (Opens Connection)
       │
       ▼
[models.py]  (Reads Rows)
       │
       ▼
[main.py]  (FastAPI Server)
       │
       ├── ← uses [schemas.py] (Converts to clean JSON)
       │
       ▼
(Frontend Request) (The User)