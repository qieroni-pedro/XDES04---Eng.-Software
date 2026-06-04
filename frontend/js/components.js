document.addEventListener("DOMContentLoaded", () => {
    console.log("Components.js carregado com sucesso. Iniciando injeção da Sidebar...");
    
    const sidebarContainer = document.getElementById('sidebar-container');
    
    if (!sidebarContainer) {
        return; // Caso não tenha o container na página, interrompe
    }

    // Busca os dados salvos no login ou define padrões seguros
    const nomeUsuario = localStorage.getItem('user_nome') || 'Operador Central';
    const perfilUsuario = localStorage.getItem('user_perfil') || 'Técnico Agrícola';

    // String literal contendo toda a estrutura HTML da Sidebar
    const sidebarHTML = `
        <aside class="w-64 bg-gradient-to-b from-emerald-900 to-emerald-950 text-white flex flex-col justify-between p-6 h-screen shrink-0 border-r border-emerald-800/40">
            <div>
                <div class="flex items-center space-x-3 text-xl font-bold tracking-tight mb-8 border-b border-emerald-800/60 pb-5">
                    <i class="bi bi-shield-check text-emerald-400 text-2xl"></i>
                    <span class="text-white">Agro<span class="text-emerald-400 font-medium">Gestor</span></span>
                </div>

                <div class="mb-6 bg-white/10 border border-white/10 p-3 rounded-xl">
                    <p class="text-[10px] text-emerald-300 font-mono tracking-wider uppercase">Operador Autenticado</p>
                    <p id="lbl-nome-usuario" class="text-sm font-semibold truncate mt-0.5">${nomeUsuario}</p>
                    <p id="lbl-perfil-usuario" class="text-[9px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-md inline-block mt-1.5 font-mono uppercase tracking-wider">${perfilUsuario}</p>
                </div>

                <nav class="space-y-1.5">
                    <a href="dashboard.html" id="menu-dashboard" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-grid-1x2-fill"></i> <span>Dashboard</span>
                    </a>
                    
                    <a href="gerenciar_funcionarios.html" id="menu-funcionarios" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-people"></i> <span>Funcionários / Técnicos</span>
                    </a>
                    
                    <a href="gerenciar_talhoes.html" id="menu-talhoes" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-geo-alt"></i> <span>Módulo Talhões</span>
                    </a>

                    <a href="#" class="flex items-center space-x-3 text-emerald-200/40 cursor-not-allowed px-4 py-2.5 text-xs font-medium">
                        <i class="bi bi-tree"></i> <span>Gerenciar Safras (Futuro)</span>
                    </a>
                    <a href="#" class="flex items-center space-x-3 text-emerald-200/40 cursor-not-allowed px-4 py-2.5 text-xs font-medium">
                        <i class="bi bi-journal-check"></i> <span>Registrar Atividades (Futuro)</span>
                    </a>
                </nav>
            </div>

            <button id="btn-logout" class="flex items-center space-x-3 text-emerald-300 hover:bg-red-900/20 hover:text-red-400 px-4 py-2.5 rounded-lg text-xs font-medium transition-all w-full text-left cursor-pointer border border-transparent hover:border-red-900/30">
                <i class="bi bi-box-arrow-left"></i> <span>Encerrar Sessão</span>
            </button>
        </aside>
    `;

    sidebarContainer.innerHTML = sidebarHTML;

    // Executa as permissões RBAC e marcação de link ativo após injetar o menu
    aplicarPermissoesMenu();
    configurarCliqueLogout();
});

function aplicarPermissoesMenu() {
    const perfil = localStorage.getItem('user_perfil');
    
    if (perfil === 'Técnico Agrícola') {
        const menuFuncionarios = document.getElementById('menu-funcionarios');
        if (menuFuncionarios) menuFuncionarios.classList.add('hidden');
    }

    const paginaAtual = window.location.pathname.split("/").pop();
    if (paginaAtual === "dashboard.html") {
        document.getElementById('menu-dashboard')?.classList.add('bg-emerald-800', 'text-white');
    } else if (paginaAtual === "gerenciar_talhoes.html") {
        document.getElementById('menu-talhoes')?.classList.add('bg-emerald-800', 'text-white');
    } else if (paginaAtual === "gerenciar_funcionarios.html") {
        document.getElementById('menu-funcionarios')?.classList.add('bg-emerald-800', 'text-white');
    }
}

function configurarCliqueLogout() {
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
        btnLogout.addEventListener('click', (e) => {
            e.preventDefault();
            console.log("Encerrando sessão do operador...");
            localStorage.clear(); // Limpa tokens de acesso e dados de perfil do navegador
            window.location.href = "index.html"; // Redireciona corretamente para a raiz do login
        });
    }
}