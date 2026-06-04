from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, usuarios, talhoes

app = FastAPI(title="AgroGestor API - Sistema de Compliance")

# Configuração de CORS para permitir comunicação com o Frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Acoplamento dos submódulos de rotas
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticação"])
app.include_router(usuarios.router, prefix="/api/v1/usuarios", tags=["Usuários & Funcionários"])
app.include_router(talhoes.router, prefix="/api/v1/talhoes", tags=["Talhões"])

@app.get("/")
def read_root():
    return {"status": "AgroGestor API rodando perfeitamente."}