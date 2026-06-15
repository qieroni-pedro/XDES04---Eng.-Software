from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
import sqlite3
from app.utils.security import get_current_user

router = APIRouter(tags=["Usuários / Equipe"])
DB_NAME = "agrogestor.db"

class CriarFuncionarioRequest(BaseModel):
    nome: str
    email: EmailStr
    senha_inicial: str
    id_fazenda: int

@router.post("/cadastrar", status_code=status.HTTP_201_CREATED)
def cadastrar_funcionario(dados: CriarFuncionarioRequest, current_user: dict = Depends(get_current_user)):
    # Validação RBAC
    if current_user["perfil"] != "Gestor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operação não permitida para o seu perfil de acesso."
        )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        # 1. Insere na tabela geral de usuários como Técnico Agrícola
        cursor.execute("""
            INSERT INTO usuarios (nome, email, senha_hash, perfil)
            VALUES (?, ?, ?, 'Técnico Agrícola');
        """, (dados.nome, dados.email, dados.senha_inicial))
        
        id_novo_usuario = cursor.lastrowid

        # 2. Insere o vínculo na tabela de agregação (papel = 'Técnico')
        cursor.execute("""
            INSERT INTO equipe_fazendas (id_fazenda, id_usuario, papel)
            VALUES (?, ?, 'Técnico');
        """, (dados.id_fazenda, id_novo_usuario))

        # 3. Registra a operação nos Logs de Auditoria para fins de conformidade
        cursor.execute("""
            INSERT INTO logs_auditoria (id_usuario, acao, detalhes)
            VALUES (?, 'CADASTRO_FUNCIONARIO', ?);
        """, (current_user["id"], f"Cadastrou o técnico {dados.nome} (ID: {id_novo_usuario})"))

        conn.commit()
        return {"detail": "Funcionário registrado e vinculado com sucesso!"}

    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O e-mail informado já está em uso no sistema."
        )
    finally:
        conn.close()

@router.get("/listar")
def listar_equipe(id_fazenda: int, current_user: dict = Depends(get_current_user)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Busca apenas os funcionários que pertencem à fazenda informada
    cursor.execute("""
        SELECT u.id, u.nome, u.email, ef.papel, u.data_criacao
        FROM equipe_fazendas ef
        JOIN usuarios u ON ef.id_usuario = u.id
        WHERE ef.id_fazenda = ?;
    """, (id_fazenda,))

    membros = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "nome": row[1],
            "email": row[2],
            "papel": row[3],
            "data_criacao": row[4]
        } for row in membros
    ]

@router.delete("/desvincular/{id_usuario}")
def desvincular_funcionario(id_usuario: int, id_fazenda: int, current_user: dict = Depends(get_current_user)):
    # Validação RBAC de segurança
    if current_user["perfil"] != "Gestor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas gestores podem remover membros da equipe."
        )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Remove o vínculo do técnico com aquela fazenda específica
        cursor.execute("""
            DELETE FROM equipe_fazendas 
            WHERE id_usuario = ? AND id_fazenda = ?;
        """, (id_usuario, id_fazenda))
        
        # Registra a remoção nos Logs de Auditoria
        cursor.execute("""
            INSERT INTO logs_auditoria (id_usuario, acao, detalhes)
            VALUES (?, 'REMOÇÃO_FUNCIONARIO', ?);
        """, (current_user["id"], f"Removeu o usuário ID {id_usuario} da fazenda ID {id_fazenda}"))
        
        conn.commit()
        return {"detail": "Funcionário desvinculado com sucesso!"}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro no banco de dados: {str(e)}"
        )
    finally:
        conn.close()