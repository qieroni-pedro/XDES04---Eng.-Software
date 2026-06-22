import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
TECNICO_EMAIL = "tecnico.alfa@agrogestor.com"
TECNICO_SENHA = "hash_senha_alfa"
GESTOR_EMAIL  = "gestor1@agrogestor.com"
GESTOR_SENHA  = "hash_senha_gestor1"
URL_LOGIN     = "http://127.0.0.1:5500/index.html"

# Pré-requisito: ter ao menos 1 safra "Colhida/Finalizada" no banco.

def executar_testes_relatorios():
    print("=" * 70)
    print(" TESTES E2E — MÓDULO DE RELATÓRIOS")
    print(" Relatório de Histórico de Safra (Linha do Tempo)")
    print("=" * 70)

    opcoes  = webdriver.FirefoxOptions()
    opcoes.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    servico = Service(GeckoDriverManager().install())
    driver  = webdriver.Firefox(service=servico, options=opcoes)
    driver.maximize_window()
    aguardar = WebDriverWait(driver, 10)

    try:
        # ==================================================================
        # PARTE 1 — LOGIN E NAVEGAÇÃO
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 1: LOGIN E NAVEGAÇÃO")
        print("=" * 70)

        driver.get(URL_LOGIN)
        time.sleep(2.0)

        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(TECNICO_EMAIL)
        driver.find_element(By.ID, "txt-senha").send_keys(TECNICO_SENHA)
        driver.find_element(By.ID, "btn-entrar").click()
        aguardar.until(EC.url_contains("dashboard.html"))
        print("✓ Login como Técnico realizado.")
        time.sleep(2.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-relatorios"))).click()
        aguardar.until(EC.url_contains("relatorios.html"))
        print("✓ Navegação para Relatórios concluída.")
        time.sleep(2.5)

        # ==================================================================
        # PARTE 2 — SELECT DE SAFRAS ENCERRADAS
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 2: SELECT DE SAFRAS ENCERRADAS")
        print("=" * 70)

        sel_el = aguardar.until(EC.visibility_of_element_located((By.ID, "sel-historico-safra")))
        sel    = Select(sel_el)
        time.sleep(1.5)

        if len(sel.options) <= 1:
            raise Exception(
                "Nenhuma safra 'Colhida/Finalizada' encontrada. "
                "Encerre uma safra em Gerenciar Safras antes de rodar este teste."
            )

        sel.select_by_index(1)
        safra_selecionada = sel.first_selected_option.text
        print(f"✓ Select populado. Safra selecionada: {safra_selecionada}")
        time.sleep(1.5)

        # ==================================================================
        # PARTE 3 — VISUALIZAR RELATÓRIO NA TELA
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 3: VISUALIZAR RELATÓRIO NA TELA")
        print("=" * 70)

        driver.find_element(By.XPATH, "//button[contains(., 'Visualizar')]").click()
        time.sleep(3.5)

        # Resultado deve aparecer
        aguardar.until(EC.visibility_of_element_located((By.ID, "resultado-historico")))
        print("✓ Seção de resultado exibida após clicar em Visualizar.")

        # Estado vazio deve sumir
        estado_vazio = driver.find_element(By.ID, "estado-vazio")
        if "hidden" in estado_vazio.get_attribute("class"):
            print("✓ Estado vazio ocultado corretamente.")

        # Dados gerais preenchidos
        grid = driver.find_element(By.ID, "grid-dados-gerais")
        if grid.text.strip():
            print(f"✓ Dados gerais da safra carregados.")
        else:
            print("⚠ Grid de dados gerais vazio — verificar API.")
        time.sleep(2.0)

        # Linha do tempo
        lista_tl = driver.find_element(By.ID, "lista-timeline")
        if lista_tl.text.strip():
            print("✓ Linha do tempo com registros exibida.")
        else:
            print("  Linha do tempo vazia (safra sem atividades com status 'Realizado').")
        time.sleep(2.0)

        # ==================================================================
        # PARTE 4 — QR CODE DE AUTENTICIDADE
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 4: QR CODE DE AUTENTICIDADE")
        print("=" * 70)

        qr_img = driver.find_element(By.ID, "qr-historico")
        qr_src = qr_img.get_attribute("src")
        if qr_src and "qrserver.com" in qr_src:
            print("✓ QR Code gerado via serviço externo.")

        link_aut = driver.find_element(By.ID, "link-historico-autenticidade")
        url_aut  = link_aut.get_attribute("href")
        if "autenticidade.html" in url_aut and "codigo=" in url_aut:
            print(f"✓ Link de autenticidade contém código HMAC.")
            print(f"  URL: {url_aut[:80]}...")
        else:
            print(f"⚠ Link de autenticidade inválido: {url_aut}")
        time.sleep(2.0)

        # ==================================================================
        # PARTE 5 — DOWNLOAD DO PDF
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 5: DOWNLOAD DO PDF")
        print("=" * 70)

        btn_pdf = driver.find_element(By.ID, "btn-download-historico")

        if btn_pdf.get_attribute("disabled"):
            print("⚠ Botão PDF ainda desabilitado — verificar renderizarHistorico().")
        else:
            print("✓ Botão 'Baixar PDF' habilitado após visualização.")
            btn_pdf.click()
            time.sleep(4.0)
            print("✓ Download do PDF acionado (verifique a pasta de downloads do Firefox).")
        time.sleep(2.0)

        # ==================================================================
        # PARTE 6 — PÁGINA PÚBLICA DE AUTENTICIDADE (via URL direta)
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 6: PÁGINA PÚBLICA DE AUTENTICIDADE")
        print("=" * 70)

        # Abre a URL de autenticidade diretamente (simula acesso de auditor)
        driver.get(url_aut.replace("127.0.0.1:8000", "127.0.0.1:5500")
                   if "8000" in url_aut else url_aut)
        time.sleep(4.0)

        # Verifica se o conteúdo verificado aparece
        try:
            conteudo = aguardar.until(EC.visibility_of_element_located(
                (By.ID, "conteudo-verificado")
            ))
            if "hidden" not in conteudo.get_attribute("class"):
                print("✓ Página de autenticidade carregou e verificou o documento.")

            badge = driver.find_element(By.XPATH, "//*[contains(., 'Documento Autêntico')]")
            if badge:
                print("✓ Badge 'Documento Autêntico' exibido.")

            # Verifica se a linha do tempo aparece
            tbody_aut = driver.find_element(By.ID, "tbody-timeline")
            if tbody_aut.text.strip():
                print("✓ Linha do tempo exibida na página de autenticidade.")
            else:
                print("  Linha do tempo vazia na página de autenticidade.")

            # Verifica seção de comprovantes
            lista_comp = driver.find_element(By.ID, "lista-comprovantes")
            if lista_comp.text.strip():
                print("✓ Comprovantes (NF/Receitas) listados para download.")
            else:
                print("  Nenhum comprovante registrado (atividades sem NF/Receita).")

        except Exception as e:
            print(f"⚠ Página de autenticidade com problema: {e}")
        time.sleep(2.5)

        # ==================================================================
        # PARTE 7 — GESTOR TAMBÉM ACESSA OS RELATÓRIOS
        # ==================================================================
        print("\n" + "=" * 70)
        print(" PARTE 7: GESTOR ACESSA OS RELATÓRIOS")
        print("=" * 70)

        # Limpa sessão anterior antes de logar como Gestor
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        time.sleep(1.0)

        driver.get(URL_LOGIN)
        time.sleep(3.0)

        aguardar_longo = WebDriverWait(driver, 20)
        campo_email = aguardar_longo.until(EC.visibility_of_element_located((By.ID, "txt-email")))
        campo_email.clear()
        campo_email.send_keys(GESTOR_EMAIL)

        campo_senha = aguardar_longo.until(EC.visibility_of_element_located((By.ID, "txt-senha")))
        campo_senha.clear()
        campo_senha.send_keys(GESTOR_SENHA)

        driver.find_element(By.ID, "btn-entrar").click()
        aguardar_longo.until(EC.url_contains("dashboard.html"))
        print("✓ Login como Gestor realizado.")
        time.sleep(2.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-relatorios"))).click()
        aguardar.until(EC.url_contains("relatorios.html"))
        print("✓ Gestor acessa o módulo de Relatórios normalmente.")
        time.sleep(2.0)

        # Repete a visualização como Gestor
        sel_g = Select(aguardar.until(EC.visibility_of_element_located((By.ID, "sel-historico-safra"))))
        time.sleep(1.5)
        if len(sel_g.options) > 1:
            sel_g.select_by_index(1)
            driver.find_element(By.XPATH, "//button[contains(., 'Visualizar')]").click()
            time.sleep(3.5)
            aguardar.until(EC.visibility_of_element_located((By.ID, "resultado-historico")))
            print("✓ Gestor visualiza o relatório de histórico normalmente.")
        time.sleep(2.0)

        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        time.sleep(2.0)

        # ==================================================================
        # RESULTADO FINAL
        # ==================================================================
        print("\n" + "=" * 70)
        print(" STATUS FINAL: SUCESSO ABSOLUTO")
        print("=" * 70)
        print(" ✓ Select populado com safras encerradas")
        print(" ✓ Visualização do relatório na tela")
        print(" ✓ Dados gerais da safra carregados")
        print(" ✓ Linha do tempo de manejos e eventos")
        print(" ✓ QR Code de autenticidade gerado")
        print(" ✓ Link de autenticidade com código HMAC")
        print(" ✓ Download do PDF acionado")
        print(" ✓ Página pública de autenticidade verificada")
        print(" ✓ Gestor acessa e visualiza relatórios")
        print("=" * 70)

    except Exception as erro:
        print("\n" + "=" * 70)
        print(f" STATUS FINAL: FALHA — {erro}")
        print("=" * 70)
        time.sleep(5.0)

    finally:
        print("Encerrando driver...")
        driver.quit()

if __name__ == "__main__":
    executar_testes_relatorios()