from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt 

SECRET_KEY = "SUA_CHAVE_SECRETA_SUPER_SECRETA" # Deve ser a mesma usada no login.py
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais de acesso.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decodifica o token enviado pelo frontend
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub") # ID do usuário
        perfil: str = payload.get("perfil") # 'Gestor' ou 'Técnico Agrícola'
        
        if user_id is None or perfil is None:
            raise credentials_exception
            
        return {"id": user_id, "perfil": perfil}
        
    except Exception:
        raise credentials_exception