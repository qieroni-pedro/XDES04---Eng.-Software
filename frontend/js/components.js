document.addEventListener("DOMContentLoaded", () => {
    console.log("Components.js carregado com sucesso. Iniciando injeção da Sidebar...");
    
    const sidebarContainer = document.getElementById('sidebar-container');
    
    if (!sidebarContainer) {
        return; // Caso não tenha o container na página, interrompe
    }

    // Busca os dados salvos no login ou define padrões seguros
    const nomeUsuario = localStorage.getItem('user_nome') || 'Operador Central';
    const perfilUsuario = localStorage.getItem('user_perfil') || 'Técnico Agrícola';

    // String literal contendo toda a estrutura HTML da Sidebar atualizada com Eventos Extremos
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

                    <a href="gerenciar_safras.html" id="menu-safras" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-tree"></i> <span>Gerenciar Safras</span>
                    </a>
                    
                    <a href="gerenciar_atividades.html" id="menu-atividades" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-journal-check"></i> <span>Registrar Atividades</span>
                    </a>

                    <a href="eventos_extremos.html" id="menu-eventos" class="flex items-center space-x-3 text-emerald-100 hover:bg-rose-900/40 hover:text-rose-200 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-shield-exclamation text-rose-400"></i> <span>Eventos Extremos</span>
                    </a>
                    <a href="relatorios.html" id="menu-relatorios" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-bar-chart-line-fill"></i> <span>Relatórios</span>
                    </a>
                    <a href="comparacao.html" id="menu-comparativo" class="flex items-center space-x-3 text-emerald-100 hover:bg-emerald-800/50 px-4 py-2.5 rounded-lg text-xs font-medium transition-all">
                        <i class="bi bi-bar-chart-steps"></i> <span>Comparativo de Safras</span>
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
    const paginaAtual = window.location.pathname.split("/").pop();

    // Regras RBAC // DRE seção 2.2
    if (perfil === 'Técnico Agrícola') {
        // Técnico não gerencia Funcionários
        document.getElementById('menu-funcionarios')?.classList.add('hidden');

        // Proteção de rota: redireciona se Técnico tentar acessar diretamente
        const rotasBloqueadasTecnico = ['gerenciar_funcionarios.html'];
        if (rotasBloqueadasTecnico.includes(paginaAtual)) {
            window.location.href = 'dashboard.html';
            return;
        }
    }

    // Destaque do item ativo na sidebar (Adicionado 'eventos_extremos.html')
    const mapaAtivo = {
        'dashboard.html':             'menu-dashboard',
        'gerenciar_talhoes.html':      'menu-talhoes',
        'gerenciar_safras.html':       'menu-safras',
        'gerenciar_funcionarios.html': 'menu-funcionarios',
        'gerenciar_atividades.html':   'menu-atividades',
        'eventos_extremos.html':       'menu-eventos',
        'relatorios.html':             'menu-relatorios',
        'comparacao.html':             'menu-comparativo'
    };
    
    const idAtivo = mapaAtivo[paginaAtual];
    if (idAtivo) {
        // Se for a página de eventos, ganha uma cor de destaque mais sutil voltada a avisos/sinistros
        if (idAtivo === 'menu-eventos') {
            document.getElementById(idAtivo)?.classList.add('bg-rose-950/60', 'text-rose-200', 'font-semibold');
        } else {
            document.getElementById(idAtivo)?.classList.add('bg-emerald-800', 'text-white');
        }
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

// FUNÇÃO GLOBAL AUXILIAR: Injetor de Mensagens Toast
window.exibirToast = function(mensagem, tipo = "success") {
    const alertContainer = document.getElementById("alert-container");
    if (!alertContainer) return;

    alertContainer.className = "p-4 rounded-xl text-xs font-medium border transition-all animate-in fade-in duration-200";
    
    if (tipo === "success") {
        alertContainer.classList.add("bg-emerald-50", "text-emerald-800", "border-emerald-200");
        alertContainer.innerHTML = `<i class="bi bi-check-circle-fill"></i> ${mensagem}`;
    } else {
        alertContainer.classList.add("bg-rose-50", "text-rose-800", "border-rose-200");
        alertContainer.innerHTML = `<i class="bi bi-exclamation-octagon-fill"></i> ${mensagem}`;
    }
    
    alertContainer.classList.remove("hidden");
    
    setTimeout(() => {
        alertContainer.classList.add("hidden");
    }, 4000);
};