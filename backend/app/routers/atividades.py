import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlite3 import Connection
from typing import Optional
from app.database import get_db
from app.utils.security import get_current_user

# Mesmas constantes do security.py
from app.utils.security import SECRET_KEY, ALGORITHM
import jwt  # PyJWT — mesma lib usada no security.py
from jwt.exceptions import InvalidTokenError

router = APIRouter()

FILES_DIRECTORY = os.path.join(os.getcwd(), "files")
os.makedirs(FILES_DIRECTORY, exist_ok=True)


def _validar_permissao_safra(id_safra: int, user_id: int, db: Connection):
    """Garante segurança baseada em RBAC e na equipe_fazendas."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT t.id_fazenda, s.status FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        WHERE s.id = ? AND s.ativo = 1 AND t.ativo = 1
    """, (id_safra,))
    res = cursor.fetchone()
    if not res:
        raise HTTPException(status_code=404, detail="Safra selecionada não existe ou foi removida.")

    id_fazenda, status_safra = res[0], res[1]

    cursor.execute(
        "SELECT 1 FROM equipe_fazendas WHERE id_fazenda = ? AND id_usuario = ?",
        (id_fazenda, user_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Acesso negado. Você não é membro da equipe desta fazenda.")

    return status_safra


# =============================================================================
# GET / — Listar todas as atividades da equipe do usuário
# =============================================================================
@router.get("")
def listar_atividades(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("""
        SELECT a.*, s.variedade_cultura AS nome_safra, u.nome AS responsavel
        FROM atividades a
        JOIN safras s ON a.id_safra = s.id
        JOIN talhoes t ON s.id_talhao = t.id
        JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
        JOIN usuarios u ON a.id_responsavel = u.id
        WHERE ef.id_usuario = ?
    """, (current_user["id"],))

    colunas = [col[0] for col in cursor.description]
    return [dict(zip(colunas, row)) for row in cursor.fetchall()]


# =============================================================================
# GET /{id} — Buscar atividade por ID com todos os detalhes (JOINs completos)
# =============================================================================
@router.get("/{id}")
def obter_atividade_por_id(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()

    # Busca dados principais + nome da safra + nome do responsável
    cursor.execute("""
        SELECT
            a.id,
            a.id_safra,
            a.id_responsavel,
            a.tipo_atividade,
            a.status,
            a.data_execucao,
            s.variedade_cultura   AS nome_safra,
            u.nome                AS responsavel
        FROM atividades a
        JOIN safras s ON a.id_safra = s.id
        JOIN usuarios u ON a.id_responsavel = u.id
        WHERE a.id = ?
    """, (id,))

    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    colunas = [col[0] for col in cursor.description]
    atv = dict(zip(colunas, row))

    # Valida se o usuário tem acesso à fazenda desta atividade
    _validar_permissao_safra(atv["id_safra"], current_user["id"], db)

    # Anexa detalhes de irrigação (se existirem)
    cursor.execute("""
        SELECT lamina_mm, horas_aplicacao
        FROM detalhes_irrigacao
        WHERE id_atividade = ?
    """, (id,))
    irr = cursor.fetchone()
    if irr:
        atv["lamina_mm"]       = irr[0]
        atv["horas_aplicacao"] = irr[1]

    # Anexa detalhes de insumos/manejo (se existirem)
    cursor.execute("""
        SELECT produto_usado,
               praga_doenca_identificada,
               caminho_foto_nota_fiscal,
               caminho_foto_receita_agronomica
        FROM detalhes_manejo_insumos
        WHERE id_atividade = ?
    """, (id,))
    ins = cursor.fetchone()
    if ins:
        atv["produto_usado"]                    = ins[0]
        atv["praga_doenca_identificada"]        = ins[1]
        atv["caminho_foto_nota_fiscal"]         = ins[2]
        atv["caminho_foto_receita_agronomica"]  = ins[3]

    return atv


# =============================================================================
# GET /{id}/arquivo/{tipo} — Servir arquivo para download (Gestor ou Técnico)
#   tipo aceito: "nota_fiscal" | "receita_agronomica"
#
#   Autenticação via query param ?token=<jwt> porque links <a href> abertos
#   em nova aba não enviam o header Authorization automaticamente.
# =============================================================================
@router.get("/{id}/arquivo/{tipo}")
def baixar_arquivo_atividade(
    id: int,
    tipo: str,
    token: str = Query(..., description="JWT do usuário (mesmo do localStorage)"),
    db: Connection = Depends(get_db)
):
    if tipo not in ("nota_fiscal", "receita_agronomica"):
        raise HTTPException(status_code=400, detail="Tipo inválido. Use 'nota_fiscal' ou 'receita_agronomica'.")

    # ── Valida o JWT manualmente (sem depender do header Authorization) ──────
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")   # mesmo campo que o security.py usa
        if user_id is None:
            raise ValueError("Payload sem sub")
        user_id = int(user_id)
    except (InvalidTokenError, ValueError, Exception):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")

    cursor = db.cursor()

    # Garante que a atividade existe e pega o id_safra para validar acesso
    cursor.execute("SELECT id_safra FROM atividades WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    _validar_permissao_safra(row[0], user_id, db)

    # Busca o caminho do arquivo solicitado
    coluna = "caminho_foto_nota_fiscal" if tipo == "nota_fiscal" else "caminho_foto_receita_agronomica"
    cursor.execute(f"SELECT {coluna} FROM detalhes_manejo_insumos WHERE id_atividade = ?", (id,))
    res = cursor.fetchone()

    if not res or not res[0]:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado para esta atividade.")

    # O banco guarda como "files/NF_ATV_1.pdf" — monta o caminho absoluto
    caminho_absoluto = os.path.join(os.getcwd(), res[0])

    if not os.path.exists(caminho_absoluto):
        raise HTTPException(status_code=404, detail="Arquivo físico não localizado no servidor.")

    return FileResponse(
        path=caminho_absoluto,
        filename=os.path.basename(caminho_absoluto),
        media_type="application/octet-stream"   # força download no browser
    )


# =============================================================================
# POST — Cadastrar nova atividade
# =============================================================================
@router.post("", status_code=status.HTTP_201_CREATED)
def registrar_nova_atividade(
    id_safra: int = Form(...),
    tipo_atividade: str = Form(...),
    status_atv: str = Form(..., alias="status"),
    data_execucao: str = Form(...),
    lamina_mm: Optional[float] = Form(None),
    horas_aplicacao: Optional[float] = Form(None),
    produto_usado: Optional[str] = Form(None),
    praga_doenca_identificada: Optional[str] = Form(None),
    caminho_foto_nota_fiscal: Optional[UploadFile] = File(None),
    caminho_foto_receita_agronomica: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    if tipo_atividade not in ('Adubação', 'Irrigação', 'Pulverização', 'Manejo de pragas/doenças', 'Plantio', 'Colheita'):
        raise HTTPException(status_code=400, detail="Operação informada inválida.")
    if status_atv not in ('Agendado', 'Em andamento', 'Realizado'):
        raise HTTPException(status_code=400, detail="Status de atividade inválido.")

    status_safra = _validar_permissao_safra(id_safra, current_user["id"], db)
    if status_safra == "Colhida/Finalizada":
        raise HTTPException(status_code=400, detail="Não é permitido registrar atividades para uma safra concluída/finalizada.")

    cursor = db.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute("""
            INSERT INTO atividades (id_safra, id_responsavel, tipo_atividade, status, data_execucao)
            VALUES (?, ?, ?, ?, ?)
        """, (id_safra, current_user["id"], tipo_atividade, status_atv, data_execucao))

        id_nova_atv = cursor.lastrowid

        if tipo_atividade == 'Irrigação':
            if lamina_mm is None or horas_aplicacao is None:
                raise HTTPException(status_code=400, detail="Métricas de lâmina e horas são obrigatórias.")
            cursor.execute("""
                INSERT INTO detalhes_irrigacao (id_atividade, lamina_mm, horas_aplicacao) VALUES (?, ?, ?)
            """, (id_nova_atv, lamina_mm, horas_aplicacao))

        elif tipo_atividade in ('Adubação', 'Pulverização', 'Manejo de pragas/doenças'):
            if not produto_usado or not produto_usado.strip():
                raise HTTPException(status_code=400, detail="Definição do insumo é obrigatória.")
            if tipo_atividade == 'Manejo de pragas/doenças' and not praga_doenca_identificada:
                raise HTTPException(status_code=400, detail="Obrigatório detalhar a praga/doença identificada.")
            if not caminho_foto_nota_fiscal or not caminho_foto_receita_agronomica:
                raise HTTPException(status_code=400, detail="Os uploads de Nota Fiscal e Receita são obrigatórios.")

            ext_nf  = caminho_foto_nota_fiscal.filename.split(".")[-1].lower()
            ext_rec = caminho_foto_receita_agronomica.filename.split(".")[-1].lower()

            if ext_nf not in ('pdf', 'jpg', 'jpeg', 'png') or ext_rec != 'pdf':
                raise HTTPException(status_code=400, detail="Formatos de arquivo inválidos.")

            nome_final_nf  = f"NF_ATV_{id_nova_atv}.{ext_nf}"
            nome_final_rec = f"REC_ATV_{id_nova_atv}.{ext_rec}"
            caminho_hd_nf  = os.path.join(FILES_DIRECTORY, nome_final_nf)
            caminho_hd_rec = os.path.join(FILES_DIRECTORY, nome_final_rec)

            with open(caminho_hd_nf,  "wb") as f_nf:  shutil.copyfileobj(caminho_foto_nota_fiscal.file, f_nf)
            with open(caminho_hd_rec, "wb") as f_rec: shutil.copyfileobj(caminho_foto_receita_agronomica.file, f_rec)

            cursor.execute("""
                INSERT INTO detalhes_manejo_insumos
                    (id_atividade, produto_usado, praga_doenca_identificada,
                     caminho_foto_nota_fiscal, caminho_foto_receita_agronomica)
                VALUES (?, ?, ?, ?, ?)
            """, (id_nova_atv, produto_usado, praga_doenca_identificada,
                  f"files/{nome_final_nf}", f"files/{nome_final_rec}"))

        cursor.execute("""
            INSERT INTO logs_auditoria (id_usuario, acao, detalhes) VALUES (?, ?, ?)
        """, (current_user["id"], "INSERIR_ATIVIDADE", f"Atividade ID {id_nova_atv} criada."))

        db.commit()
        return {"message": "Atividade gravada com sucesso.", "id": id_nova_atv}

    except Exception as e:
        db.rollback()
        if 'caminho_hd_nf'  in locals() and os.path.exists(caminho_hd_nf):  os.remove(caminho_hd_nf)
        if 'caminho_hd_rec' in locals() and os.path.exists(caminho_hd_rec): os.remove(caminho_hd_rec)
        if isinstance(e, HTTPException): raise e
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PUT /{id} — Atualizar atividade
# =============================================================================
@router.put("/{id}")
def atualizar_atividade(
    id: int,
    id_safra: int = Form(...),
    tipo_atividade: str = Form(...),
    status_atv: str = Form(..., alias="status"),
    data_execucao: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT status, id_safra FROM atividades WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    status_atual, id_safra_atual = row
    _validar_permissao_safra(id_safra_atual, current_user["id"], db)

    if status_atual == "Realizado":
        raise HTTPException(status_code=400, detail="Atividades finalizadas não podem ser alteradas.")

    if status_atual == "Em andamento":
        if status_atv != "Realizado":
            raise HTTPException(status_code=400, detail="Atividades em andamento só podem ser alteradas para Realizado.")
        cursor.execute("UPDATE atividades SET status = ? WHERE id = ?", (status_atv, id))

    elif status_atual == "Agendado":
        status_safra = _validar_permissao_safra(id_safra, current_user["id"], db)
        if status_safra == "Colhida/Finalizada":
            raise HTTPException(status_code=400, detail="Não é permitido mover uma atividade para uma safra concluída.")
        cursor.execute("""
            UPDATE atividades SET id_safra = ?, tipo_atividade = ?, status = ?, data_execucao = ?
            WHERE id = ?
        """, (id_safra, tipo_atividade, status_atv, data_execucao, id))
    else:
        raise HTTPException(status_code=400, detail="Mudança de estado não permitida.")

    db.commit()
    return {"message": "Atividade atualizada com sucesso."}


# =============================================================================
# DELETE /{id} — Excluir atividade (somente Agendado)
# =============================================================================
@router.delete("/{id}")
def excluir_atividade_por_id(
    id: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("SELECT status, id_safra FROM atividades WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Atividade não encontrada.")

    status_atual, id_safra = row
    _validar_permissao_safra(id_safra, current_user["id"], db)

    if status_atual != "Agendado":
        raise HTTPException(status_code=400, detail="Apenas atividades agendadas podem ser excluídas.")

    cursor.execute("DELETE FROM atividades WHERE id = ?", (id,))
    db.commit()
    return {"message": "Atividade excluída com sucesso."}