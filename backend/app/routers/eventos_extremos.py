import os
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlite3 import Connection
from app.database import get_db
from app.utils.security import get_current_user

router = APIRouter()

def _validar_permissao_e_status_safra(id_safra: int, user_id: int, db: Connection):
    """
    Garante que o usuário pertence à equipe da fazenda e valida se a 
    safra está estritamente 'Em andamento'.
    """
    cursor = db.cursor()
    cursor.execute("""
        SELECT t.id_fazenda, s.status 
        FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        WHERE s.id = ? AND s.ativo = 1 AND t.ativo = 1
    """, (id_safra,))
    res = cursor.fetchone()
    
    if not res:
        raise HTTPException(status_code=404, detail="Safra selecionada não existe ou foi removida.")
    
    id_fazenda, status_safra = res[0], res[1]
    
    # Validação de vínculo de Equipe (RBAC)
    cursor.execute(
        "SELECT 1 FROM equipe_fazendas WHERE id_fazenda = ? AND id_usuario = ?",
        (id_fazenda, user_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Acesso negado. Você não possui vínculo com esta fazenda.")
        
    # Regra de negócio restritiva: Apenas safras em andamento recebem sinistros
    if status_safra != "Em andamento":
        raise HTTPException(
            status_code=400, 
            detail=f"Não é permitido registrar eventos para safras com status '{status_safra}'. Apenas safras 'Em andamento' são permitidas."
        )
        
    return status_safra

# --- ROTA GET (Consultar Histórico) ---
@router.get("")
def listar_eventos_extremos(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    # Retorna os eventos das fazendas onde o usuário logado trabalha
    cursor.execute("""
        SELECT ev.*, s.variedade_cultura as nome_safra
        FROM eventos_extremos ev
        JOIN safras s ON ev.id_safra = s.id
        JOIN talhoes t ON s.id_talhao = t.id
        JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
        WHERE ef.id_usuario = ?
        ORDER BY ev.data_ocorrência DESC
    """, (current_user["id"],))
    
    colunas = [col[0] for col in cursor.description]
    return [dict(zip(colunas, row)) for row in cursor.fetchall()]

# --- ROTA GET POR ID (Detalhe de um Evento) ---
@router.get("/{id_evento}")
def detalhar_evento_extremo(
    id_evento: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    # Busca o evento completo junto com dados da safra e talhão,
    # garantindo que o usuário tem vínculo com a fazenda (RBAC)
    cursor.execute("""
        SELECT
            ev.id,
            ev.id_safra,
            ev.tipo_evento,
            ev.data_ocorrência,
            ev.descricao_danos,
            s.variedade_cultura  AS nome_safra,
            t.nome               AS nome_talhao
        FROM eventos_extremos ev
        JOIN safras s           ON ev.id_safra = s.id
        JOIN talhoes t          ON s.id_talhao = t.id
        JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
        WHERE ev.id = ?
          AND ef.id_usuario = ?
    """, (id_evento, current_user["id"]))
    
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Evento não encontrado ou você não possui acesso a este registro."
        )
    
    colunas = [col[0] for col in cursor.description]
    return dict(zip(colunas, row))

# --- ROTA POST (Inserir Ocorrência) ---
@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_evento_extremo(
    id_safra: int = Form(...),
    tipo_evento: str = Form(...),
    data_ocorrencia: str = Form(..., alias="data_ocorrência"),
    descricao_danos: str = Form(..., alias="descricao_danos"),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    # Validação do ENUM do banco de dados
    opcoes_validas = ('Granizo', 'Seca/Estiagem', 'Geada', 'Vendaval/Tempestade', 'Quebra Crítica de Maquinário', 'Outro')
    if tipo_evento not in opcoes_validas:
        raise HTTPException(status_code=400, detail="Tipo de evento informado é inválido.")
        
    if not descricao_danos or not descricao_danos.strip():
        raise HTTPException(status_code=400, detail="A descrição detalhada dos danos é obrigatória.")

    # Executa validação de segurança e ciclo de vida da safra
    _validar_permissao_e_status_safra(id_safra, current_user["id"], db)

    cursor = db.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        
        # Inserção do Sinistro
        cursor.execute("""
            INSERT INTO eventos_extremos (id_safra, tipo_evento, data_ocorrência, descricao_danos)
            VALUES (?, ?, ?, ?)
        """, (id_safra, tipo_evento, data_ocorrencia, descricao_danos))
        
        id_novo_evento = cursor.lastrowid

        # Registro na Tabela de Auditoria (Compliance)
        detalhes_log = f"Evento do tipo '{tipo_evento}' registrado na Safra ID {id_safra}. Descrição: {descricao_danos[:60]}..."
        cursor.execute("""
            INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)
        """, (current_user["id"], "INSERIR_EVENTO_EXTREMO", detalhes_log))

        db.commit()
        return {"message": "Evento extremo protocolado com sucesso.", "id": id_novo_evento}
        
    except Exception as e:
        db.rollback()
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))