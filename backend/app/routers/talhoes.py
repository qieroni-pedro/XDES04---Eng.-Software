from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlite3 import Connection
from typing import Optional
from app.database import get_db
from app.utils.security import get_current_user

router = APIRouter()

# Função auxiliar para capturar a fazenda associada ao usuário atual
def obter_fazenda_usuario(user_id: int, db: Connection) -> int:
    cursor = db.cursor()
    cursor.execute("SELECT id_fazenda FROM equipe_fazendas WHERE id_usuario = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Operador não associado a nenhuma fazenda ativa no sistema."
        )
    return row[0]

# --- RFS03: CONSULTAR TALHÕES ---
@router.get("/")
def listar_talhoes(
    nome: Optional[str] = Query(None),
    area_min: Optional[float] = Query(None),
    area_max: Optional[float] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    id_fazenda = obter_fazenda_usuario(current_user["id"], db)
    cursor = db.cursor()
    
    # Query trazendo registros não deletados (ativo = 1) pertencentes à fazenda do usuário
    query = "SELECT id, nome, area_ha, tipo_solo FROM talhoes WHERE id_fazenda = ? AND ativo = 1"
    params = [id_fazenda]
    
    # Filtro parcial por nome do talhão
    if nome:
        query += " AND nome LIKE ?"
        params.append(f"%{nome}%")
    # Filtros por intervalo de área (de / até)
    if area_min is not None:
        query += " AND area_ha >= ?"
        params.append(area_min)
    if area_max is not None:
        query += " AND area_ha <= ?"
        params.append(area_max)
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    return [{"id": r[0], "nome": r[1], "area_ha": r[2], "tipo_solo": r[3]} for r in rows]

# --- RFS01: INSERIR TALHÃO (Apenas Gestor) ---
@router.post("/", status_code=status.HTTP_201_CREATED)
def inserir_talhao(
    payload: dict, 
    current_user: dict = Depends(get_current_user), 
    db: Connection = Depends(get_db)
):
    # Regra de negócio: Apenas perfil Gestor pode realizar cadastro
    if current_user["perfil"] != "Gestor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permissão negada. Apenas Gestores podem inserir novos talhões."
        )
        
    id_fazenda = obter_fazenda_usuario(current_user["id"], db)
    nome = payload.get("nome")
    area_ha = payload.get("area_ha")
    tipo_solo = payload.get("tipo_solo")
    
    if not nome or area_ha is None or tipo_solo not in ['Argiloso', 'Arenoso', 'Misto']:
        raise HTTPException(status_code=400, detail="Dados obrigatórios ausentes ou incorretos.")
        
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO talhoes (id_fazenda, nome, area_ha, tipo_solo) VALUES (?, ?, ?, ?)",
        (id_fazenda, nome, area_ha, tipo_solo)
    )
    db.commit()
    
    # Log de Auditoria do Sistema
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "INSERIR_TALHAO", f"Talhão '{nome}' adicionado à fazenda ID {id_fazenda}.")
    )
    db.commit()
    return {"message": "Talhão cadastrado com sucesso."}

# --- RFS02: EDITAR TALHÃO (Técnico e Gestor) ---
@router.put("/{id}")
def editar_talhao(
    id: int, 
    payload: dict, 
    current_user: dict = Depends(get_current_user), 
    db: Connection = Depends(get_db)
):
    id_fazenda = obter_fazenda_usuario(current_user["id"], db)
    cursor = db.cursor()
    
    # Verifica se o registro pertence à fazenda dele e está ativo
    cursor.execute("SELECT nome FROM talhoes WHERE id = ? AND id_fazenda = ? AND ativo = 1", (id, id_fazenda))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Talhão não localizado na fazenda atual.")
        
    nome = payload.get("nome")
    area_ha = payload.get("area_ha")
    tipo_solo = payload.get("tipo_solo")
    
    cursor.execute(
        "UPDATE talhoes SET nome = ?, area_ha = ?, tipo_solo = ? WHERE id = ? AND id_fazenda = ?",
        (nome, area_ha, tipo_solo, id, id_fazenda)
    )
    db.commit()
    
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "EDITAR_TALHAO", f"Talhão ID {id} modificado.")
    )
    db.commit()
    return {"message": "Dados do talhão atualizados com sucesso."}

# --- RFS04: EXCLUIR TALHÃO (Soft Delete + Trava de Segurança de Safras) ---
@router.delete("/{id}")
def excluir_talhao(
    id: int, 
    current_user: dict = Depends(get_current_user), 
    db: Connection = Depends(get_db)
):
    # Regra de negócio: Operação restrita ao Gestor
    if current_user["perfil"] != "Gestor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permissão negada. Apenas Gestores podem remover talhões."
        )
        
    id_fazenda = obter_fazenda_usuario(current_user["id"], db)
    cursor = db.cursor()
    
    cursor.execute("SELECT nome FROM talhoes WHERE id = ? AND id_fazenda = ? AND ativo = 1", (id, id_fazenda))
    talhao = cursor.fetchone()
    if not talhao:
        raise HTTPException(status_code=404, detail="Talhão não localizado.")
        
    # EXIGÊNCIA RFS04: Não permitir se possuir safras associadas (ativas ou encerradas)
    cursor.execute("SELECT id FROM safras WHERE id_talhao = ? LIMIT 1", (id,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Não é possível remover. Este talhão possui históricos de safras vinculados a ele."
        )
        
    # Executa a exclusão lógica (soft delete)
    cursor.execute("UPDATE talhoes SET ativo = 0 WHERE id = ?", (id,))
    
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "EXCLUIR_TALHAO", f"Exclusão lógica aplicada ao talhão {talhao[0]} (ID: {id}).")
    )
    db.commit()
    return {"message": "Talhão removido com sucesso."}