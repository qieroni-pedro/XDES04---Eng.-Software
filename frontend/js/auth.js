document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem('agro_token');
    
    // Pega o nome do arquivo
    let paginaAtual = window.location.pathname.split("/").pop().trim();
    if (paginaAtual === "") {
        paginaAtual = "index.html";
    }

    const paginaLogin = "index.html"; 

    console.log(`[Segurança] Página: ${paginaAtual} | Autenticado: ${!!token}`);

    // CASO 1: O usuário está em uma página interna mas NÃO está logado
    if (!token && paginaAtual !== paginaLogin) {
        console.warn("Acesso negado. Redirecionando para a tela de autenticação...");
        window.location.href = paginaLogin;
        return; 
    }

    // CASO 2: O usuário JÁ está logado, mas tentou entrar na página de login de novo
    if (token && paginaAtual === paginaLogin) {
        console.log("Usuário já autenticado. Redirecionando para a dashboard...");
        window.location.href = "dashboard.html";
        return;
    }

    // Se passou pelas travas de segurança e o token existe, alimenta a interface
    if (token) {
        configurarDadosOperador();
    }
});

function configurarDadosOperador() {
    const nome = localStorage.getItem('user_nome') || 'Operador';
    const perfil = localStorage.getItem('user_perfil') || 'Técnico';

    const lblNome = document.getElementById('lbl-nome-usuario');
    const lblPerfil = document.getElementById('lbl-perfil-usuario');

    if (lblNome) lblNome.textContent = nome;
    if (lblPerfil) lblPerfil.textContent = perfil;

    // Configura o clique do botão de logout na barra lateral
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout && !btnLogout.dataset.hasListener) {
        btnLogout.dataset.hasListener = "true"; // Impede que o JS crie múltiplos eventos no mesmo botão
        btnLogout.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Sessão encerrada pelo usuário.");
            localStorage.clear(); 
            window.location.href = "index.html"; 
        });
    }
}