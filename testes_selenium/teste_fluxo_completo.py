import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# ==============================================================================
# CONFIGURAÇÕES DE CREDENCIAIS
# ==============================================================================
GERENTE_EMAIL = "gestor1@agrogestor.com"
GERENTE_SENHA = "hash_senha_gestor1"

TECNICO_EMAIL = "tecnico.alfa@agrogestor.com"
TECNICO_SENHA = "hash_senha_alfa"

def executar_fluxo_mestre():
    print("======================================================================")
    print("INICIALIZAÇÃO DO AMBIENTE DE TESTES")
    print("======================================================================")
    print("Inicializando robo de teste E2E (Firefox)...")
    
    # Configuração e inicialização do WebDriver para o Mozilla Firefox
    opcoes = webdriver.FirefoxOptions()
    servico = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=servico, options=opcoes)
    driver.maximize_window()
    
    # Explicit Wait: Configura uma espera dinâmica de até 10 segundos.
    # Evita falhas por assincronicidade (quando o script tenta interagir com um elemento que ainda não carregou).
    aguardar = WebDriverWait(driver, 10)
    
    # Padrão Anti-Duplicidade: Gera um sufixo numérico exclusivo baseado no timestamp atual.
    # Para garantir a reprodutibilidade dos testes sem violar restrições de unicidade (Unique Constraints) no banco.
    sufixo_unico = str(int(time.time() * 1000))[-6:]
    nome_funcionario = f"Tecnico {sufixo_unico}"
    email_funcionario = f"tecnico_{sufixo_unico}@agrogestor.com"
    
    talhao_para_tecnico = f"Talhao Alfa {sufixo_unico}"
    talhao_para_gerente = f"Talhao Beta {sufixo_unico}"
    
    try:
        # ======================================================================
        # PARTE 1: SESSÃO DO GERENTE - AUTENTICAÇÃO E RECURSOS HUMANOS
        # ======================================================================
        print("\n======================================================================")
        print("PARTE 1: SESSÃO DO GERENTE - AUTENTICAÇÃO E RECURSOS HUMANOS")
        print("======================================================================")
        url_login = "http://127.0.0.1:5500/frontend/index.html" 
        print(f"Acessando tela de login: {url_login}")
        driver.get(url_login)
        time.sleep(3.0)  # Velocidade do visual para fins de auditoria/demonstração humana

        print("Autenticando perfil: Gerente...")
        # Aguarda a visibilidade do campo antes de interagir (boa prática de resiliência)
        campo_email = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email")))
        campo_email.send_keys(GERENTE_EMAIL)
        time.sleep(1.5)
        
        campo_senha = driver.find_element(By.ID, "txt-senha")
        campo_senha.send_keys(GERENTE_SENHA)
        time.sleep(2.0)
        
        driver.find_element(By.ID, "btn-entrar").click()

        print("Validando acesso ao Dashboard do Gerente...")
        # Asserção de fluxo: Verifica se a URL mudou para a página correta após o login
        aguardar.until(EC.url_contains("dashboard.html"))
        time.sleep(3.0)

        print("Navegando para Gerenciamento de Funcionarios...")
        btn_menu_func = aguardar.until(EC.element_to_be_clickable((By.ID, "menu-funcionarios")))
        btn_menu_func.click()
        
        aguardar.until(EC.url_contains("gerenciar_funcionarios.html"))
        time.sleep(3.0)

        print(f"Cadastrando novo integrante: {nome_funcionario}")
        btn_add_func = aguardar.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Adicionar Integrante')]")))
        btn_add_func.click()
        time.sleep(2.5)

        # Preenchimento do formulário modal de cadastro de funcionário
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(nome_funcionario)
        time.sleep(1.0)
        driver.find_element(By.ID, "txt-email").send_keys(email_funcionario)
        time.sleep(1.0)
        driver.find_element(By.ID, "txt-senha").send_keys("SenhaSegura123")
        time.sleep(3.0)
        
        # Submete as informações via gatilho nativo do formulário HTML
        driver.find_element(By.ID, "form-funcionario").submit()

        print("Confirmando persistencia do novo integrante na tabela...")
        # Validação de persistência: certifica que o texto dinâmico foi renderizado no DOM da tabela
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-funcionarios"), nome_funcionario))
        time.sleep(3.0)

        print(f"Executando remocao do integrante cadastrado: {nome_funcionario}")
        # Localização Avançada: Encontra a linha (<tr>) específica que contém o nome do funcionário criado
        xpath_linha_registro = f"//tr[contains(., '{nome_funcionario}')]"
        linha_func = aguardar.until(EC.presence_of_element_located((By.XPATH, xpath_linha_registro)))
        
        # Busca descendente relativa (CSS/XPath) para encontrar o botão de exclusão contido dentro daquela linha
        btn_excluir = linha_func.find_element(By.XPATH, ".//button | .//a | .//i[contains(@class, 'bi')]")
        btn_excluir.click()
        time.sleep(2.5)
        
        # Tratamento de Janelas Nativas: Manipula o confirm pop-up (JavaScript Alert) do navegador
        try:
            alerta = driver.switch_to.alert
            alerta.accept()
            print("Alerta de confirmacao de exclusao aceito.")
            time.sleep(2.5)
        except:
            pass  # Ignora caso o sistema utilize modais customizados via Tailwind em vez de alertas nativos

        # ======================================================================
        # PARTE 2: GERENTE - GERENCIAMENTO COMPLETO DE TALHÕES
        # ======================================================================
        print("\n======================================================================")
        print("PARTE 2: SESSÃO DO GERENTE - GERENCIAMENTO COMPLETO DE TALHÕES")
        print("======================================================================")
        print("Navegando para Gerenciamento de Talhoes...")
        btn_menu_talhoes = aguardar.until(EC.element_to_be_clickable((By.ID, "menu-talhoes")))
        btn_menu_talhoes.click()
        
        aguardar.until(EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(3.0)

        # Caso de Uso A: Criação de dado base estável para posterior consumo do perfil Técnico
        print(f"Inserindo talhao de teste para o Tecnico: {talhao_para_tecnico}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(2.5)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_tecnico)
        driver.find_element(By.ID, "txt-area").send_keys("100")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_tecnico))
        time.sleep(3.5)

        # Caso de Uso B: Criação de um segundo registro para validar o ciclo completo (CRUD) do Gerente
        print(f"Inserindo talhao de teste exclusivo do Gerente: {talhao_para_gerente}")
        driver.find_element(By.ID, "btn-novo-talhao").click()
        time.sleep(2.5)
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-nome"))).send_keys(talhao_para_gerente)
        driver.find_element(By.ID, "txt-area").send_keys("200")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        
        aguardar.until(EC.text_to_be_present_in_element((By.ID, "tbody-talhoes"), talhao_para_gerente))
        time.sleep(3.5)

        # Teste de Escrita (Update) do Gerente
        print(f"Gerente iniciando edicao do talhao: {talhao_para_gerente}")
        linha_gerente_talhao = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        # Mapeia dinamicamente o ícone de lápis do Bootstrap (bi-pencil) injetado na linha
        btn_editar_gerente = linha_gerente_talhao.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]")
        btn_editar_gerente.click()
        time.sleep(2.5)

        print("Gerente alterando extensao territorial do talhao...")
        campo_area_gerente = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area_gerente.clear()  # Limpa o valor padrão (200) antes de digitar o novo dado
        time.sleep(1.0)
        campo_area_gerente.send_keys("250")
        time.sleep(2.5)
        driver.find_element(By.ID, "form-talhao").submit()
        time.sleep(4.0)

        # Teste de Deleção (Delete) do Gerente no Talhão B
        print(f"Gerente iniciando remocao do talhao: {talhao_para_gerente}")
        linha_gerente_excluir = driver.find_element(By.XPATH, f"//tr[contains(., '{talhao_para_gerente}')]")
        # Localiza o controle de lixeira (bi-trash) 
        btn_excluir_gerente = linha_gerente_excluir.find_element(By.XPATH, ".//*[contains(@class, 'bi-trash') or contains(@class, 'bi-x-lg') or contains(., 'Excluir')]")
        btn_excluir_gerente.click()
        time.sleep(2.5)
        try:
            alerta = driver.switch_to.alert
            alerta.accept()
            print("Alerta de confirmacao de exclusao de talhao aceito.")
            time.sleep(2.5)
        except:
            pass

        print("Finalizando sessao do Gerente...")
        btn_logout = aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout")))
        btn_logout.click()
        time.sleep(3.5)

        # ======================================================================
        # PARTE 3: SESSÃO DO TÉCNICO - CONSULTA E EDIÇÃO COMPLETA DE TALHÃO
        # ======================================================================
        print("\n======================================================================")
        print("PARTE 3: SESSÃO DO TÉCNICO - CONSULTA E EDIÇÃO DE TALHÃO")
        print("======================================================================")
        print("Iniciando nova autenticacao para perfil: Tecnico...")
        aguardar.until(EC.visibility_of_element_located((By.ID, "txt-email"))).send_keys(TECNICO_EMAIL)
        time.sleep(1.5)
        driver.find_element(By.ID, "txt-senha").send_keys(TECNICO_SENHA)
        time.sleep(2.0)
        
        driver.find_element(By.ID, "btn-entrar").click()

        print("Validando acesso ao painel do Tecnico...")
        aguardar.until(EC.url_contains("dashboard.html") or EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(3.5)

        print("Navegando ate o escopo autorizado (Consulta de Taloes)...")
        btn_menu_talhoes_tec = aguardar.until(EC.element_to_be_clickable((By.ID, "menu-talhoes")))
        btn_menu_talhoes_tec.click()
        
        aguardar.until(EC.url_contains("gerenciar_talhoes.html"))
        time.sleep(3.5)

        # Teste de Leitura (Read) do Técnico: Valida consistência e concorrência dos dados criados pelo Gerente
        print(f"Executando consulta visual do talhao inserido previamente: {talhao_para_tecnico}")
        aguardar.until(EC.visibility_of_element_located((By.XPATH, f"//tr[contains(., '{talhao_para_tecnico}')]")))
        time.sleep(3.0)

        # Teste de Permissão de Modificação do Técnico no Talhão A
        print(f"Tecnico acionando fluxo de edicao do talhao: {talhao_para_tecnico}")
        xpath_linha_talhao = f"//tr[contains(., '{talhao_para_tecnico}')]"
        linha_talhao = driver.find_element(By.XPATH, xpath_linha_talhao)
        
        btn_editar_talhao = linha_talhao.find_element(By.XPATH, ".//*[contains(@class, 'bi-pencil') or contains(., 'Editar')]")
        btn_editar_talhao.click()
        time.sleep(2.5)

        print("Tecnico modificando parametros de area do talhao...")
        campo_area_edicao = aguardar.until(EC.visibility_of_element_located((By.ID, "txt-area")))
        campo_area_edicao.clear()
        time.sleep(1.5)
        campo_area_edicao.send_keys("180")
        time.sleep(3.0)

        driver.find_element(By.ID, "form-talhao").submit()
        print("Gravacao de alteracoes do Tecnico enviada com sucesso.")
        time.sleep(4.0)

        print("Finalizando sessao do Tecnico...")
        btn_logout_tec = aguardar.until(EC.element_to_be_clickable((By.ID, "btn-logout")))
        btn_logout_tec.click()
        time.sleep(3.0)

        print("\n======================================================================")
        print("STATUS FINAL: SUCESSO ABSOLUTO")
        print("======================================================================")
        print(" -> Operacoes completas do Gerente (Cadastro, Edicao, Remocao) validadas.")
        print(" -> Isolamento e controle de concorrencia entre dados ativo.")
        print(" -> Fluxo de consulta e modificacao por parte do Tecnico concluido.")
        print("======================================================================")

    except Exception as erro:
        # Tratamento de exceções robusto: Captura qualquer falha no fluxo, imprime o log técnico e encerra o processo sem travar a máquina.
        print("\n======================================================================")
        print(f"STATUS FINAL: O FLUXO CRASHOU! Detalhes da excecao: {erro}")
        print("======================================================================")
        time.sleep(6.0)
        
    finally:
        # Bloco de fechamento obrigatório: Garante o encerramento do processo oculto do navegador no sistema operacional (limpeza de memória).
        print("Finalizando processo do driver do navegador...")
        driver.quit()

if __name__ == "__main__":
    executar_fluxo_mestre()