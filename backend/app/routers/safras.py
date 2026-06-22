from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlite3 import Connection
from typing import Optional
from app.database import get_db
from app.utils.security import get_current_user

router = APIRouter()

# Verifica que o usuário pertence à fazenda do talhão
def _verificar_acesso_talhao(id_talhao: int, user_id: int, db: Connection):
    cursor = db.cursor()
    cursor.execute("SELECT id_fazenda FROM talhoes WHERE id = ? AND ativo = 1", (id_talhao,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Talhão não encontrado ou inativo.")
    cursor.execute(
        "SELECT 1 FROM equipe_fazendas WHERE id_fazenda = ? AND id_usuario = ?",
        (row[0], user_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Acesso negado. Você não pertence à fazenda deste talhão.")

# RFS07 - CONSULTAR SAFRAS
@router.get("/")
def listar_safras(
    id_talhao: Optional[int] = Query(None),
    variedade: Optional[str] = Query(None),
    status_safra: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    query = """
        SELECT s.id, s.id_talhao, t.nome AS nome_talhao,
               s.variedade_cultura, s.data_inicio_prevista, s.data_colheita_prevista,
               s.status, s.produtividade_safra
        FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
        WHERE ef.id_usuario = ? AND s.ativo = 1 AND t.ativo = 1
    """
    params = [current_user["id"]]

    if id_talhao is not None:
        query += " AND s.id_talhao = ?"; params.append(id_talhao)
    if variedade:
        query += " AND s.variedade_cultura LIKE ?"; params.append(f"%{variedade}%")
    if status_safra:
        if status_safra not in ("Planejada", "Em andamento", "Colhida/Finalizada"):
            raise HTTPException(status_code=400, detail="Valor de status inválido.")
        query += " AND s.status = ?"; params.append(status_safra)

    query += " ORDER BY s.data_inicio_prevista DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()

    return [
        {
            "id": r[0], "id_talhao": r[1], "nome_talhao": r[2],
            "variedade_cultura": r[3], "data_inicio_prevista": r[4],
            "data_colheita_prevista": r[5], "status": r[6],
            "produtividade_safra": r[7],
        }
        for r in rows
    ]

# RFS05 - INSERIR SAFRA
@router.post("/", status_code=status.HTTP_201_CREATED)
def inserir_safra(
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    id_talhao     = payload.get("id_talhao")
    variedade     = (payload.get("variedade_cultura") or "").strip()
    data_inicio   = (payload.get("data_inicio_prevista") or "").strip()
    data_colheita = (payload.get("data_colheita_prevista") or "").strip()
    st            = payload.get("status", "Planejada")

    if not all([id_talhao, variedade, data_inicio, data_colheita]):
        raise HTTPException(status_code=400, detail="Campos obrigatórios ausentes.")
    if st not in ("Planejada", "Em andamento", "Colhida/Finalizada"):
        raise HTTPException(status_code=400, detail="Status inválido.")
    # RN03
    if data_colheita <= data_inicio:
        raise HTTPException(status_code=400, detail="A data de colheita prevista deve ser posterior à data de início.")
    # RN05
    if payload.get("produtividade_safra") is not None and st != "Colhida/Finalizada":
        raise HTTPException(status_code=400, detail="A produtividade só pode ser informada ao encerrar a safra.")

    _verificar_acesso_talhao(id_talhao, current_user["id"], db)
    cursor = db.cursor()

    # RN01
    if st == "Em andamento":
        cursor.execute(
            "SELECT id FROM safras WHERE id_talhao = ? AND status = 'Em andamento' AND ativo = 1",
            (id_talhao,)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Este talhão já possui uma safra 'Em andamento'.")

    cursor.execute(
        "INSERT INTO safras (id_talhao, variedade_cultura, data_inicio_prevista, data_colheita_prevista, status) VALUES (?, ?, ?, ?, ?)",
        (id_talhao, variedade, data_inicio, data_colheita, st)
    )
    nova_id = cursor.lastrowid
    db.commit()
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "INSERIR_SAFRA", f"Safra ID {nova_id} ({variedade}) criada para talhão ID {id_talhao}.")
    )
    db.commit()
    return {"message": "Safra cadastrada com sucesso.", "id": nova_id}

# RFS06 - EDITAR SAFRA
@router.put("/{id}")
def editar_safra(
    id: int,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute(
        """SELECT s.id_talhao, s.variedade_cultura, s.data_inicio_prevista,
                  s.data_colheita_prevista, s.status, s.produtividade_safra
           FROM safras s
           JOIN talhoes t ON s.id_talhao = t.id
           JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
           WHERE s.id = ? AND s.ativo = 1 AND ef.id_usuario = ?""",
        (id, current_user["id"])
    )
    safra = cursor.fetchone()
    if not safra:
        raise HTTPException(status_code=404, detail="Safra não encontrada ou sem permissão.")

    id_talhao_a, var_a, ini_a, col_a, st_a, prod_a = safra

    novo_talhao   = payload.get("id_talhao",             id_talhao_a)
    nova_var      = (payload.get("variedade_cultura",     var_a) or "").strip()
    novo_inicio   = (payload.get("data_inicio_prevista",  ini_a) or "").strip()
    nova_colheita = (payload.get("data_colheita_prevista",col_a) or "").strip()
    novo_st       = payload.get("status",                st_a)
    nova_prod     = payload.get("produtividade_safra",   prod_a)

    if novo_st not in ("Planejada", "Em andamento", "Colhida/Finalizada"):
        raise HTTPException(status_code=400, detail="Status inválido.")

    # Campos bloqueados após início do cultivo (RN06)
    if st_a in ("Em andamento", "Colhida/Finalizada"):
        if novo_talhao != id_talhao_a:
            raise HTTPException(status_code=400, detail="Talhão não pode ser alterado após início do cultivo.")
        if nova_var != var_a:
            raise HTTPException(status_code=400, detail="Variedade não pode ser alterada após início do cultivo.")
        if novo_inicio != ini_a:
            raise HTTPException(status_code=400, detail="Data de início não pode ser alterada após início do cultivo.")

    # RN03
    if nova_colheita <= novo_inicio:
        raise HTTPException(status_code=400, detail="Data de colheita deve ser posterior à data de início.")
    # RN07
    if nova_prod is not None and novo_st != "Colhida/Finalizada":
        raise HTTPException(status_code=400, detail="Produtividade só pode ser registrada ao encerrar (Colhida/Finalizada).")
    # RN01
    if novo_st == "Em andamento" and st_a != "Em andamento":
        cursor.execute(
            "SELECT id FROM safras WHERE id_talhao = ? AND status = 'Em andamento' AND ativo = 1 AND id != ?",
            (novo_talhao, id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe uma safra 'Em andamento' para este talhão.")

    cursor.execute(
        """UPDATE safras SET id_talhao=?, variedade_cultura=?, data_inicio_prevista=?,
           data_colheita_prevista=?, status=?, produtividade_safra=? WHERE id=?""",
        (novo_talhao, nova_var, novo_inicio, nova_colheita, novo_st, nova_prod, id)
    )
    db.commit()
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "EDITAR_SAFRA", f"Safra ID {id} atualizada. Novo status: {novo_st}.")
    )
    db.commit()
    return {"message": "Safra atualizada com sucesso."}

# ENCERRAR SAFRA
# Ação de encerramento com registro de produtividade (RN05 / RN07)
@router.patch("/{id}/encerrar")
def encerrar_safra(
    id: int,
    payload: dict,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    produtividade      = payload.get("produtividade_safra")
    data_colheita_real = payload.get("data_colheita_prevista")

    if produtividade is None:
        raise HTTPException(status_code=400, detail="produtividade_safra é obrigatória.")
    if not isinstance(produtividade, (int, float)) or produtividade <= 0:
        raise HTTPException(status_code=400, detail="produtividade_safra deve ser um número positivo.")

    cursor = db.cursor()
    cursor.execute(
        """SELECT s.status, s.data_inicio_prevista
           FROM safras s
           JOIN talhoes t ON s.id_talhao = t.id
           JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
           WHERE s.id = ? AND s.ativo = 1 AND ef.id_usuario = ?""",
        (id, current_user["id"])
    )
    safra = cursor.fetchone()
    if not safra:
        raise HTTPException(status_code=404, detail="Safra não encontrada.")
    if safra[0] == "Colhida/Finalizada":
        raise HTTPException(status_code=400, detail="Esta safra já foi encerrada.")
    if data_colheita_real and data_colheita_real < safra[1]:
        raise HTTPException(status_code=400, detail="Data de colheita real não pode ser anterior ao plantio.")

    campos = "status = 'Colhida/Finalizada', produtividade_safra = ?"
    params = [produtividade]
    if data_colheita_real:
        campos += ", data_colheita_prevista = ?"; params.append(data_colheita_real)
    params.append(id)

    cursor.execute(f"UPDATE safras SET {campos} WHERE id = ?", params)
    db.commit()
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "ENCERRAR_SAFRA", f"Safra ID {id} encerrada. Produtividade: {produtividade} sc/ha.")
    )
    db.commit()
    return {"message": "Safra encerrada com sucesso. Produtividade registrada."}

# RFS08 - EXCLUIR SAFRA (soft delete)
@router.delete("/{id}")
def excluir_safra(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute(
        """SELECT s.variedade_cultura FROM safras s
           JOIN talhoes t ON s.id_talhao = t.id
           JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
           WHERE s.id = ? AND s.ativo = 1 AND ef.id_usuario = ?""",
        (id, current_user["id"])
    )
    safra = cursor.fetchone()
    if not safra:
        raise HTTPException(status_code=404, detail="Safra não encontrada ou sem permissão.")

    cursor.execute("SELECT id FROM atividades WHERE id_safra = ? LIMIT 1", (id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Não é possível excluir. Esta safra já possui atividades registradas.")

    cursor.execute("UPDATE safras SET ativo = 0 WHERE id = ?", (id,))
    cursor.execute(
        "INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)",
        (current_user["id"], "EXCLUIR_SAFRA", f"Exclusão lógica da safra ID {id} ({safra[0]}).")
    )
    db.commit()
    return {"message": "Safra removida com sucesso."}

# DASHBOARD
@router.get("/{safra_id}/indicadores")
def obter_indicadores_dashboard(
    safra_id: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute(
        """SELECT s.id FROM safras s
           JOIN talhoes t ON s.id_talhao = t.id
           JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
           WHERE s.id = ? AND ef.id_usuario = ?""",
        (safra_id, current_user["id"])
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Safra não encontrada ou sem acesso.")

    cursor.execute("SELECT status FROM atividades WHERE id_safra = ?", (safra_id,))
    atividades = cursor.fetchall()
    totais = len(atividades)
    executadas = sum(1 for a in atividades if a[0] == "Realizado")
    porcentagem = int((executadas / totais) * 100) if totais > 0 else 0

    cursor.execute(
        """SELECT a.data_execucao, a.tipo_atividade, u.nome FROM atividades a
           JOIN usuarios u ON a.id_responsavel = u.id
           WHERE a.id_safra = ? AND a.status = 'Agendado'
           ORDER BY a.data_execucao ASC LIMIT 5""",
        (safra_id,)
    )
    proximas = [{"data": r[0], "nome": r[1], "responsavel": r[2]} for r in cursor.fetchall()]

    cursor.execute(
        """SELECT tipo_evento, data_ocorrência, descricao_danos FROM eventos_extremos
           WHERE id_safra = ? ORDER BY data_ocorrência DESC""",
        (safra_id,)
    )
    alertas = [
        {"tipo": "critico", "titulo": f"OCORRÊNCIA: {r[0]}", "desc": f"Registrado em {r[1]}: {r[2]}"}
        for r in cursor.fetchall()
    ]

    return {"porcentagem": porcentagem, "executadas": executadas, "totais": totais,
            "proximasAtividades": proximas, "alertas": alertas}
