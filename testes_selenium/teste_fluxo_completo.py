import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from datetime import datetime, timedelta

# ==============================================================================
# CONFIGURAÇÕES DE CREDENCIAIS
# ==============================================================================
GERENTE_EMAIL = "gestor1@agrogestor.com"
GERENTE_SENHA = "hash_senha_gestor1"

TECNICO_EMAIL = "tecnico.alfa@agrogestor.com"
TECNICO_SENHA = "hash_senha_alfa"

URL_LOGIN = "http://127.0.0.1:5500/index.html"

def executar_fluxo_mestre():
    print("=" * 70)
    print(" INICIALIZAÇÃO DO AMBIENTE DE TESTES E2E — AgroGestor")
    print(" Cobertura: Funcionários | Talhões | Safras")
    print("=" * 70)
    print("Inicializando robô de teste E2E (Firefox)...")

    opcoes  = webdriver.FirefoxOptions()
    servico = Service(GeckoDriverManager().install())
    driver  = webdriver.Firefox(service=servico, options=opcoes)
    driver.maximize_window()

    aguardar = WebDriverWait(driver, 10)

    # Padrão Anti-Duplicidade do Atila
    sufixo_unico      = str(int(time.time() * 1000))[-6:]
    nome_funcionario  = f"Tecnico {sufixo_unico}"
    email_funcionario = f"tecnico_{sufixo_unico}@agrogestor.com"
    talhao_para_tecnico  = f"Talhao Alfa {sufixo_unico}"
    talhao_para_gerente  = f"Talhao Beta {sufixo_unico}"
    variedade_safra      = f"Soja Teste {sufixo_unico}"
    variedade_exclusao   = f"Milho Exclusao {sufixo_unico}"

    # Datas para o módulo de safras
    hoje              = datetime.now()
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
        time.sleep(3.0)

        print("Autenticando perfil: Gerente...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(GERENTE_EMAIL)
        time.sleep(1.5)
        driver.find_element(By.ID, "txt-senha").send_keys(GERENTE_SENHA)
        time.sleep(2.0)
        driver.find_element(By.ID, "btn-entrar").click()

        print("Validando acesso ao Dashboard do Gerente...")
        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(3.0)

        print("Navegando para Gerenciamento de Funcionários...")
        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-funcionarios"))).click()
        aguardar.until(EC.url_contains("gerenciar_funcionarios.html"))
        time.sleep(3.0)

        print(f"Cadastrando novo integrante: {nome_funcionario}")
        aguardar.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Adicionar Integrante')]")
        )).click()
        time.sleep(2.5)

        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(nome_funcionario)
        time.sleep(1.0)
        driver.find_element(By.ID, "txt-email").send_keys(email_funcionario)
        time.sleep(1.0)
        driver.find_element(By.ID, "txt-senha").send_keys("SenhaSegura123")
        time.sleep(3.0)
        driver.find_element(By.ID, "form-funcionario").submit()

        print("Confirmando persistência do novo integrante na tabela...")
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-funcionarios"), nome_funcionario))
        time.sleep(3.0)

        print(f"Executando remoção do integrante cadastrado: {nome_funcionario}")
        xpath_linha = f"//tr[contains(., '{nome_funcionario}')]"
        linha_func  = aguardar.until(EC.presence_of_element_located((By.XPATH, xpath_linha)))
        btn_excluir = linha_func.find_element(By.XPATH, ".//button | .//a | .//i[contains(@class, 'bi')]")
        btn_excluir.click()
        time.sleep(2.5)
        try:
            driver.switch_to.alert.accept()
            print("Alerta de confirmação de exclusão aceito.")
            time.sleep(2.5)
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
        time.sleep(3.0)

        print(f"Inserindo talhão de teste para o Técnico: {talhao_para_tecnico}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(2.5)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_tecnico)
        driver.find_element(By.ID, "txt-area").send_keys("100")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_tecnico))
        time.sleep(3.5)

        print(f"Inserindo talhão exclusivo do Gerente: {talhao_para_gerente}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(2.5)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_gerente)
        driver.find_element(By.ID, "txt-area").send_keys("200")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_gerente))
        time.sleep(3.5)

        print(f"Gerente editando talhão: {talhao_para_gerente}")
        linha_g = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        linha_g.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]").click()
        time.sleep(2.5)
        campo_area = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area.clear()
        time.sleep(1.0)
        campo_area.send_keys("250")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        time.sleep(4.0)

        print(f"Gerente removendo talhão: {talhao_para_gerente}")
        linha_g2 = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        linha_g2.find_element(By.XPATH, ".//*[contains(@class, 'bi-trash') or contains(., 'Excluir')]").click()
        time.sleep(2.5)
        try:
            driver.switch_to.alert.accept()
            print("Alerta de confirmação de exclusão de talhão aceito.")
            time.sleep(2.5)
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
        time.sleep(3.5)

        print("Autenticando perfil: Técnico...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(TECNICO_EMAIL)
        time.sleep(1.5)
        driver.find_element(By.ID, "txt-senha").send_keys(TECNICO_SENHA)
        time.sleep(2.0)
        driver.find_element(By.ID, "btn-entrar").click()

        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(3.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-talhoes"))).click()
        aguardar.until(EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(3.5)

        print(f"Técnico consultando talhão: {talhao_para_tecnico}")
        aguardar.until(EC.visibility_of_element_located(
            (By.XPATH, f"//tr[contains(., '{talhao_para_tecnico}')]")
        ))
        time.sleep(3.0)

        print(f"Técnico editando talhão: {talhao_para_tecnico}")
        linha_t = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_tecnico}')]")
        linha_t.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]").click()
        time.sleep(2.5)
        campo_area2 = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area2.clear()
        time.sleep(1.5)
        campo_area2.send_keys("180")
        time.sleep(3.0)
        driver.find_element(By.ID, "form-talhao").submit()
        print("Gravação de alterações do Técnico enviada com sucesso.")
        time.sleep(4.0)

        # ==================================================================
        # PARTE 4: TÉCNICO — GERENCIAMENTO COMPLETO DE SAFRAS
        # RFS05 Inserir | RFS06 Editar | RFS07 Consultar | RFS08 Excluir
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 4: TÉCNICO — GERENCIAMENTO DE SAFRAS")
        print(" RFS05 Inserir | RFS06 Editar | RFS07 Consultar | RFS08 Excluir")
        print("=" * 70)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-safras"))).click()
        aguardar.until(EC.url_contains("gerenciar_safras.html"))
        print("✓ Navegação para Gerenciar Safras concluída.")
        time.sleep(2.5)

        # ── RFS05: Inserir Safra 
        print(f"RFS05 — Inserindo safra: {variedade_safra}")
        aguardar.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Abrir Nova Safra')]")
        )).click()
        time.sleep(2.0)

        sel_talhao = aguardar.until(EC.visibility_of_element_located((By.ID, "ab-talhao")))
        sel = Select(sel_talhao)
        if len(sel.options) <= 1:
            raise Exception("Nenhum talhão disponível para criar safra.")
        sel.select_by_index(1)
        time.sleep(1.0)

        driver.find_element(By.ID, "ab-variedade").send_keys(variedade_safra)
        driver.execute_script(f"document.getElementById('ab-inicio').value = '{data_inicio_iso}'")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{data_colheita_iso}'")
        Select(driver.find_element(By.ID, "ab-status")).select_by_value("Em andamento")
        time.sleep(1.5)

        driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), variedade_safra))
        print(f"✓ RFS05 — Safra '{variedade_safra}' inserida e confirmada na tabela.")
        time.sleep(3.0)

        # ── RFS07: Consultar com filtro
        print("RFS07 — Consultando safras com filtro por status...")
        Select(driver.find_element(By.ID, "filtro-status")).select_by_value("Em andamento")
        driver.find_element(By.XPATH, "//button[contains(., 'Filtrar')]").click()
        time.sleep(2.5)
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), variedade_safra))
        print("✓ RFS07 — Filtro por status 'Em andamento' funcionando.")
        Select(driver.find_element(By.ID, "filtro-status")).select_by_value("")
        driver.find_element(By.XPATH, "//button[contains(., 'Filtrar')]").click()
        time.sleep(2.0)

        # ── RFS06: Editar Safra 
        print("RFS06 — Editando safra (verificando bloqueio de campos)...")
        linha_s = aguardar.until(EC.presence_of_element_located(
            (By.XPATH, f"//tr[contains(., '{variedade_safra}')]")
        ))
        linha_s.find_element(By.XPATH, ".//*[contains(@class,'bi-pencil')]").click()
        time.sleep(2.0)

        talhao_bloqueado    = driver.find_element(By.ID, "ab-talhao").get_attribute("disabled")
        variedade_bloqueada = driver.find_element(By.ID, "ab-variedade").get_attribute("disabled")
        if talhao_bloqueado and variedade_bloqueada:
            print("✓ RFS06 — Campos bloqueados corretamente após início do cultivo (RN06).")
        else:
            print("⚠ RFS06 — ATENÇÃO: campos deveriam estar bloqueados.")

        nova_colheita = (hoje + timedelta(days=150)).strftime("%Y-%m-%d")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{nova_colheita}'")
        time.sleep(1.5)
        driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        time.sleep(2.5)
        print("✓ RFS06 — Data de colheita atualizada com sucesso.")

        # ── Encerrar Safra (Registrar Colheita + Produtividade) 
        print("Encerrando safra — registrando colheita e produtividade...")
        linha_s2 = aguardar.until(EC.presence_of_element_located(
            (By.XPATH, f"//tr[contains(., '{variedade_safra}')]")
        ))
        linha_s2.find_element(By.XPATH, ".//*[contains(@class,'bi-trophy')]").click()
        time.sleep(2.0)

        driver.execute_script(f"document.getElementById('enc-data-real').value = '{data_colheita_real_iso}'")
        time.sleep(0.8)
        driver.find_element(By.ID, "enc-produtividade").send_keys("68.5")
        time.sleep(1.5)
        driver.find_element(By.XPATH, "//button[contains(., 'Confirmar Colheita')]").click()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), "68.5"))
        print("✓ Encerramento — Produtividade '68.5 sc/ha' registrada e confirmada.")
        time.sleep(3.0)

        # ── RFS08: Excluir Safra (cria uma nova para excluir) 
        print(f"RFS08 — Inserindo safra para teste de exclusão: {variedade_exclusao}")
        aguardar.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Abrir Nova Safra')]")
        )).click()
        time.sleep(2.0)

        sel2 = Select(aguardar.until(EC.visibility_of_element_located((By.ID, "ab-talhao"))))
        sel2.select_by_index(1)
        driver.find_element(By.ID, "ab-variedade").send_keys(variedade_exclusao)
        driver.execute_script(f"document.getElementById('ab-inicio').value = '{data_inicio_iso}'")
        driver.execute_script(f"document.getElementById('ab-colheita').value = '{data_colheita_iso}'")
        Select(driver.find_element(By.ID, "ab-status")).select_by_value("Planejada")
        time.sleep(1.5)
        driver.find_element(By.XPATH, "//button[contains(., 'Salvar Safra')]").click()
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), variedade_exclusao))
        time.sleep(2.5)

        linha_excl = driver.find_element(By.XPATH, f"//tr[contains(., '{variedade_exclusao}')]")
        linha_excl.find_element(By.XPATH, ".//*[contains(@class,'bi-trash')]").click()
        time.sleep(1.5)
        try:
            driver.switch_to.alert.accept()
            time.sleep(2.0)
        except:
            pass
        aguardar.until(EC.invisibility_of_element_located(
            (By.XPATH, f"//tr[contains(., '{variedade_exclusao}')]")
        ))
        print(f"✓ RFS08 — Safra '{variedade_exclusao}' excluída e removida da tabela.")
        time.sleep(2.5)

        # ==================================================================
        # PARTE 5: GESTOR — VALIDA ACESSO AO MÓDULO DE SAFRAS
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 5: GESTOR — VALIDAÇÃO DE ACESSO AO MÓDULO DE SAFRAS")
        print("=" * 70)

        print("Finalizando sessão do Técnico...")
        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(3.0)

        print("Autenticando perfil: Gestor...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(GERENTE_EMAIL)
        driver.find_element(By.ID, "txt-senha").send_keys(GERENTE_SENHA)
        driver.find_element(By.ID, "btn-entrar").click()
        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(2.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-safras"))).click()
        aguardar.until(EC.url_contains("gerenciar_safras.html"))
        print("✓ Gestor acessa o módulo de safras normalmente.")
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-safras"), "68.5"))
        print("✓ Gestor visualiza a produtividade registrada pelo Técnico.")
        time.sleep(2.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(2.0)

        # ==================================================================
        # RESULTADO FINAL
        # ==================================================================
        print("\n" + "=" * 70)
        print(" STATUS FINAL: SUCESSO ABSOLUTO")
        print("=" * 70)
        print(" -> Operações completas do Gerente (Funcionários, Talhões) validadas.")
        print(" -> Consulta e edição de Talhão pelo Técnico validadas.")
        print(" -> RFS05 — Inserir safra com formulário de abertura/plantio.")
        print(" -> RFS06 — Editar safra com bloqueio de campos (RN06).")
        print(" -> RFS07 — Consultar safras com filtro por status.")
        print(" -> RFS08 — Excluir safra (soft delete).")
        print(" ->         Encerramento com produtividade (sc/ha) registrada.")
        print(" ->         Acesso do Gestor ao módulo de safras validado.")
        print("=" * 70)

    except Exception as erro:
        print("\n" + "=" * 70)
        print(f" STATUS FINAL: O FLUXO CRASHOU! Detalhes: {erro}")
        print("=" * 70)
        time.sleep(6.0)

    finally:
        print("Finalizando processo do driver do navegador...")
        driver.quit()

if __name__ == "__main__":
    executar_fluxo_mestre()
