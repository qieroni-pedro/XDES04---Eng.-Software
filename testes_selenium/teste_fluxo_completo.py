import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURAÇÕES DE CREDENCIAIS E AMBIENTE
# ==============================================================================
GERENTE_EMAIL = "gestor1@agrogestor.com"
GERENTE_SENHA = "hash_senha_gestor1"

TECNICO_EMAIL = "tecnico.alfa@agrogestor.com"
TECNICO_SENHA = "hash_senha_alfa"

URL_LOGIN = "http://127.0.0.1:5500/frontend/index.html"

# Controle de cadência visual (em segundos) para desacelerar o robô
CADENCIA_CURTA = 1.0
CADENCIA_MEDIA = 2.0
CADENCIA_LONGA = 3.0

def executar_fluxo_mestre():
    print("=" * 70)
    print(" INICIALIZAÇÃO DO AMBIENTE DE TESTES E2E — AgroGestor")
    print(" Cobertura: Funcionários | Talhões | Safras (Auditoria Atualizada)")
    print("=" * 70)
    print("Inicializando robô de teste E2E (Firefox)...")

    opcoes  = webdriver.FirefoxOptions()
    servico = Service(GeckoDriverManager().install())
    driver  = webdriver.Firefox(service=servico, options=opcoes)
    driver.maximize_window()

    # Tempo máximo global que o Selenium espera os elementos aparecerem no DOM
    aguardar = WebDriverWait(driver, 12)

    # Padrão Anti-Duplicidade
    sufixo_unico      = str(int(time.time() * 1000))[-6:]
    nome_funcionario  = f"Tecnico {sufixo_unico}"
    email_funcionario = f"tecnico_{sufixo_unico}@agrogestor.com"
    talhao_para_tecnico  = f"Talhao Alfa {sufixo_unico}"
    talhao_para_gerente  = f"Talhao Beta {sufixo_unico}"
    variedade_safra      = f"Soja Teste {sufixo_unico}"
    variedade_exclusao   = f"Milho Exclusao {sufixo_unico}"

    # Datas dinâmicas para o módulo de safras
    hoje               = datetime.now()
    data_inicio_iso   = hoje.strftime("%Y-%m-%d")
    data_colheita_iso = (hoje + timedelta(days=120)).strftime("%Y-%m-%d")
    data_colheita_real_iso = (hoje + timedelta(days=5)).strftime("%Y-%m-%d")

    try:
        # ==================================================================
        # PARTE 1: SESSÃO DO GERENTE — AUTENTICAÇÃO E RECURSOS HUMANOS
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 1: SESSÃO DO GERENTE — AUTENTICAÇÃO E RECURSOS HUMANOS")
        print("=" * 70)
        print(f"Acessando tela de login: {URL_LOGIN}")
        driver.get(URL_LOGIN)
        time.sleep(CADENCIA_MEDIA)

        print("Autenticando perfil: Gerente...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(GERENTE_EMAIL)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "txt-senha").send_keys(GERENTE_SENHA)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "btn-entrar").click()

        print("Validando acesso ao Dashboard do Gerente...")
        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(CADENCIA_MEDIA)

        print("Navegando para Gerenciamento de Funcionários...")
        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-funcionarios"))).click()
        aguardar.until(EC.url_contains("gerenciar_funcionarios.html"))
        time.sleep(CADENCIA_MEDIA)

        print(f"Cadastrando novo integrante: {nome_funcionario}")
        aguardar.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Adicionar Integrante')]"))).click()
        time.sleep(CADENCIA_MEDIA)

        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(nome_funcionario)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "txt-email").send_keys(email_funcionario)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "txt-senha").send_keys("SenhaSegura123")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.ID, "form-funcionario").submit()

        print("Confirmando persistência do novo integrante na tabela...")
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-funcionarios"), nome_funcionario))
        time.sleep(CADENCIA_LONGA)

        print(f"Executando remoção do integrante cadastrado: {nome_funcionario}")
        xpath_linha = f"//tr[contains(., '{nome_funcionario}')]"
        linha_func  = aguardar.until(EC.presence_of_element_located((By.XPATH, xpath_linha)))
        btn_excluir = linha_func.find_element(By.XPATH, ".//button | .//a | .//i[contains(@class, 'bi')]")
        btn_excluir.click()
        time.sleep(CADENCIA_MEDIA)
        try:
            driver.switch_to.alert.accept()
            print("Alerta de confirmação de exclusão aceito.")
            time.sleep(CADENCIA_MEDIA)
        except:
            pass

        # ==================================================================
        # PARTE 2: GERENTE — GERENCIAMENTO COMPLETO DE TALHÕES
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 2: SESSÃO DO GERENTE — GERENCIAMENTO COMPLETO DE TALHÕES")
        print("=" * 70)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-talhoes"))).click()
        aguardar.until(EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(CADENCIA_MEDIA)

        print(f"Inserindo talhão de teste para o Técnico: {talhao_para_tecnico}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(CADENCIA_CURTA)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_tecnico)
        driver.find_element(By.ID, "txt-area").send_keys("100")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.ID, "form-talhao").submit()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_tecnico))
        time.sleep(CADENCIA_MEDIA)

        print(f"Inserindo talhão exclusivo do Gerente: {talhao_para_gerente}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(CADENCIA_CURTA)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_gerente)
        driver.find_element(By.ID, "txt-area").send_keys("200")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.ID, "form-talhao").submit()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_gerente))
        time.sleep(CADENCIA_MEDIA)

        print(f"Gerente editando talhão: {talhao_para_gerente}")
        linha_g = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        linha_g.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]").click()
        time.sleep(CADENCIA_MEDIA)
        campo_area = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area.clear()
        time.sleep(CADENCIA_CURTA)
        campo_area.send_keys("250")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.ID, "form-talhao").submit()
        time.sleep(CADENCIA_LONGA)

        print(f"Gerente removendo talhão: {talhao_para_gerente}")
        linha_g2 = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        linha_g2.find_element(By.XPATH, ".//*[contains(@class, 'bi-trash') or contains(., 'Excluir')]").click()
        time.sleep(CADENCIA_MEDIA)
        try:
            driver.switch_to.alert.accept()
            print("Alerta de confirmação de exclusão de talhão aceito.")
            time.sleep(CADENCIA_MEDIA)
        except:
            pass

        # ==================================================================
        # PARTE 3: SESSÃO DO TÉCNICO — CONSULTA E EDIÇÃO DE TALHÃO
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 3: SESSÃO DO TÉCNICO — CONSULTA E EDIÇÃO DE TALHÃO")
        print("=" * 70)

        print("Finalizando sessão do Gerente...")
        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(CADENCIA_MEDIA)

        print("Autenticando perfil: Técnico...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(TECNICO_EMAIL)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "txt-senha").send_keys(TECNICO_SENHA)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "btn-entrar").click()

        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(CADENCIA_MEDIA)
        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-talhoes"))).click()
        aguardar.until(EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(CADENCIA_MEDIA)

        print(f"Técnico consultando talhão: {talhao_para_tecnico}")
        aguardar.until(EC.visibility_of_element_located((By.ID, "tbody-talhoes")))
        time.sleep(CADENCIA_LONGA)

        print(f"Técnico editando talhão: {talhao_para_tecnico}")
        linha_t = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_tecnico}')]")
        linha_t.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]").click()
        time.sleep(CADENCIA_MEDIA)
        campo_area2 = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area2.clear()
        time.sleep(CADENCIA_CURTA)
        campo_area2.send_keys("180")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.ID, "form-talhao").submit()
        print("✓ Alterações do Técnico enviadas.")
        time.sleep(CADENCIA_LONGA)

        # ==================================================================
        # PARTE 4: TÉCNICO — GERENCIAMENTO COMPLETO DE SAFRAS (REVISADO)
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 4: TÉCNICO — GERENCIAMENTO DE SAFRAS (REGRAS DE AUDITORIA)")
        print("=" * 70)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-safras"))).click()
        aguardar.until(EC.url_contains("gerenciar_safras.html"))
        print("✓ Navegação para Gerenciar Safras concluída.")
        time.sleep(CADENCIA_MEDIA)

        # ── TESTE DE FLUXO 1: Criar Safra Diretamente "Em andamento"
        print(f"Nova Regra — Inserindo safra diretamente como 'Em andamento': {variedade_safra}")
        aguardar.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Abrir Nova Safra')]"))).click()
        time.sleep(CADENCIA_MEDIA)

        # Verificação da correção: O campo status DEVE estar habilitado no cadastro de nova safra
        status_novo_disabled = driver.find_element(By.ID, "ab-status").get_attribute("disabled")
        if status_novo_disabled:
            raise Exception("ERRO AUDITORIA: O status não pode vir bloqueado no cadastro de uma nova safra!")
        print("✓ Sucesso: Campo status está destravado para novas safras.")

        sel_talhao = aguardar.until(EC.visibility_of_element_located((By.ID, "ab-talhao")))
        sel = Select(sel_talhao)
        sel.select_by_index(1)
        time.sleep(CADENCIA_CURTA)

        driver.find_element(By.ID, "ab-variedade").send_keys(variedade_safra)
        time.sleep(CADENCIA_CURTA)
        driver.execute_script(f"document.getElementById('ab-inicio').value = '{data_inicio_iso}'")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{data_colheita_iso}'")
        time.sleep(CADENCIA_CURTA)
        
        # Seleciona "Em andamento"
        Select(driver.find_element(By.ID, "ab-status")).select_by_value("Em andamento")
        time.sleep(CADENCIA_MEDIA)
        
        # Resolução robusta para o acionamento do botão Salvar Safra
        try:
            driver.find_element(By.ID, "btn-salvar-safra").click()
        except:
            driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        
        # Correção da variável digitada incorretamente (de variedad_safra para variedade_safra)
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), variedade_safra))
        print("✓ Safra criada em andamento com sucesso.")
        time.sleep(CADENCIA_LONGA)

        # ── RFS06: Testar Bloqueios de Edição em uma safra "Em andamento"
        print("RFS06 — Editando safra 'Em andamento' para validar travas de segurança...")
        linha_s = aguardar.until(EC.presence_of_element_located((By.XPATH, f"//tr[contains(., '{variedade_safra}')]")))
        linha_s.find_element(By.XPATH, ".//*[contains(@class,'bi-pencil')]").click()
        time.sleep(CADENCIA_MEDIA)

        # Agora que está "Em andamento", os dados base e o status DEVEM bloquear
        talhao_bloqueado = driver.find_element(By.ID, "ab-talhao").get_attribute("disabled")
        variedade_bloqueada = driver.find_element(By.ID, "ab-variedade").get_attribute("disabled")
        status_bloqueado = driver.find_element(By.ID, "ab-status").get_attribute("disabled")

        if talhao_bloqueado and variedade_bloqueada and status_bloqueado:
            print("✓ Auditoria Perfeita: Status e dados iniciais congelados para safra em andamento!")
        else:
            raise Exception("FALHA DE AUDITORIA: Campos não foram bloqueados em safra em atividade.")

        # Modifica apenas o permitido (data estimada de colheita)
        nova_colheita = (hoje + timedelta(days=150)).strftime("%Y-%m-%d")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{nova_colheita}'")
        time.sleep(CADENCIA_MEDIA)
        
        try:
            driver.find_element(By.ID, "btn-salvar-safra").click()
        except:
            driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        time.sleep(CADENCIA_LONGA)

        # ── Encerrar Safra via Troféu
        print("Encerrando safra via ferramenta oficial de auditoria (Troféu)...")
        linha_s2 = aguardar.until(EC.presence_of_element_located((By.XPATH, f"//tr[contains(., '{variedade_safra}')]")))
        linha_s2.find_element(By.XPATH, ".//*[contains(@class,'bi-trophy')]").click()
        time.sleep(CADENCIA_MEDIA)

        driver.execute_script(f"document.getElementById('enc-data-real').value = '{data_colheita_real_iso}'")
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "enc-produtividade").send_keys("68.5")
        time.sleep(CADENCIA_MEDIA)
        driver.find_element(By.XPATH, "//button[contains(., 'Confirmar Colheita')]").click()
        
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), "68.5"))
        print("✓ Encerramento auditado e concluído com sucesso.")
        time.sleep(CADENCIA_LONGA)

        # ── Teste de Imutabilidade (Cadeado)
        print("Validando imutabilidade total pós-conclusão...")
        linha_concluida = driver.find_element(By.XPATH, f"//tr[contains(., '{variedade_safra}')]")
        
        # O botão de lápis deve ter sumido e dado lugar ao ícone de cadeado travado
        botoes_edicao_ativos = linha_concluida.find_elements(By.XPATH, ".//button[contains(@onclick, 'abrirModalEdicao')]")
        cadeados_auditoria = linha_concluida.find_elements(By.XPATH, ".//*[contains(@class, 'bi-lock-fill')]")
        
        if len(botoes_edicao_ativos) == 0 and len(cadeados_auditoria) > 0:
            print("✓ Auditoria Perfeita: Botão de edição removido e registro selado com cadeado!")
        else:
            raise Exception("FALHA DE AUDITORIA: O registro concluído ainda permite tentativas de edição externa!")
        time.sleep(CADENCIA_MEDIA)

        # ── RFS08: Testar criação e remoção de safra "Planejada"
        print(f"RFS08 — Cadastrando safra 'Planejada' para teste de exclusão: {variedade_exclusao}")
        driver.find_element(By.XPATH, "//button[contains(., 'Abrir Nova Safra')]").click()
        time.sleep(CADENCIA_MEDIA)

        sel2 = Select(aguardar.until(EC.visibility_of_element_located((By.ID, "ab-talhao"))))
        sel2.select_by_index(1)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "ab-variedade").send_keys(variedade_exclusao)
        time.sleep(CADENCIA_CURTA)
        driver.execute_script(f"document.getElementById('ab-inicio').value = '{data_inicio_iso}'")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{data_colheita_iso}'")
        time.sleep(CADENCIA_CURTA)
        
        # Garante que está como planejada
        Select(driver.find_element(By.ID, "ab-status")).select_by_value("Planejada")
        time.sleep(CADENCIA_MEDIA)
        
        try:
            driver.find_element(By.ID, "btn-salvar-safra").click()
        except:
            driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), variedad_exclusao))
        time.sleep(CADENCIA_LONGA)

        # Executa a exclusão permitida (visto que status é Planejada)
        linha_excl = driver.find_element(By.XPATH, f"//tr[contains(., '{variedade_exclusao}')]")
        linha_excl.find_element(By.XPATH, ".//*[contains(@class,'bi-trash')]").click()
        time.sleep(CADENCIA_MEDIA)
        try:
            driver.switch_to.alert.accept()
            time.sleep(CADENCIA_MEDIA)
        except:
            pass
            
        aguardar.until(EC.invisibility_of_element_located((By.XPATH, f"//tr[contains(., '{variedade_exclusao}')]")))
        print(f"✓ RFS08 — Safra planejada removida com sucesso.")
        time.sleep(CADENCIA_MEDIA)

        # ==================================================================
        # PARTE 5: GESTOR — VALIDA ACESSO AO MÓDULO DE SAFRAS
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 5: GESTOR — VALIDAÇÃO DE ACESSO AO MÓDULO DE SAFRAS")
        print("=" * 70)

        print("Finalizando sessão do Técnico...")
        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(CADENCIA_MEDIA)

        print("Autenticando perfil: Gestor...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(GERENTE_EMAIL)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "txt-senha").send_keys(GERENTE_SENHA)
        time.sleep(CADENCIA_CURTA)
        driver.find_element(By.ID, "btn-entrar").click()
        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(CADENCIA_MEDIA)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-safras"))).click()
        aguardar.until(EC.url_contains("gerenciar_safras.html"))
        print("✓ Gestor acessa o módulo de safras normalmente.")
        time.sleep(CADENCIA_LONGA)
        
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), "68.5"))
        print("✓ Gestor visualiza a produtividade trancada com segurança.")
        time.sleep(CADENCIA_LONGA)

        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(CADENCIA_MEDIA)

        # ==================================================================
        # RESULTADO FINAL
        # ==================================================================
        print("\n" + "=" * 70)
        print(" STATUS FINAL: SUCESSO ABSOLUTO (SISTEMA BLINDADO)")
        print("=" * 70)
        print(" -> Regras de imutabilidade de Auditoria testadas e validadas com sucesso.")
        print("=" * 70)

    except Exception as erro:
        print("\n" + "=" * 70)
        print(f" STATUS FINAL: O FLUXO CRASHOU! Detalhes: {erro}")
        print("=" * 70)
        time.sleep(5.0)

    finally:
        print("Finalizando processo do driver do navegador...")
        driver.quit()

if __name__ == "__main__":
    executar_fluxo_mestre()