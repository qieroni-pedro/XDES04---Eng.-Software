from fastapi import APIRouter, HTTPException, status
import sqlite3

router = APIRouter()
DB_NAME = "agrogestor.db"

@router.get("/{safra_id}/indicadores")
def obter_indicadores_dashboard(safra_id: int):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Ativa a checagem de chaves estrangeiras
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    try:
        # 1. Consulta todas as atividades daquela safra para calcular o percentual do CARD 1
        # Mapeamento do BD: status IN ('Agendado', 'Em andamento', 'Realizado')
        cursor.execute("""
            SELECT status FROM atividades WHERE id_safra = ?;
        """, (safra_id,))
        atividades = cursor.fetchall()
        
        # 2. CARD 2: Linha do tempo com as próximas 5 tarefas agendadas (Status = 'Agendado')
        # Traz o nome do responsável fazendo JOIN com a tabela usuarios
        cursor.execute("""
            SELECT a.data_execucao, a.tipo_atividade, u.nome as responsavel
            FROM atividades a
            JOIN usuarios u ON a.id_responsavel = u.id
            WHERE a.id_safra = ? AND a.status = 'Agendado'
            ORDER BY a.data_execucao ASC 
            LIMIT 5;
        """, (safra_id,))
        proximas_atvs_db = cursor.fetchall()

        # 3. CARD 3: Painel de Alertas Ativos alimentado pela tabela de eventos_extremos
        cursor.execute("""
            SELECT tipo_evento, data_ocorrência, descricao_danos 
            FROM eventos_extremos 
            WHERE id_safra = ?
            ORDER BY data_ocorrência DESC;
        """, (safra_id,))
        alertas_db = cursor.fetchall()

    except sqlite3.OperationalError as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro operacional no banco de dados: {str(e)}"
        )

    conn.close()

    # --- LÓGICA DE CÁLCULO REAL E DINÂMICA (RFS17) ---
    totais = len(atividades)
    # No BD, atividades concluídas têm o status 'Realizado'
    executadas = sum(1 for atv in atividades if atv['status'] == 'Realizado')
    porcentagem = int((executadas / totais) * 100) if totais > 0 else 0

    # Monta a lista cronológica para o Card 2
    lista_atividades = []
    for atv in proximas_atvs_db:
        lista_atividades.append({
            "data": atv["data_execucao"], # Usa a coluna exata do BD
            "nome": atv["tipo_atividade"],
            "responsavel": atv["responsavel"]
        })

    # Monta a lista de alertas críticos para o Card 3 baseada nos eventos extremos salvos
    lista_alertas = []
    for alr in alertas_db:
        lista_alertas.append({
            "tipo": "critico", # Todo evento extremo catalogado gera um bloco de atenção crítico
            "titulo": f"OCORRÊNCIA: {alr['tipo_evento']}",
            "desc": f"Registrado em {alr['data_ocorrência']}: {alr['descricao_danos']}"
        })

    # Retorna o payload limpo que o frontend/js/dashboard.js vai ler
    return {
        "porcentagem": porcentagem,
        "executadas": executadas,
        "totais": totais,
        "proximasAtividades": lista_atividades,
        "alertas": lista_alertas
    }