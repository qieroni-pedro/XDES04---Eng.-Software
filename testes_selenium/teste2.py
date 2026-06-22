import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
BASE_URL = "http://127.0.0.1:5500/frontend"  # ajuste para o endereço do seu frontend

EMAIL = "tecnico.alfa@agrogestor.com"
SENHA = "hash_senha_alfa"

# Caminhos dos arquivos a serem enviados (ajuste os caminhos conforme sua máquina)
ARQUIVO_NF = os.path.abspath("nf.png")
ARQUIVO_RECEITA = os.path.abspath("receita.pdf")

WAIT_TIMEOUT = 15

# Tempo em segundos para pausa visual entre ações do teste
TEMPO_PAUSA_VISUAL = 1.5


# ============================================================================
# FUNÇÕES AUXILIARES DE VISUALIZAÇÃO
# ============================================================================
def espera_visual():
    """Garante uma pausa controlada para que o olho humano acompanhe as ações."""
    time.sleep(TEMPO_PAUSA_VISUAL)


def destacar_elemento(driver, elemento):
    """Aplica uma borda vermelha piscante no elemento para destacar a ação atual."""
    try:
        driver.execute_script("arguments[0].style.border='3px solid red';", elemento)
        time.sleep(0.3)
        driver.execute_script("arguments[0].style.border='';", elemento)
    except Exception:
        pass


# ============================================================================
# SETUP
# ============================================================================
def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    return driver


def fazer_login(driver, wait):
    driver.get(f"{BASE_URL}/index.html")
    espera_visual()

    campo_email = wait.until(EC.presence_of_element_located((By.ID, "txt-email")))
    destacar_elemento(driver, campo_email)
    campo_email.send_keys(EMAIL)
    
    campo_senha = driver.find_element(By.ID, "txt-senha")
    destacar_elemento(driver, campo_senha)
    campo_senha.send_keys(SENHA)
    espera_visual()

    btn_entrar = driver.find_element(By.ID, "btn-entrar")
    destacar_elemento(driver, btn_entrar)
    btn_entrar.click()

    wait.until(EC.url_contains("dashboard.html"))
    print("[OK] Login realizado com sucesso.")
    espera_visual()


# ============================================================================
# MÓDULO: ATIVIDADES (CRUD - Create + Read + Delete)
# ============================================================================
def abrir_pagina_atividades(driver, wait):
    driver.get(f"{BASE_URL}/gerenciar_atividades.html")
    wait.until(EC.presence_of_element_located((By.ID, "btn-nova-atividade")))
    time.sleep(2)  # aguarda carregamento das safras via fetch


def cadastrar_atividade(driver, wait, tipo_atividade, status_atividade, **extra):
    """Abre o modal, preenche e salva uma nova atividade."""
    btn_nova = driver.find_element(By.ID, "btn-nova-atividade")
    destacar_elemento(driver, btn_nova)
    btn_nova.click()
    
    wait.until(EC.visibility_of_element_located((By.ID, "modal-atividade")))
    espera_visual()

    # Seleciona a primeira safra disponível ("Em andamento")
    elem_safra = driver.find_element(By.ID, "id_safra")
    destacar_elemento(driver, elem_safra)
    select_safra = Select(elem_safra)
    opcoes_validas = [o for o in select_safra.options if o.get_attribute("value")]
    assert opcoes_validas, "Nenhuma safra disponível para cadastro de atividade."
    select_safra.select_by_value(opcoes_validas[0].get_attribute("value"))
    espera_visual()

    # Seleciona o tipo de atividade
    elem_tipo = driver.find_element(By.ID, "tipo_atividade")
    destacar_elemento(driver, elem_tipo)
    select_tipo = Select(elem_tipo)
    select_tipo.select_by_value(tipo_atividade)
    time.sleep(1.5)  # tempo adaptado para exibir submenus dinâmicos visualmente

    # Campos específicos por tipo de atividade
    if tipo_atividade == "Irrigação":
        c_lamina = driver.find_element(By.ID, "lamina_mm")
        destacar_elemento(driver, c_lamina)
        c_lamina.send_keys(str(extra.get("lamina_mm", "25.5")))
        
        c_horas = driver.find_element(By.ID, "horas_aplicacao")
        destacar_elemento(driver, c_horas)
        c_horas.send_keys(str(extra.get("horas_aplicacao", "3")))
        espera_visual()

    elif tipo_atividade in ("Adubação", "Pulverização", "Manejo de pragas/doenças"):
        if tipo_atividade == "Manejo de pragas/doenças":
            c_praga = driver.find_element(By.ID, "praga_doenca_identificada")
            destacar_elemento(driver, c_praga)
            c_praga.send_keys(extra.get("praga_doenca_identificada", "Lagarta-do-cartucho"))
            
        c_prod = driver.find_element(By.ID, "produto_usado")
        destacar_elemento(driver, c_prod)
        c_prod.send_keys(extra.get("produto_usado", "Adubo NPK 20-05-20"))
        
        c_qtd = driver.find_element(By.ID, "quantidade_por_ha")
        destacar_elemento(driver, c_qtd)
        c_qtd.send_keys(str(extra.get("quantidade_por_ha", "150")))
        espera_visual()

        # Upload dos arquivos obrigatórios
        c_nf = driver.find_element(By.ID, "caminho_foto_nota_fiscal")
        destacar_elemento(driver, c_nf)
        c_nf.send_keys(ARQUIVO_NF)
        
        c_rec = driver.find_element(By.ID, "caminho_foto_receita_agronomica")
        destacar_elemento(driver, c_rec)
        c_rec.send_keys(ARQUIVO_RECEITA)
        espera_visual()

    # Status e data de execução
    elem_status = driver.find_element(By.ID, "status")
    destacar_elemento(driver, elem_status)
    select_status = Select(elem_status)
    select_status.select_by_value(status_atividade)
    espera_visual()

    campo_data = driver.find_element(By.ID, "data_execucao")
    destacar_elemento(driver, campo_data)
    driver.execute_script("arguments[0].value = arguments[1];", campo_data, extra.get("data_execucao", "2026-06-15"))
    espera_visual()

    # Salva
    btn_submit = driver.find_element(By.ID, "btn-submit")
    destacar_elemento(driver, btn_submit)
    btn_submit.click()

    # Aguarda fechamento do modal (sucesso) ou alerta de erro
    wait.until(EC.invisibility_of_element_located((By.ID, "modal-atividade")))
    time.sleep(2)
    print(f"[OK] Atividade '{tipo_atividade}' cadastrada com sucesso.")


def consultar_atividade_listada(driver, wait):
    """Consulta uma atividade da tabela que possua botão de ação disponível (Read)."""
    wait.until(EC.presence_of_element_located((By.ID, "tbody-atividades")))

    # Filtra linhas que possuem botões de ação ativos
    linhas = driver.find_elements(By.CSS_SELECTOR, "#tbody-atividades tr")

    botao_acao = None
    for linha in linhas:
        botoes = linha.find_elements(By.CSS_SELECTOR, ".row-actions button")
        if botoes:
            botao_acao = botoes[0]
            break

    assert botao_acao is not None, "Nenhuma atividade com botão de ação disponível foi encontrada."
    destacar_elemento(driver, botao_acao)
    espera_visual()
    botao_acao.click()

    wait.until(EC.visibility_of_element_located((By.ID, "modal-atividade")))
    espera_visual()

    candidatos = driver.find_elements(
        By.XPATH,
        "//div[@id='painel-visualizacao']//button[contains(., 'Fechar')] | "
        "//form[@id='form-atividade']//button[contains(., 'Cancelar')]"
    )
    botao_fechar = next(b for b in candidatos if b.is_displayed())
    destacar_elemento(driver, botao_fechar)
    espera_visual()
    botao_fechar.click()
    
    wait.until(EC.invisibility_of_element_located((By.ID, "modal-atividade")))
    time.sleep(1)
    print("[OK] Consulta de atividade já listada realizada com sucesso.")


def excluir_atividade_agendada(driver, wait, tipo_atividade_alvo="Plantio"):
    """
    Localiza a atividade inserida no primeiro passo (Plantio - que possui status 'Agendado')
    e a exclui, aproveitando os dados já existentes para testar o CRUD - Delete.
    """
    wait.until(EC.presence_of_element_located((By.ID, "tbody-atividades")))
    time.sleep(1)

    linhas = driver.find_elements(By.CSS_SELECTOR, "#tbody-atividades tr")

    botao_excluir = None
    for linha in linhas:
        # Garante que é a atividade correta e que possui o botão de exclusão
        if tipo_atividade_alvo not in linha.text:
            continue
        botoes_excluir = inline_botoes = linha.find_elements(By.CSS_SELECTOR, ".row-actions button[title='Excluir Registro']")
        if botoes_excluir:
            botao_excluir = botoes_excluir[0]
            break

    assert botao_excluir is not None, (
        f"Não foi possível localizar a atividade '{tipo_atividade_alvo}' "
        f"com botão de exclusão disponível."
    )

    destacar_elemento(driver, botao_excluir)
    espera_visual()
    botao_excluir.click()
    espera_visual()

    # Aceita o window.confirm() do navegador
    wait.until(EC.alert_is_present())
    alerta = driver.switch_to.alert
    alerta.accept()

    time.sleep(2)
    print(f"[OK] Atividade '{tipo_atividade_alvo}' (Agendada previamente) excluída com sucesso.")


# ============================================================================
# MÓDULO: EVENTOS EXTREMOS (CRUD - Create + Read | sem Update/Delete)
# ============================================================================
def abrir_pagina_eventos(driver, wait):
    driver.get(f"{BASE_URL}/eventos_extremos.html")
    wait.until(EC.presence_of_element_located((By.ID, "btn-novo-evento")))
    time.sleep(2)  # aguarda carregamento das safras via fetch


def cadastrar_evento_extremo(driver, wait, tipo_evento, descricao):
    btn_novo = driver.find_element(By.ID, "btn-novo-evento")
    destacar_elemento(driver, btn_novo)
    btn_novo.click()
    
    wait.until(EC.visibility_of_element_located((By.ID, "modal-evento")))
    espera_visual()

    # Seleciona a primeira safra "Em andamento" disponível
    elem_safra = driver.find_element(By.ID, "id_safra")
    destacar_elemento(driver, elem_safra)
    select_safra = Select(elem_safra)
    opcoes_validas = [o for o in select_safra.options if o.get_attribute("value")]
    assert opcoes_validas, "Nenhuma safra 'Em andamento' disponível para registrar evento extremo."
    select_safra.select_by_value(opcoes_validas[0].get_attribute("value"))
    espera_visual()

    # Tipo do evento
    elem_tipo = driver.find_element(By.ID, "tipo_evento")
    destacar_elemento(driver, elem_tipo)
    select_tipo = Select(elem_tipo)
    select_tipo.select_by_value(tipo_evento)
    espera_visual()

    # Data da ocorrência
    campo_data = driver.find_element(By.ID, "data_ocorrência")
    destacar_elemento(driver, campo_data)
    driver.execute_script("arguments[0].value = arguments[1];", campo_data, "2026-06-10")
    espera_visual()

    # Descrição dos danos
    c_desc = driver.find_element(By.ID, "descricao_danos")
    destacar_elemento(driver, c_desc)
    c_desc.send_keys(descricao)
    espera_visual()

    # Confirma
    btn_submit = driver.find_element(By.ID, "btn-submit")
    destacar_elemento(driver, btn_submit)
    btn_submit.click()

    wait.until(EC.invisibility_of_element_located((By.ID, "modal-evento")))
    time.sleep(2)
    print(f"[OK] Evento extremo '{tipo_evento}' registrado com sucesso.")


def consultar_evento_listado(driver, wait):
    """Consulta o primeiro evento extremo da tabela (Read)."""
    wait.until(EC.presence_of_element_located((By.ID, "tbody-eventos")))
    primeira_linha = driver.find_element(By.CSS_SELECTOR, "#tbody-eventos tr")

    botao_visualizar = primeira_linha.find_element(By.CSS_SELECTOR, "button[onclick^='abrirModalVisualizar']")
    destacar_elemento(driver, botao_visualizar)
    espera_visual()
    botao_visualizar.click()

    wait.until(EC.visibility_of_element_located((By.ID, "modal-visualizar")))
    wait.until(EC.visibility_of_element_located((By.ID, "modal-vis-conteudo")))
    espera_visual()

    btn_fechar = driver.find_element(By.XPATH, "//div[@id='modal-visualizar']//button[contains(., 'Fechar')]")
    destacar_elemento(driver, btn_fechar)
    espera_visual()
    btn_fechar.click()
    
    wait.until(EC.invisibility_of_element_located((By.ID, "modal-visualizar")))
    time.sleep(1)
    print("[OK] Consulta de evento extremo já listado realizada com sucesso.")


def validar_ausencia_edicao_exclusao_evento(driver):
    """Garante que a tabela de eventos extremos não possui botões de editar/excluir."""
    primeira_linha = driver.find_element(By.CSS_SELECTOR, "#tbody-eventos tr")
    destacar_elemento(driver, primeira_linha)
    espera_visual()
    
    botoes = primeira_linha.find_elements(By.TAG_NAME, "button")

    icones_proibidos = ("bi-pencil", "bi-trash")
    for botao in botoes:
        html_botao = botao.get_attribute("innerHTML")
        for icone in icones_proibidos:
            assert icone not in html_botao, (
                f"Encontrado botão de '{icone}' na tabela de Eventos Extremos — "
                f"edição/exclusão não deveria ser permitida."
            )

    print("[OK] Confirmado: Eventos Extremos não permitem edição ou exclusão.")


# ============================================================================
# FLUXO PRINCIPAL
# ============================================================================
def main():
    driver = iniciar_driver()
    wait = WebDriverWait(driver, WAIT_TIMEOUT)

    try:
        # 1. LOGIN
        fazer_login(driver, wait)

        # 2. CADASTRO DE 2 ATIVIDADES (Reduzido para otimizar o fluxo)
        abrir_pagina_atividades(driver, wait)
        # Atividade 1: Plantio (Gera status "Agendado", passível de exclusão futura)
        cadastrar_atividade(driver, wait, tipo_atividade="Plantio", status_atividade="Agendado")

        abrir_pagina_atividades(driver, wait)
        # Atividade 2: Irrigação
        cadastrar_atividade(
            driver, wait,
            tipo_atividade="Irrigação",
            status_atividade="Em andamento",
            lamina_mm="18.4",
            horas_aplicacao="2.5",
        )

        # 3. CONSULTA DE ATIVIDADE JÁ LISTADA
        abrir_pagina_atividades(driver, wait)
        consultar_atividade_listada(driver, wait)

        # 4. EXCLUSÃO DA ATIVIDADE "Agendado" (Usa a atividade 'Plantio' criada no passo 2)
        abrir_pagina_atividades(driver, wait)
        excluir_atividade_agendada(driver, wait, tipo_atividade_alvo="Plantio")

        # 5. CADASTRO DE 3 EVENTOS EXTREMOS
        abrir_pagina_eventos(driver, wait)
        cadastrar_evento_extremo(driver, wait, "Granizo", "Perda estimada de 30% da área foliar devido a granizo.")

        abrir_pagina_eventos(driver, wait)
        cadastrar_evento_extremo(driver, wait, "Seca/Estiagem", "Estresse hídrico severo nas últimas 3 semanas.")

        abrir_pagina_eventos(driver, wait)
        cadastrar_evento_extremo(driver, wait, "Vendaval/Tempestade", "Queda de estruturas e danos em equipamentos de irrigação.")

        # 6. CONSULTA DE EVENTO EXTREMO JÁ LISTADO
        abrir_pagina_eventos(driver, wait)
        consultar_evento_listado(driver, wait)

        # 7. VALIDA AUSÊNCIA DE EDIÇÃO/EXCLUSÃO EM EVENTOS EXTREMOS
        validar_ausencia_edicao_exclusao_evento(driver)

        print("\n=== TODOS OS TESTES FORAM EXECUTADOS COM SUCESSO ===")

    finally:
        time.sleep(5)
        driver.quit()


if __name__ == "__main__":
    main()