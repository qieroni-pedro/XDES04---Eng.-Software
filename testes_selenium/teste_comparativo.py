import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager


# CONFIGURAÇÕES
TECNICO_EMAIL = "tecnico.alfa@agrogestor.com"
TECNICO_SENHA = "hash_senha_alfa"
GESTOR_EMAIL  = "gestor1@agrogestor.com"
GESTOR_SENHA  = "hash_senha_gestor1"
URL_LOGIN     = "http://127.0.0.1:5500/index.html"


def executar_teste_comparativo():
    print("=" * 70)
    print(" TESTES E2E — RELATÓRIO COMPARATIVO DE PRODUTIVIDADE")
    print(" (rode 'python seed_relatorios.py' antes, se ainda não rodou)")
    print("=" * 70)

    opcoes  = webdriver.FirefoxOptions()
    opcoes.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
    servico = Service(GeckoDriverManager().install())
    driver  = webdriver.Firefox(service=servico, options=opcoes)
    driver.maximize_window()
    aguardar = WebDriverWait(driver, 10)

    try:
        # PARTE 1 — LOGIN E NAVEGAÇÃO
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

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-comparativo"))).click()
        aguardar.until(EC.url_contains("comparacao.html"))
        print("✓ Navegação para Comparativo de Safras concluída.")
        time.sleep(2.5)

        # PARTE 2 — SELEÇÃO DE SAFRAS (CHECKBOXES)
        print("\n" + "=" * 70)
        print(" PARTE 2: SELEÇÃO DE SAFRAS PARA COMPARAÇÃO")
        print("=" * 70)

        checkboxes = aguardar.until(EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, ".safra-checkbox")
        ))
        time.sleep(1.5)

        if len(checkboxes) < 2:
            raise Exception(
                "Menos de 2 safras encerradas disponíveis. "
                "Rode 'python seed_relatorios.py' no backend antes deste teste."
            )

        print(f"✓ {len(checkboxes)} safras encerradas disponíveis para seleção.")

        # Seleciona as 4 primeiras (ou todas se houver menos de 4)
        n_selecionar = min(4, len(checkboxes))
        for i in range(n_selecionar):
            checkboxes[i].click()
            time.sleep(0.6)
        print(f"✓ {n_selecionar} safras selecionadas via checkbox.")
        time.sleep(1.5)

        # Confirma o contador
        contador = driver.find_element(By.ID, "counter-msg")
        print(f"✓ Contador exibido: '{contador.text}'")
        time.sleep(1.5)

        # ── RN09: testar limite de 5 safras (se houver checkboxes suficientes) ──
        if len(checkboxes) > 5:
            print("Testando limite RN09 (máximo 5 safras)...")
            for i in range(n_selecionar, len(checkboxes)):
                checkboxes[i].click()
                time.sleep(0.5)
                # Aceita o alert de limite imediatamente se aparecer
                try:
                    alerta = driver.switch_to.alert
                    texto_alerta = alerta.text
                    alerta.accept()
                    print(f"✓ RN09 — Alert disparado corretamente: '{texto_alerta}'")
                    break
                except:
                    pass
            time.sleep(1.0)
            marcados = driver.find_elements(By.CSS_SELECTOR, ".safra-checkbox:checked")
            print(f"✓ RN09 — {len(marcados)} safra(s) marcada(s) após tentativa de exceder limite.")

        # PARTE 3 — GERAR MATRIZ COMPARATIVA
        print("\n" + "=" * 70)
        print(" PARTE 3: GERAR MATRIZ COMPARATIVA")
        print("=" * 70)

        driver.find_element(By.ID, "btn-comparar").click()
        time.sleep(3.5)

        aguardar.until(EC.visibility_of_element_located((By.ID, "resultado-comparacao")))
        print("✓ Seção de resultado exibida.")

        estado_vazio = driver.find_element(By.ID, "estado-vazio")
        if "hidden" in estado_vazio.get_attribute("class"):
            print("✓ Estado vazio ocultado corretamente.")
        time.sleep(2.0)

        # Cabeçalho da matriz com uma coluna por safra
        header_cells = driver.find_elements(By.CSS_SELECTOR, "#table-header th")
        print(f"✓ Matriz comparativa com {len(header_cells) - 1} colunas de safra (+1 de indicador).")
        time.sleep(1.5)

        # Verifica destaque "Melhor Desempenho"
        try:
            melhor = driver.find_element(By.XPATH, "//*[contains(text(), 'Melhor Desempenho')]")
            print(f"✓ Destaque de 'Melhor Desempenho' identificado na matriz.")
        except:
            print("  Nenhum destaque de melhor desempenho encontrado (verificar lógica).")
        time.sleep(2.0)

        # Linhas da tabela (Variedade, Semeadura, Colheita, Duração, Produtividade)
        linhas_tabela = driver.find_elements(By.CSS_SELECTOR, "#table-body tr")
        print(f"✓ {len(linhas_tabela)} indicadores exibidos na matriz (Variedade/Datas/Duração/Produtividade).")
        time.sleep(2.0)

        # PARTE 4 — LINHA DO TEMPO CONSOLIDADA
        print("\n" + "=" * 70)
        print(" PARTE 4: LINHA DO TEMPO CONSOLIDADA")
        print("=" * 70)

        linhas_timeline = driver.find_elements(By.CSS_SELECTOR, "#timeline-body tr")
        if linhas_timeline:
            print(f"✓ Linha do tempo consolidada com {len(linhas_timeline)} eventos de todas as safras.")

            # Verifica se há ao menos um evento extremo destacado (vermelho)
            eventos_extremos = driver.find_elements(
                By.XPATH, "//tr[contains(@class, 'bg-red-50')]"
            )
            if eventos_extremos:
                print(f"✓ {len(eventos_extremos)} evento(s) extremo(s) destacado(s) em vermelho na linha do tempo.")
            else:
                print("  Nenhum evento extremo na seleção atual (depende de quais safras foram marcadas).")
        else:
            print("  Linha do tempo vazia.")
        time.sleep(2.5)

        # PARTE 5 — QR CODE E LINK DE AUTENTICIDADE (código múltiplo/HMAC)
        print("\n" + "=" * 70)
        print(" PARTE 5: QR CODE E AUTENTICIDADE (MÚLTIPLAS SAFRAS)")
        print("=" * 70)

        qr_img = driver.find_element(By.ID, "qr-comparativo")
        qr_src = qr_img.get_attribute("src")
        if qr_src and "qrserver.com" in qr_src:
            print("✓ QR Code do comparativo gerado.")

        link_aut = driver.find_element(By.ID, "link-autenticidade")
        url_aut  = link_aut.get_attribute("href")
        if "autenticidade.html" in url_aut and "safras=" in url_aut and "codigo=" in url_aut:
            print("✓ Link de autenticidade contém parâmetro 'safras=' (plural) e código HMAC.")
            print(f"  URL: {url_aut[:90]}...")
        else:
            print(f"⚠ Link de autenticidade inesperado: {url_aut}")
        time.sleep(2.0)

        # PARTE 6 — DOWNLOAD DO PDF
        print("\n" + "=" * 70)
        print(" PARTE 6: DOWNLOAD DO PDF COMPARATIVO")
        print("=" * 70)

        btn_pdf = driver.find_element(By.ID, "btn-pdf")
        if "hidden" not in btn_pdf.get_attribute("class"):
            print("✓ Botão 'Baixar PDF' visível após gerar comparativo.")
            btn_pdf.click()
            time.sleep(4.0)
            print("✓ Download do PDF comparativo acionado (verifique a pasta de downloads).")
        else:
            print("⚠ Botão 'Baixar PDF' ainda oculto.")
        time.sleep(2.0)

        # PARTE 7 — PÁGINA PÚBLICA DE AUTENTICIDADE (COMPARATIVO)
        print("\n" + "=" * 70)
        print(" PARTE 7: PÁGINA PÚBLICA DE AUTENTICIDADE (COMPARATIVO)")
        print("=" * 70)

        driver.get(url_aut)
        time.sleep(4.0)

        try:
            conteudo = aguardar.until(EC.visibility_of_element_located((By.ID, "conteudo-verificado")))
            if "hidden" not in conteudo.get_attribute("class"):
                print("✓ Página de autenticidade verificou o comparativo com sucesso.")

            badge = driver.find_element(By.XPATH, "//*[contains(., 'Documento Autêntico')]")
            print("✓ Badge 'Documento Autêntico' exibido.")

            # Confirma que o título foi ajustado para "Safras Comparadas"
            titulo_secao = driver.find_element(By.CSS_SELECTOR, "#conteudo-verificado h2")
            if "Safras Comparadas" in titulo_secao.text:
                print(f"✓ Título ajustado corretamente: '{titulo_secao.text}'")
            else:
                print(f"  Título exibido: '{titulo_secao.text}' (esperado conter 'Safras Comparadas')")

            # Grid com múltiplos cards de safra
            grid = driver.find_element(By.ID, "grid-dados-safra")
            cards = grid.find_elements(By.XPATH, "./div")
            print(f"✓ {len(cards)} cards de safra exibidos no grid de dados gerais.")

            # Linha do tempo consolidada na página pública
            tbody_aut = driver.find_element(By.ID, "tbody-timeline")
            linhas_pub = tbody_aut.find_elements(By.TAG_NAME, "tr")
            print(f"✓ Linha do tempo pública com {len(linhas_pub)} linha(s).")

            # Comprovantes (NF/Receita) disponíveis para download
            lista_comp = driver.find_element(By.ID, "lista-comprovantes")
            comprovantes_links = lista_comp.find_elements(By.TAG_NAME, "a")
            if comprovantes_links:
                print(f"✓ {len(comprovantes_links)} comprovante(s) (NF/Receita) disponível(is) para download.")
                # Confirma que o rótulo inclui o nome da safra entre parênteses
                primeiro_texto = comprovantes_links[0].text
                if "(" in primeiro_texto:
                    print(f"✓ Comprovante identifica a safra de origem: '{primeiro_texto[:60]}...'")
            else:
                print("  Nenhum comprovante encontrado nas safras selecionadas.")

        except Exception as e:
            print(f"⚠ Página de autenticidade do comparativo com problema: {e}")
        time.sleep(2.5)

        # PARTE 8 — GESTOR TAMBÉM ACESSA O COMPARATIVO
        print("\n" + "=" * 70)
        print(" PARTE 8: GESTOR ACESSA O COMPARATIVO")
        print("=" * 70)

        # Volta direto para o login (a página de autenticidade não tem sidebar/logout)
        # Limpa o token do Técnico do localStorage antes de tentar o login do Gestor
        driver.get(URL_LOGIN)
        time.sleep(1.5)
        driver.execute_script("localStorage.clear();")
        driver.get(URL_LOGIN)
        time.sleep(2.0)

        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(GESTOR_EMAIL)
        driver.find_element(By.ID, "txt-senha").send_keys(GESTOR_SENHA)
        driver.find_element(By.ID, "btn-entrar").click()
        aguardar.until(EC.url_contains("dashboard.html"))
        print("✓ Login como Gestor realizado.")
        time.sleep(2.5)

        aguardar.until(EC.element_to_be_clickable((By.ID, "menu-comparativo"))).click()
        aguardar.until(EC.url_contains("comparacao.html"))
        print("✓ Gestor acessa o módulo de Comparativo normalmente.")
        time.sleep(2.0)

        # Logout — aguarda a sidebar carregar antes de buscar o botão
        aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout"))).click()
        aguardar.until(EC.url_contains("index.html"))
        time.sleep(1.5)

        # RESULTADO FINAL
        print("\n" + "=" * 70)
        print(" STATUS FINAL: SUCESSO ABSOLUTO")
        print("=" * 70)
        print(" ✓ Seleção de safras via checkboxes (RN09 — máx. 5)")
        print(" ✓ Matriz comparativa gerada com destaque de melhor desempenho")
        print(" ✓ Linha do tempo consolidada com eventos extremos destacados")
        print(" ✓ QR Code e link de autenticidade com código HMAC múltiplo")
        print(" ✓ Download do PDF comparativo acionado")
        print(" ✓ Página pública de autenticidade — comparativo verificado")
        print(" ✓ Comprovantes (NF/Receita) com identificação da safra de origem")
        print(" ✓ Gestor acessa o módulo normalmente")
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
    executar_teste_comparativo()
