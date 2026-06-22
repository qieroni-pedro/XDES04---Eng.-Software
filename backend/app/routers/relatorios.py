"""
AgroGestor – Módulo de Relatórios
Relatório de Histórico de Safra (Linha do Tempo)

Geração de PDF com QR Code de autenticidade no rodapé (proposta do Atila):
  O PDF traz no rodapé um QR Code que aponta para a página pública
  autenticidade.html, onde auditores e credores podem consultar a linha
  do tempo da safra e baixar as Notas Fiscais / Receitas Agronômicas
  vinculadas a cada atividade, com suas respectivas datas.
"""

import os
import hmac
import hashlib
from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlite3 import Connection

from app.database import get_db
from app.utils.security import get_current_user, SECRET_KEY, ALGORITHM
import jwt
from jwt.exceptions import InvalidTokenError

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage, HRFlowable
)

import qrcode

router = APIRouter()

FRONTEND_BASE_URL = os.environ.get("AGRO_FRONTEND_URL", "http://127.0.0.1:5500")

VERDE_PRINCIPAL = colors.HexColor("#2E7D32")
VERDE_ESCURO    = colors.HexColor("#1B5E20")
CINZA_CLARO     = colors.HexColor("#F1F5F9")
CINZA_TEXTO     = colors.HexColor("#475569")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _gerar_codigo_verificacao(id_safra: int) -> str:
    msg = f"AGROGESTOR-AUTENTICIDADE-SAFRA-{id_safra}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]


def _gerar_codigo_verificacao_multipla(ids_safras: list) -> str:
    """Mesma lógica HMAC do histórico individual, aplicada a um conjunto ordenado de IDs.
    Garante que o código muda se a combinação de safras comparadas mudar."""
    ids_ordenados = ",".join(str(i) for i in sorted(ids_safras))
    msg = f"AGROGESTOR-AUTENTICIDADE-COMPARATIVO-{ids_ordenados}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]


def _validar_codigo_verificacao_multipla(ids_safras: list, codigo: str):
    esperado = _gerar_codigo_verificacao_multipla(ids_safras)
    if not hmac.compare_digest(esperado, codigo or ""):
        raise HTTPException(status_code=403, detail="Código de verificação inválido.")


def _validar_codigo_verificacao(id_safra: int, codigo: str):
    esperado = _gerar_codigo_verificacao(id_safra)
    if not hmac.compare_digest(esperado, codigo or ""):
        raise HTTPException(status_code=403, detail="Código de verificação inválido.")


def _validar_jwt_query(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError()
        return {"id": int(user_id), "perfil": payload.get("perfil")}
    except (InvalidTokenError, ValueError, Exception):
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")


def _obter_safra_autorizada(id_safra: int, user_id: int, db: Connection):
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.id, s.variedade_cultura, s.data_inicio_prevista, s.data_colheita_prevista,
               s.status, s.produtividade_safra, t.nome AS nome_talhao, t.id_fazenda
        FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        WHERE s.id = ? AND s.ativo = 1
    """, (id_safra,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Safra não encontrada.")

    safra = {
        "id": row[0], "variedade_cultura": row[1], "data_inicio_prevista": row[2],
        "data_colheita_prevista": row[3], "status": row[4],
        "produtividade_safra": row[5], "nome_talhao": row[6], "id_fazenda": row[7],
    }

    cursor.execute(
        "SELECT 1 FROM equipe_fazendas WHERE id_fazenda = ? AND id_usuario = ?",
        (safra["id_fazenda"], user_id)
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Acesso negado.")

    if safra["status"] != "Colhida/Finalizada":
        raise HTTPException(
            status_code=400,
            detail="Relatório disponível apenas para safras com status 'Colhida/Finalizada'."
        )
    return safra


def _calcular_duracao_dias(data_inicio: str, data_fim: str) -> int:
    try:
        return (datetime.strptime(data_fim, "%Y-%m-%d") - datetime.strptime(data_inicio, "%Y-%m-%d")).days
    except (ValueError, TypeError):
        return 0


def _formatar_data_br(data_iso: str) -> str:
    try:
        return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return data_iso or "—"


def _montar_linha_do_tempo(id_safra: int, db: Connection):
    cursor = db.cursor()

    cursor.execute("""
        SELECT a.id, a.tipo_atividade, a.data_execucao, u.nome AS responsavel,
               di.lamina_mm, di.horas_aplicacao,
               dmi.produto_usado, dmi.praga_doenca_identificada,
               dmi.caminho_foto_nota_fiscal, dmi.caminho_foto_receita_agronomica
        FROM atividades a
        JOIN usuarios u ON a.id_responsavel = u.id
        LEFT JOIN detalhes_irrigacao di ON di.id_atividade = a.id
        LEFT JOIN detalhes_manejo_insumos dmi ON dmi.id_atividade = a.id
        WHERE a.id_safra = ? AND a.status = 'Realizado'
        ORDER BY a.data_execucao ASC
    """, (id_safra,))

    eventos = []
    for r in cursor.fetchall():
        (aid, tipo, data_exec, responsavel, lamina, horas,
         produto, praga, caminho_nf, caminho_rec) = r

        if tipo == "Irrigação" and lamina is not None:
            detalhes = f"Lâmina aplicada: {lamina} mm | Duração: {horas} h"
        elif produto:
            detalhes = f"Produto: {produto}"
            if praga:
                detalhes += f" | Praga/doença: {praga}"
        else:
            detalhes = "—"

        eventos.append({
            "id_origem": aid, "origem": "atividade",
            "data": data_exec, "tipo": tipo,
            "responsavel": responsavel, "detalhes": detalhes,
            "tem_nota_fiscal": bool(caminho_nf),
            "tem_receita": bool(caminho_rec),
        })

    cursor.execute("""
        SELECT id, tipo_evento, data_ocorrência, descricao_danos
        FROM eventos_extremos WHERE id_safra = ?
        ORDER BY data_ocorrência ASC
    """, (id_safra,))

    for r in cursor.fetchall():
        eid, tipo_evento, data_oc, descricao = r
        eventos.append({
            "id_origem": eid, "origem": "evento_extremo",
            "data": data_oc, "tipo": f"Evento Extremo: {tipo_evento}",
            "responsavel": "—", "detalhes": descricao,
            "tem_nota_fiscal": False, "tem_receita": False,
        })

    eventos.sort(key=lambda e: e["data"] or "")
    return eventos


# ─────────────────────────────────────────────────────────────────────────────
# LISTA DE SAFRAS ENCERRADAS — alimenta o select do frontend
# GET /api/v1/relatorios/safras-encerradas
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/safras-encerradas")
def listar_safras_encerradas(
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.id, s.variedade_cultura, t.nome AS nome_talhao,
               s.data_inicio_prevista, s.data_colheita_prevista, s.produtividade_safra
        FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        JOIN equipe_fazendas ef ON t.id_fazenda = ef.id_fazenda
        WHERE ef.id_usuario = ? AND s.ativo = 1 AND s.status = 'Colhida/Finalizada'
        ORDER BY s.data_colheita_prevista DESC
    """, (current_user["id"],))

    return [
        {
            "id": r[0],
            "label": f"{r[2]} – {r[1]}",
            "data_semeadura": r[3],
            "data_colheita": r[4],
            "produtividade_safra": r[5],
        }
        for r in cursor.fetchall()
    ]


# ─────────────────────────────────────────────────────────────────────────────
# COMPARATIVO DE PRODUTIVIDADE — JSON (RFS16)
# GET /api/v1/relatorios/comparativo?ids=1,2,3
#
# RN09 — máximo de 5 safras por relatório
# RN10 — unidade de medida padronizada (sc/ha em todo o modelo de dados)
# RN11 — alerta quando as safras comparadas são de culturas/espécies distintas
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/comparativo")
def relatorio_comparativo(
    ids: str = Query(..., description="IDs das safras separados por vírgula (2 a 5 safras)"),
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    try:
        lista_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Parâmetro 'ids' inválido. Use IDs numéricos separados por vírgula.")

    if len(lista_ids) > 5:
        raise HTTPException(
            status_code=400,
            detail="Limite máximo atingido. É permitido comparar até 5 safras por relatório."
        )
    if len(lista_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecione ao menos 2 safras para o relatório comparativo.")

    safras = [_obter_safra_autorizada(sid, current_user["id"], db) for sid in lista_ids]

    resultado = []
    especies = set()
    for safra in safras:
        duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
        especie = safra["variedade_cultura"].split(" ")[0] if safra["variedade_cultura"] else "—"
        especies.add(especie.lower())

        resultado.append({
            "id": safra["id"],
            "talhao": safra["nome_talhao"],
            "variedade": safra["variedade_cultura"],
            "data_semeadura_br": _formatar_data_br(safra["data_inicio_prevista"]),
            "data_colheita_br":  _formatar_data_br(safra["data_colheita_prevista"]),
            "duracao_dias": duracao,
            "produtividade_safra": safra["produtividade_safra"],
            "linha_tempo": [
                {**ev, "data_br": _formatar_data_br(ev["data"])}
                for ev in _montar_linha_do_tempo(safra["id"], db)
            ],
        })

    alerta_variedades = len(especies) > 1
    alerta_mensagem = (
        "As safras selecionadas pertencem a culturas biologicamente distintas. "
        "A comparação ainda é exibida para fins de análise de uso da terra."
        if alerta_variedades else None
    )

    codigo = _gerar_codigo_verificacao_multipla(lista_ids)
    url_verificacao = f"{FRONTEND_BASE_URL}/autenticidade.html?safras={ids}&codigo={codigo}"

    return {
        "safras": resultado,
        "alerta_variedades": alerta_variedades,
        "alerta_mensagem": alerta_mensagem,
        "unidade_produtividade": "sc/ha",
        "verificacao": {
            "codigo": codigo,
            "url": url_verificacao,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# COMPARATIVO DE PRODUTIVIDADE — PDF para download
# GET /api/v1/relatorios/comparativo/pdf?ids=1,2,3&token=...
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/comparativo/pdf")
def relatorio_comparativo_pdf(
    ids: str = Query(...),
    token: str = Query(...),
    db: Connection = Depends(get_db)
):
    current_user = _validar_jwt_query(token)

    try:
        lista_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Parâmetro 'ids' inválido.")

    if len(lista_ids) > 5:
        raise HTTPException(status_code=400, detail="Limite máximo atingido. É permitido comparar até 5 safras por relatório.")
    if len(lista_ids) < 2:
        raise HTTPException(status_code=400, detail="Selecione ao menos 2 safras para o relatório comparativo.")

    safras = [_obter_safra_autorizada(sid, current_user["id"], db) for sid in lista_ids]

    dados = []
    especies = set()
    todos_eventos = []
    for safra in safras:
        duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
        especie = safra["variedade_cultura"].split(" ")[0] if safra["variedade_cultura"] else "—"
        especies.add(especie.lower())
        dados.append({
            "label": safra["nome_talhao"],
            "variedade": safra["variedade_cultura"],
            "data_semeadura_br": _formatar_data_br(safra["data_inicio_prevista"]),
            "data_colheita_br":  _formatar_data_br(safra["data_colheita_prevista"]),
            "duracao_dias": duracao,
            "produtividade_safra": safra["produtividade_safra"] or 0,
        })
        for ev in _montar_linha_do_tempo(safra["id"], db):
            todos_eventos.append({**ev, "data_br": _formatar_data_br(ev["data"]), "safra_label": safra["nome_talhao"]})
    todos_eventos.sort(key=lambda e: e["data"] or "")
    alerta_variedades = len(especies) > 1

    codigo = _gerar_codigo_verificacao_multipla(lista_ids)
    url_verificacao = f"{FRONTEND_BASE_URL}/autenticidade.html?safras={ids}&codigo={codigo}"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18*mm, bottomMargin=18*mm,
        leftMargin=18*mm, rightMargin=18*mm,
        title="Relatório Comparativo de Produtividade e Ciclos"
    )

    styles  = getSampleStyleSheet()
    s_titulo = ParagraphStyle("T", parent=styles["Heading1"], textColor=VERDE_ESCURO, fontSize=16, spaceAfter=2)
    s_sub    = ParagraphStyle("S", parent=styles["Normal"], textColor=CINZA_TEXTO, fontSize=9, spaceAfter=10)
    s_secao  = ParagraphStyle("Se", parent=styles["Heading2"], textColor=VERDE_PRINCIPAL, fontSize=11, spaceBefore=12, spaceAfter=6)
    s_cel    = ParagraphStyle("C", parent=styles["Normal"], fontSize=8, leading=10)
    s_cel_b  = ParagraphStyle("CB", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold")
    s_nota   = ParagraphStyle("N", parent=s_cel, textColor=CINZA_TEXTO, fontSize=7.5)

    elementos = []
    elementos.append(Paragraph("AgroGestor — Relatório Comparativo de Produtividade e Ciclos", s_titulo))
    elementos.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  {len(dados)} safras comparadas",
        s_sub
    ))
    elementos.append(HRFlowable(width="100%", color=VERDE_PRINCIPAL, thickness=1.2))
    elementos.append(Spacer(1, 8))

    if alerta_variedades:
        elementos.append(Paragraph(
            "⚠ As safras selecionadas pertencem a culturas biologicamente distintas. "
            "A comparação é exibida para fins de análise de uso da terra.",
            ParagraphStyle("alerta", parent=s_cel, textColor=colors.HexColor("#B45309"),
                           backColor=colors.HexColor("#FEF3C7"), borderPadding=6)
        ))
        elementos.append(Spacer(1, 8))

    # Matriz comparativa
    elementos.append(Paragraph("Matriz Comparativa de Dados Gerais", s_secao))
    cabecalho = [
        Paragraph("Talhão / Safra", s_cel_b), Paragraph("Variedade", s_cel_b),
        Paragraph("Semeadura", s_cel_b), Paragraph("Colheita", s_cel_b),
        Paragraph("Duração (dias)", s_cel_b), Paragraph("Produtividade (sc/ha)", s_cel_b),
    ]
    linhas = [cabecalho]
    for d in dados:
        linhas.append([
            Paragraph(d["label"], s_cel), Paragraph(d["variedade"], s_cel),
            Paragraph(d["data_semeadura_br"], s_cel), Paragraph(d["data_colheita_br"], s_cel),
            Paragraph(str(d["duracao_dias"]), s_cel), Paragraph(f"{d['produtividade_safra']}", s_cel),
        ])
    tabela_matriz = Table(linhas, colWidths=[32*mm, 38*mm, 22*mm, 22*mm, 24*mm, 30*mm], repeatRows=1)
    tabela_matriz.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE_PRINCIPAL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA_CLARO]),
    ]))
    elementos.append(tabela_matriz)
    elementos.append(Spacer(1, 14))

    # Linha do tempo consolidada (todas as safras)
    elementos.append(Paragraph("Histórico de Manejos e Eventos Extremos (Todas as Safras)", s_secao))
    if not todos_eventos:
        elementos.append(Paragraph("Nenhuma atividade ou evento registrado nas safras selecionadas.", s_cel))
    else:
        cab_tl = [
            Paragraph("Data", s_cel_b), Paragraph("Safra / Talhão", s_cel_b),
            Paragraph("Atividade / Evento", s_cel_b), Paragraph("Detalhes", s_cel_b),
        ]
        linhas_tl = [cab_tl]
        for ev in todos_eventos:
            linhas_tl.append([
                Paragraph(ev["data_br"], s_cel), Paragraph(ev["safra_label"], s_cel),
                Paragraph(ev["tipo"], s_cel), Paragraph(ev["detalhes"], s_cel),
            ])
        tabela_tl = Table(linhas_tl, colWidths=[20*mm, 35*mm, 35*mm, 76*mm], repeatRows=1)
        estilo_tl = [
            ("BACKGROUND", (0, 0), (-1, 0), VERDE_PRINCIPAL),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("BOX",        (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID",  (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i, ev in enumerate(todos_eventos, start=1):
            if ev["origem"] == "evento_extremo":
                estilo_tl.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FEF2F2")))
            elif i % 2 == 0:
                estilo_tl.append(("BACKGROUND", (0, i), (-1, i), CINZA_CLARO))
        tabela_tl.setStyle(TableStyle(estilo_tl))
        elementos.append(tabela_tl)

    elementos.append(Spacer(1, 16))
    elementos.append(HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"), thickness=0.6))

    # Rodapé com QR Code
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(url_verificacao)
    qr.make()
    qr_buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_buf, format="PNG")
    qr_buf.seek(0)

    rodape = Table([[
        RLImage(qr_buf, width=22*mm, height=22*mm),
        Paragraph(
            "<b>Verificação de Autenticidade</b><br/>"
            "Escaneie o QR Code para acessar a página oficial de verificação, consultar a linha do tempo "
            "consolidada e baixar as Notas Fiscais e Receitas Agronômicas vinculadas a estas safras.<br/>"
            f"Código de verificação: <b>{codigo}</b>",
            s_nota
        )
    ]], colWidths=[26*mm, 139*mm])
    rodape.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
    ]))
    elementos.append(rodape)

    doc.build(elementos)
    buffer.seek(0)

    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Relatorio_Comparativo_Produtividade.pdf"'}
    )


# ─────────────────────────────────────────────────────────────────────────────
# HISTÓRICO DE SAFRA — JSON (para exibição na tela)
# GET /api/v1/relatorios/historico/{id_safra}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/historico/{id_safra}")
def relatorio_historico_safra(
    id_safra: int,
    current_user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db)
):
    safra = _obter_safra_autorizada(id_safra, current_user["id"], db)
    duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
    linha_tempo = _montar_linha_do_tempo(id_safra, db)

    codigo = _gerar_codigo_verificacao(id_safra)
    url_verificacao = f"{FRONTEND_BASE_URL}/autenticidade.html?safra={id_safra}&codigo={codigo}"

    return {
        "safra": {
            "id": safra["id"],
            "talhao": safra["nome_talhao"],
            "variedade": safra["variedade_cultura"],
            "data_semeadura_br": _formatar_data_br(safra["data_inicio_prevista"]),
            "data_colheita_br":  _formatar_data_br(safra["data_colheita_prevista"]),
            "duracao_dias": duracao,
            "produtividade_safra": safra["produtividade_safra"],
        },
        "linha_tempo": [
            {**ev, "data_br": _formatar_data_br(ev["data"])} for ev in linha_tempo
        ],
        "verificacao": {
            "codigo": codigo,
            "url": url_verificacao,
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# HISTÓRICO DE SAFRA — PDF para download
# GET /api/v1/relatorios/historico/{id_safra}/pdf?token=...
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/historico/{id_safra}/pdf")
def relatorio_historico_safra_pdf(
    id_safra: int,
    token: str = Query(...),
    db: Connection = Depends(get_db)
):
    current_user = _validar_jwt_query(token)
    safra = _obter_safra_autorizada(id_safra, current_user["id"], db)
    duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
    linha_tempo = _montar_linha_do_tempo(id_safra, db)
    codigo = _gerar_codigo_verificacao(id_safra)
    url_verificacao = f"{FRONTEND_BASE_URL}/autenticidade.html?safra={id_safra}&codigo={codigo}"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=18*mm, bottomMargin=22*mm,
        leftMargin=18*mm, rightMargin=18*mm,
        title=f"Histórico de Safra – {safra['nome_talhao']}"
    )

    styles = getSampleStyleSheet()
    s_titulo  = ParagraphStyle("T", parent=styles["Heading1"],
                               textColor=VERDE_ESCURO, fontSize=16, spaceAfter=2)
    s_sub     = ParagraphStyle("S", parent=styles["Normal"],
                               textColor=CINZA_TEXTO, fontSize=9, spaceAfter=10)
    s_secao   = ParagraphStyle("Se", parent=styles["Heading2"],
                               textColor=VERDE_PRINCIPAL, fontSize=11, spaceBefore=10, spaceAfter=6)
    s_cel     = ParagraphStyle("C", parent=styles["Normal"], fontSize=8, leading=10)
    s_cel_b   = ParagraphStyle("CB", parent=styles["Normal"], fontSize=8, leading=10,
                               fontName="Helvetica-Bold")
    s_nota    = ParagraphStyle("N", parent=s_cel, textColor=CINZA_TEXTO, fontSize=7.5)

    elementos = []

    # Cabeçalho
    elementos.append(Paragraph("AgroGestor — Relatório de Histórico de Safra", s_titulo))
    elementos.append(Paragraph(
        f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  "
        f"Safra #{safra['id']} — {safra['nome_talhao']}",
        s_sub
    ))
    elementos.append(HRFlowable(width="100%", color=VERDE_PRINCIPAL, thickness=1.2))
    elementos.append(Spacer(1, 8))

    # Dados gerais
    elementos.append(Paragraph("Dados Gerais da Safra", s_secao))
    tabela_dg = Table([
        ["Talhão de cultivo",    safra["nome_talhao"]],
        ["Variedade da cultura", safra["variedade_cultura"]],
        ["Data de semeadura",    _formatar_data_br(safra["data_inicio_prevista"])],
        ["Data da colheita",     _formatar_data_br(safra["data_colheita_prevista"])],
        ["Duração do ciclo",     f"{duracao} dias"],
        ["Produtividade obtida", f"{safra['produtividade_safra']} sc/ha" if safra["produtividade_safra"] is not None else "—"],
    ], colWidths=[55*mm, 110*mm])
    tabela_dg.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), CINZA_CLARO),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.HexColor("#1E293B")),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(tabela_dg)
    elementos.append(Spacer(1, 10))

    # Linha do tempo
    elementos.append(Paragraph("Histórico de Manejos e Eventos Extremos (Linha do Tempo)", s_secao))

    if not linha_tempo:
        elementos.append(Paragraph("Nenhuma atividade ou evento registrado para esta safra.", s_cel))
    else:
        cabecalho = [
            Paragraph("Data", s_cel_b),
            Paragraph("Atividade / Evento", s_cel_b),
            Paragraph("Responsável", s_cel_b),
            Paragraph("Detalhes", s_cel_b),
            Paragraph("Comprovantes*", s_cel_b),
        ]
        linhas = [cabecalho]
        for ev in linha_tempo:
            comp = []
            if ev["tem_nota_fiscal"]: comp.append("NF")
            if ev["tem_receita"]:     comp.append("Receita")
            linhas.append([
                Paragraph(ev["data_br"], s_cel),
                Paragraph(ev["tipo"], s_cel),
                Paragraph(ev["responsavel"], s_cel),
                Paragraph(ev["detalhes"], s_cel),
                Paragraph(" + ".join(comp) if comp else "—", s_cel),
            ])

        tabela_tl = Table(linhas, colWidths=[22*mm, 32*mm, 28*mm, 58*mm, 25*mm], repeatRows=1)
        estilo = [
            ("BACKGROUND",    (0, 0), (-1, 0), VERDE_PRINCIPAL),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID",     (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for i, ev in enumerate(linha_tempo, start=1):
            if ev["origem"] == "evento_extremo":
                estilo.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FEF2F2")))
            elif i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), CINZA_CLARO))
        tabela_tl.setStyle(TableStyle(estilo))
        elementos.append(tabela_tl)
        elementos.append(Spacer(1, 4))
        elementos.append(Paragraph(
            "* Os comprovantes podem ser baixados na página de verificação acessível pelo QR Code abaixo.",
            s_nota
        ))

    elementos.append(Spacer(1, 16))
    elementos.append(HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"), thickness=0.6))

    # Rodapé com QR Code
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(url_verificacao)
    qr.make()
    qr_buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(qr_buf, format="PNG")
    qr_buf.seek(0)

    rodape = Table([[
        RLImage(qr_buf, width=22*mm, height=22*mm),
        Paragraph(
            "<b>Verificação de Autenticidade</b><br/>"
            "Escaneie o QR Code para acessar a página oficial de verificação, consultar a linha do tempo "
            "e baixar as Notas Fiscais e Receitas Agronômicas vinculadas a esta safra.<br/>"
            f"Código de verificação: <b>{codigo}</b>",
            s_nota
        )
    ]], colWidths=[26*mm, 139*mm])
    rodape.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",  (0, 0), (-1, -1), 8),
    ]))
    elementos.append(rodape)

    doc.build(elementos)
    buffer.seek(0)

    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Historico_Safra_{id_safra}.pdf"'}
    )


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PÚBLICA DE AUTENTICIDADE (sem login) — acessada via QR Code
# GET /api/v1/relatorios/autenticidade/{id_safra}?codigo=...
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/autenticidade/{id_safra}")
def autenticidade_safra(
    id_safra: int,
    codigo: str = Query(...),
    db: Connection = Depends(get_db)
):
    _validar_codigo_verificacao(id_safra, codigo)

    cursor = db.cursor()
    cursor.execute("""
        SELECT s.id, s.variedade_cultura, s.data_inicio_prevista, s.data_colheita_prevista,
               s.status, s.produtividade_safra, t.nome AS nome_talhao
        FROM safras s
        JOIN talhoes t ON s.id_talhao = t.id
        WHERE s.id = ? AND s.ativo = 1
    """, (id_safra,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Safra não encontrada.")

    safra = {
        "id": row[0], "variedade_cultura": row[1], "data_inicio_prevista": row[2],
        "data_colheita_prevista": row[3], "status": row[4],
        "produtividade_safra": row[5], "nome_talhao": row[6],
    }
    duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
    linha_tempo = _montar_linha_do_tempo(id_safra, db)

    comprovantes = []
    for ev in linha_tempo:
        if ev["origem"] != "atividade":
            continue
        if ev["tem_nota_fiscal"]:
            comprovantes.append({
                "id_atividade": ev["id_origem"],
                "tipo_atividade": ev["tipo"],
                "data_br": _formatar_data_br(ev["data"]),
                "rotulo": "Nota Fiscal",
                "url": f"/autenticidade/{id_safra}/arquivo/{ev['id_origem']}/nota_fiscal?codigo={codigo}",
            })
        if ev["tem_receita"]:
            comprovantes.append({
                "id_atividade": ev["id_origem"],
                "tipo_atividade": ev["tipo"],
                "data_br": _formatar_data_br(ev["data"]),
                "rotulo": "Receita Agronômica",
                "url": f"/autenticidade/{id_safra}/arquivo/{ev['id_origem']}/receita_agronomica?codigo={codigo}",
            })

    return {
        "documento": "Relatório Consolidado",
        "safra": {
            "id": safra["id"],
            "talhao": safra["nome_talhao"],
            "variedade": safra["variedade_cultura"],
            "data_semeadura_br": _formatar_data_br(safra["data_inicio_prevista"]),
            "data_colheita_br":  _formatar_data_br(safra["data_colheita_prevista"]),
            "duracao_dias": duracao,
            "produtividade_safra": safra["produtividade_safra"],
            "status": safra["status"],
        },
        "linha_tempo": [
            {**ev, "data_br": _formatar_data_br(ev["data"])} for ev in linha_tempo
        ],
        "comprovantes": comprovantes,
        "verificado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PÁGINA PÚBLICA DE AUTENTICIDADE — MÚLTIPLAS SAFRAS (Comparativo)
# GET /api/v1/relatorios/autenticidade-comparativo?safras=1,2,3&codigo=...
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/autenticidade-comparativo")
def autenticidade_comparativo(
    safras: str = Query(...),
    codigo: str = Query(...),
    db: Connection = Depends(get_db)
):
    try:
        lista_ids = [int(x) for x in safras.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Parâmetro 'safras' inválido.")

    _validar_codigo_verificacao_multipla(lista_ids, codigo)

    cursor = db.cursor()
    resultado_safras = []
    todos_eventos = []
    todos_comprovantes = []

    for id_safra in lista_ids:
        cursor.execute("""
            SELECT s.id, s.variedade_cultura, s.data_inicio_prevista, s.data_colheita_prevista,
                   s.status, s.produtividade_safra, t.nome AS nome_talhao
            FROM safras s
            JOIN talhoes t ON s.id_talhao = t.id
            WHERE s.id = ? AND s.ativo = 1
        """, (id_safra,))
        row = cursor.fetchone()
        if not row:
            continue

        safra = {
            "id": row[0], "variedade_cultura": row[1], "data_inicio_prevista": row[2],
            "data_colheita_prevista": row[3], "produtividade_safra": row[5], "nome_talhao": row[6],
        }
        duracao = _calcular_duracao_dias(safra["data_inicio_prevista"], safra["data_colheita_prevista"])
        linha_tempo = _montar_linha_do_tempo(id_safra, db)

        resultado_safras.append({
            "id": safra["id"],
            "talhao": safra["nome_talhao"],
            "variedade": safra["variedade_cultura"],
            "data_semeadura_br": _formatar_data_br(safra["data_inicio_prevista"]),
            "data_colheita_br":  _formatar_data_br(safra["data_colheita_prevista"]),
            "duracao_dias": duracao,
            "produtividade_safra": safra["produtividade_safra"],
        })

        for ev in linha_tempo:
            todos_eventos.append({
                **ev, "data_br": _formatar_data_br(ev["data"]), "safra_label": safra["nome_talhao"]
            })
            if ev["origem"] != "atividade":
                continue
            if ev["tem_nota_fiscal"]:
                todos_comprovantes.append({
                    "id_atividade": ev["id_origem"], "safra_label": safra["nome_talhao"],
                    "tipo_atividade": ev["tipo"], "data_br": _formatar_data_br(ev["data"]),
                    "rotulo": "Nota Fiscal",
                    "url": f"/autenticidade/{id_safra}/arquivo/{ev['id_origem']}/nota_fiscal?codigo={_gerar_codigo_verificacao(id_safra)}",
                })
            if ev["tem_receita"]:
                todos_comprovantes.append({
                    "id_atividade": ev["id_origem"], "safra_label": safra["nome_talhao"],
                    "tipo_atividade": ev["tipo"], "data_br": _formatar_data_br(ev["data"]),
                    "rotulo": "Receita Agronômica",
                    "url": f"/autenticidade/{id_safra}/arquivo/{ev['id_origem']}/receita_agronomica?codigo={_gerar_codigo_verificacao(id_safra)}",
                })

    if not resultado_safras:
        raise HTTPException(status_code=404, detail="Nenhuma safra válida encontrada.")

    todos_eventos.sort(key=lambda e: e["data"] or "")

    return {
        "documento": "Relatório Comparativo de Produtividade",
        "safras": resultado_safras,
        "linha_tempo": todos_eventos,
        "comprovantes": todos_comprovantes,
        "verificado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD PÚBLICO DE COMPROVANTES (sem login)
# GET /api/v1/relatorios/autenticidade/{id_safra}/arquivo/{id_atividade}/{tipo}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/autenticidade/{id_safra}/arquivo/{id_atividade}/{tipo}")
def autenticidade_download_arquivo(
    id_safra: int,
    id_atividade: int,
    tipo: str,
    codigo: str = Query(...),
    db: Connection = Depends(get_db)
):
    _validar_codigo_verificacao(id_safra, codigo)

    if tipo not in ("nota_fiscal", "receita_agronomica"):
        raise HTTPException(status_code=400, detail="Tipo de arquivo inválido.")

    cursor = db.cursor()
    cursor.execute("SELECT id_safra FROM atividades WHERE id = ?", (id_atividade,))
    row = cursor.fetchone()
    if not row or row[0] != id_safra:
        raise HTTPException(status_code=404, detail="Atividade não pertence a esta safra.")

    coluna = "caminho_foto_nota_fiscal" if tipo == "nota_fiscal" else "caminho_foto_receita_agronomica"
    cursor.execute(f"SELECT {coluna} FROM detalhes_manejo_insumos WHERE id_atividade = ?", (id_atividade,))
    res = cursor.fetchone()
    if not res or not res[0]:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado para esta atividade.")

    caminho = os.path.join(os.getcwd(), res[0])
    if not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Arquivo físico não localizado no servidor.")

    return FileResponse(path=caminho, filename=os.path.basename(caminho), media_type="application/octet-stream")
