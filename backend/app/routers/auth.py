from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
import sqlite3
import jwt  
from datetime import datetime, timedelta

router = APIRouter()
DB_NAME = "agrogestor.db"

# CHAVE E ALGORITMO SINCRONIZADOS COM O SECURITY.PY
SECRET_KEY = "SUA_CHAVE_SECRETA_SUPER_SECRETA"
ALGORITHM = "HS256"

class LoginRequest(BaseModel):
    email: EmailStr  
    password: str

@router.post("/login")
def login(dados: LoginRequest):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Busca os dados do usuário
    cursor.execute("SELECT id, nome, email, senha_hash, perfil FROM usuarios WHERE email = ?;", (dados.email,))
    usuario = cursor.fetchone()
    
    if not usuario:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou e-mail não cadastrado."
        )
        
    user_id, nome, email, senha_hash, perfil = usuario
    
    if dados.password != senha_hash:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Senha incorreta."
        )
    
    # Busca os vínculos de fazenda deste usuário
    cursor.execute("""
        SELECT ef.id_fazenda, f.nome, ef.papel 
        FROM equipe_fazendas ef
        JOIN fazendas f ON ef.id_fazenda = f.id
        WHERE ef.id_usuario = ?;
    """, (user_id,))
    
    vinculos = cursor.fetchall()
    conn.close()
    
    fazendas_associadas = [
        {"id_fazenda": row[0], "nome_fazenda": row[1], "papel_na_fazenda": row[2]} 
        for row in vinculos
    ]
    
    # --- GERAÇÃO DO TOKEN REAL JWT ---
    # Coloca no payload as mesmas propriedades que o security.py tenta ler ('sub' e 'perfil')
    tempo_expiracao = datetime.utcnow() + timedelta(hours=8)
    payload_token = {
        "sub": str(user_id),
        "perfil": perfil,
        "exp": tempo_expiracao
    }
    
    token_real = jwt.encode(payload_token, SECRET_KEY, algorithm=ALGORITHM)
    
    return {
        "access_token": token_real,
        "token_type": "bearer",
        "nome": nome,
        "perfil_global": perfil,
        "fazendas": fazendas_associadas 
    }