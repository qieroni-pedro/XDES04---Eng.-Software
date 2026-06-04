document.addEventListener("DOMContentLoaded", async () => {
    const cmbSafra = document.getElementById('cmb-safra');
    const perfil = localStorage.getItem('user_perfil');

    // Esconde a aba de funcionários no menu se for Técnico Agrícola
    if (perfil === 'Técnico Agrícola') {
        const menuFuncionarios = document.getElementById('menu-funcionarios');
        if (menuFuncionarios) menuFuncionarios.classList.add('hidden');
    }
    
    // 1. Primeiro carrega dinamicamente as safras disponíveis no banco de dados
    await carregarOpcoesDeSafras(cmbSafra);

    // 2. Escuta mudanças no select
    cmbSafra.addEventListener('change', () => {
        carregarDadosDashboard(cmbSafra.value);
    });

    // 3. Carga inicial dos indicadores baseada na primeira safra retornada
    if (cmbSafra.value) {
        carregarDadosDashboard(cmbSafra.value);
    }
});

// Alimenta o select com dados reais do banco
async function carregarOpcoesDeSafras(selectElement) {
    try {
        const token = localStorage.getItem('agro_token');
        const response = await fetch(`http://127.0.0.1:8000/api/v1/safras/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) throw new Error();

        const safras = await response.json(); // Espera uma lista de safras: [{id: 1, nome: "Safra 2024/25 - Soja"}, ...]
        
        selectElement.innerHTML = ""; // Limpa o "Carregando safras..."
        
        if (safras.length === 0) {
            selectElement.innerHTML = `<option value="">Nenhuma safra cadastrada</option>`;
            return;
        }

        safras.forEach(safra => {
            selectElement.innerHTML += `<option value="${safra.id}">${safra.nome}</option>`;
        });

    } catch (error) {
        console.error("Erro ao carregar lista de safras:", error);
        selectElement.innerHTML = `<option value="">Erro ao carregar safras</option>`;
    }
}

async function carregarDadosDashboard(safraId) {
    if (!safraId) return; // Evita requisição se não houver ID válido
    try {
        const token = localStorage.getItem('agro_token');
        const response = await fetch(`http://127.0.0.1:8000/api/v1/safras/${safraId}/indicadores`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Falha ao obter indicadores do servidor.");

        const dados = await response.json();
        renderizarDashboard(dados);

    } catch (error) {
        console.error("Erro na comunicação com a API de indicadores:", error);
        renderizarDashboard({ porridge: 0, executadas: 0, totais: 0, proximasAtividades: [], alertas: [] });
    }
}

// ... Sua função renderizarDashboard(dados) continua exatamente igual abaixo ...
function renderizarDashboard(dados) {
    document.getElementById('txt-porcentagem').textContent = `${dados.porcentagem}%`;
    document.getElementById('lbl-atividades-executadas').textContent = `${dados.executadas} de ${dados.totais}`;
    
    const svgProgresso = document.getElementById('svg-progresso');
    if (svgProgresso) {
        svgProgresso.setAttribute('stroke-dasharray', `${dados.porcentagem}, 100`);
    }

    const containerAtividades = document.getElementById('container-proximas-atividades');
    containerAtividades.innerHTML = ""; 
    
    if (!dados.proximasAtividades || dados.proximasAtividades.length === 0) {
        containerAtividades.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-center py-12 text-slate-400">
                <i class="bi bi-calendar-x text-3xl mb-2 text-slate-300"></i>
                <p class="font-medium text-xs">Nenhuma atividade planejada</p>
                <p class="text-[10px] text-slate-400 max-w-[180px] mt-1">As tarefas agendadas aparecerão nesta cronologia assim que inseridas.</p>
            </div>
        `;
    } else {
        dados.proximasAtividades.forEach(atv => {
            containerAtividades.innerHTML += `
                <div class="flex items-center justify-between p-2 bg-slate-50 border border-slate-100 rounded-lg text-xs">
                    <div class="flex items-center space-x-3">
                        <span class="font-mono text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded text-[11px]">${atv.data}</span>
                        <span class="font-medium text-slate-700">${atv.nome}</span>
                    </div>
                    <span class="text-slate-500"><i class="bi bi-person text-xs"></i> ${atv.responsavel}</span>
                </div>
            `;
        });
    }

    const containerAlertas = document.getElementById('container-alertas-ativos');
    containerAlertas.innerHTML = "";
    
    if (!dados.alertas || dados.alertas.length === 0) {
        containerAlertas.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-center py-12 text-slate-400">
                <i class="bi bi-shield-check text-3xl mb-2 text-emerald-600/60"></i>
                <p class="font-medium text-xs text-slate-600">Nenhum alerta de risco</p>
                <p class="text-[10px] text-slate-400 max-w-[180px] mt-1">O barramento de compliance está operando sob normalidade técnica.</p>
            </div>
        `;
    } else {
        dados.alertas.forEach(alerta => {
            const corClasse = alerta.tipo === 'critico' ? 'bg-red-50/60 border-red-200 text-red-700' : 'bg-amber-50/60 border-amber-200 text-amber-700';
            const icone = alerta.tipo === 'critico' ? 'bi-exclamation-circle-fill text-red-600' : 'bi-exclamation-triangle-fill text-amber-600';
            
            containerAlertas.innerHTML += `
                <div class="${corClasse} border p-3 rounded-lg flex gap-3 items-start text-xs">
                    <i class="bi ${icone} text-base shrink-0"></i>
                    <div>
                        <p class="font-semibold">${alerta.titulo}</p>
                        <p class="opacity-90 text-[11px] mt-0.5">${alerta.desc}</p>
                    </div>
                </div>
            `;
        });
    }
}