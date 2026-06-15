const API_URL = "http://localhost:8000";

document.getElementById('form-login').addEventListener('submit', async (event) => {
    event.preventDefault();

    const email = document.getElementById('txt-email').value;
    const senha = document.getElementById('txt-senha').value;
    const btnTexto = document.getElementById('btn-texto');
    const btnEntrar = document.getElementById('btn-entrar');
    const alertErro = document.getElementById('alert-erro');
    const alertMensagem = document.getElementById('alert-mensagem');

    alertErro.classList.add('hidden');
    btnTexto.textContent = "Autenticando...";
    btnEntrar.disabled = true;
    btnEntrar.classList.add('opacity-75', 'cursor-wait');

    try {
        const response = await fetch(`${API_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email,
                password: senha
            })
        });

        const dados = await response.json();

        if (response.ok) {
            // Mapeando os campos do objeto de resposta unificado
            localStorage.setItem('agro_token', dados.access_token);
            localStorage.setItem('user_nome', dados.nome);
            localStorage.setItem('user_perfil', dados.perfil_global); 
            
            // Grava o array de fazendas associadas em formato string JSON para ler depois
            localStorage.setItem('user_fazendas', JSON.stringify(dados.fazendas));

            // Extrai e isola o ID da fazenda ativa para talhões/funcionários
            if (dados.fazendas && dados.fazendas.length > 0) {
                // Se a chave vier como objeto completo contendo id_fazenda, ou id direto
                const primeiraFazenda = dados.fazendas[0];
                const idFazenda = primeiraFazenda.id_fazenda !== undefined ? primeiraFazenda.id_fazenda : primeiraFazenda.id;
                localStorage.setItem('user_fazenda_id', idFazenda);
            } else {
                localStorage.setItem('user_fazenda_id', '0');
            }

            window.location.href = 'dashboard.html';
        } else {
            throw new Error(dados.detail || "Falha na autenticação.");
        }

    } catch (erro) {
        alertMensagem.textContent = erro.message;
        alertErro.classList.remove('hidden');
        
        btnTexto.textContent = "Validar e Acessar Logs";
        btnEntrar.disabled = false;
        btnEntrar.classList.remove('opacity-75', 'cursor-wait');
    }
});