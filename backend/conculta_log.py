import sqlite3
from datetime import datetime

DB_NAME = "agrogestor.db"

def consultar_logs_auditoria():
    print("=" * 80)
    print(f" CONSULTANDO TABELA: logs_auditoria ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})")
    print("=" * 80)
    
    # Conecta ao banco de dados e configura para retornar linhas como dicionários (Row)
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Executa a busca trazendo o nome do usuário (se houver) através de um LEFT JOIN
        cursor.execute("""
            SELECT l.id, l.id_usuario, u.nome AS nome_usuario, l.acao, l.detalhes, l.data_hora
            FROM logs_auditoria l
            LEFT JOIN usuarios u ON l.id_usuario = u.id
            ORDER BY l.data_hora DESC;
        """)
        
        logs = cursor.fetchall()
        
        if not logs:
            print("\n [AVISO]: A tabela 'logs_auditoria' está VAZIA.")
            print("Nenhum log de alteração ou acesso foi registrado ainda.\n")
            return
            
        print(f" Total de registros encontrados: {len(logs)}\n")
        
        # Cabeçalho da tabela formatada no terminal
        print(f"{'ID':<4} | {'Usuário (ID - Nome)':<25} | {'Ação':<18} | {'Data/Hora':<19} | {'Detalhes'}")
        print("-" * 100)
        
        # Varre os registros imprimindo linha por linha
        for log in logs:
            user_info = "N/A (Excluído/Sistema)"
            if log['id_usuario']:
                user_info = f"{log['id_usuario']} - {log['nome_usuario']}"
                
            # Limita o tamanho do texto de detalhes para não quebrar a linha do terminal
            detalhes = log['detalhes'] if log['detalhes'] else ""
            if len(detalhes) > 35:
                detalhes = detalhes[:32] + "..."
                
            print(f"{log['id']:<4} | {user_info:<25} | {log['acao']:<18} | {log['data_hora']:<19} | {detalhes}")
            
    except sqlite3.OperationalError as e:
        print(f"\n [ERRO OPERACIONAL]: Não foi possível consultar a tabela.")
        print(f"Detalhes do erro: {e}")
        print("Certifique-se de que o arquivo do banco de dados está na mesma pasta e com o nome correto.\n")
        
    finally:
        conn.close()
        print("=" * 80)

if __name__ == "__main__":
    consultar_logs_auditoria()