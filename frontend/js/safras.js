const URL_API_SAFRAS  = "http://127.0.0.1:8000/api/v1/safras";
const URL_API_TALHOES = "http://127.0.0.1:8000/api/v1/talhoes";

// Inicialização
document.addEventListener("DOMContentLoaded", async () => {
    const token = localStorage.getItem("agro_token");
    const perfil = localStorage.getItem("user_perfil");

    if (!token) { window.location.href = "index.html"; return; }

    // TRAVA RBAC VISUAL: Se for Gestor, esconde o botão de abrir nova safra completamente
    const btnNovo = document.getElementById("btn-nova-safra") || document.getElementById("btn-abrir-modal");
    if (perfil === "Gestor" && btnNovo) {
        btnNovo.classList.add("hidden");
    }

    // Sequenciar: primeiro talhões (popula os selects), depois safras
    await carregarTalhoesNosFiltros();
    await carregarSafras();
});

// Fetch com retry automático (até 3 tentativas, intervalo de 400ms)
async function fetchComRetry(url, opcoes, tentativas = 3, intervalo = 400) {
    for (let i = 1; i <= tentativas; i++) {
        try {
            const resp = await fetch(url, opcoes);
            return resp;
        } catch (err) {
            if (i === tentativas) throw err;
            console.warn(`[Retry ${i}/${tentativas}] ${url} — aguardando ${intervalo}ms...`);
            await new Promise(r => setTimeout(r, intervalo));
        }
    }
}

// Popula selects de talhão (filtro + formulário de abertura)
async function carregarTalhoesNosFiltros() {
    const token = localStorage.getItem("agro_token");
    try {
        const resp = await fetchComRetry(`${URL_API_TALHOES}/`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) return;
        const talhoes = await resp.json();

        const selFiltro = document.getElementById("filtro-talhao");
        const selAb     = document.getElementById("ab-talhao");

        selFiltro.querySelectorAll("option:not([value=''])").forEach(o => o.remove());
        selAb.querySelectorAll("option:not([value=''])").forEach(o => o.remove());

        talhoes.forEach(t => {
            selFiltro.appendChild(new Option(`${t.nome} (${t.area_ha} ha)`, t.id));
            selAb.appendChild(new Option(`${t.nome} (${t.area_ha} ha)`, t.id));
        });
    } catch (err) {
        console.error("[Talhões] Falha ao carregar após retries:", err);
    }
}

// RFS07 – CONSULTAR (listar com filtros)
async function carregarSafras() {
    const token     = localStorage.getItem("agro_token");
    const idTalhao  = document.getElementById("filtro-talhao").value;
    const variedade = document.getElementById("filtro-variedade").value;
    const status    = document.getElementById("filtro-status").value;

    let url = `${URL_API_SAFRAS}/?`;
    if (idTalhao)  url += `id_talhao=${idTalhao}&`;
    if (variedade) url += `variedade=${encodeURIComponent(variedade)}&`;
    if (status)    url += `status=${encodeURIComponent(status)}&`;

    const tbody = document.getElementById("tbody-safras");
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400 font-mono text-[11px]">
        <span class="animate-pulse">Carregando safras...</span></td></tr>`;

    try {
        const resp = await fetchComRetry(url, {
            headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" }
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `Erro ${resp.status}`);
        }
        renderizarTabelaSafras(await resp.json());
    } catch (err) {
        console.error("[Safras] Erro ao listar:", err);
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-red-400 font-mono text-[11px]">
            Falha ao carregar. Verifique se a API está rodando e tente novamente.</td></tr>`;
    }
}

// Renderização da tabela com restrições rígidas de auditoria
function renderizarTabelaSafras(lista) {
    const tbody = document.getElementById("tbody-safras");
    tbody.innerHTML = "";

    const perfil = localStorage.getItem("user_perfil");

    if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-8 text-slate-400 font-mono text-[11px]">
            Nenhuma safra encontrada para os parâmetros informados.</td></tr>`;
        return;
    }

    lista.forEach(s => {
        const badgeClass = {
            "Planejada":         "badge-planejada",
            "Em andamento":      "badge-andamento",
            "Colhida/Finalizada":"badge-colhida",
        }[s.status] || "";

        const produtividade = s.produtividade_safra != null
            ? `<span class="font-mono font-semibold text-emerald-700">${s.produtividade_safra} sc/ha</span>`
            : `<span class="text-slate-300 font-mono text-[10px]">—</span>`;

        let colunaAcoesHTML = "";

        if (perfil === "Gestor") {
            colunaAcoesHTML = `<span class="text-slate-400 font-mono text-[10px] uppercase tracking-wider">Apenas Consulta</span>`;
        } else {
            const ehConcluida = s.status === "Colhida/Finalizada";

            const btnEncerrar = !ehConcluida
                ? `<button onclick="abrirModalEncerramento(${s.id}, '${_esc(s.nome_talhao)}', '${_esc(s.variedade_cultura)}', '${s.data_inicio_prevista}')"
                       class="text-slate-400 hover:text-emerald-700 px-2 py-1 transition-all cursor-pointer" title="Registrar Colheita">
                       <i class="bi bi-trophy"></i>
                   </button>`
                : "";

            const btnEditar = ehConcluida
                ? `<button class="text-slate-300 cursor-not-allowed px-2 py-1 transition-all" title="Histórico Auditado e Travado (Imutável)" disabled>
                       <i class="bi bi-lock-fill"></i>
                   </button>`
                : `<button onclick="abrirModalEdicao(${JSON.stringify(s).replace(/"/g, '&quot;')})"
                       class="text-slate-400 hover:text-emerald-700 px-2 py-1 transition-all cursor-pointer" title="Editar">
                       <i class="bi bi-pencil-square"></i>
                   </button>`;

            colunaAcoesHTML = `
                ${btnEditar}
                ${btnEncerrar}
                <button onclick="solicitarExclusao(${s.id}, '${s.status}')"
                    class="text-slate-400 hover:text-red-600 px-2 py-1 transition-all cursor-pointer" title="Excluir">
                    <i class="bi bi-trash3"></i>
                </button>
            `;
        }

        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50/50 transition-all";
        tr.innerHTML = `
            <td class="px-6 py-4 font-semibold text-slate-800">${_esc(s.nome_talhao)}</td>
            <td class="px-6 py-4 text-slate-700">${_esc(s.variedade_cultura)}</td>
            <td class="px-6 py-4 font-mono text-slate-500 text-[11px]">${_formatarData(s.data_inicio_prevista)}</td>
            <td class="px-6 py-4 font-mono text-slate-500 text-[11px]">${_formatarData(s.data_colheita_prevista)}</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded text-[11px] font-medium ${badgeClass}">
                    ${s.status}
                </span>
            </td>
            <td class="px-6 py-4">${produtividade}</td>
            <td class="px-6 py-4 text-right space-x-1">
                ${colunaAcoesHTML}
            </td>`;
        tbody.appendChild(tr);
    });
}

// Modal de Abertura (RFS05) - CORRIGIDO
function abrirModalAbertura() {
    if (localStorage.getItem("user_perfil") === "Gestor") return;

    document.getElementById("form-abertura").reset();
    document.getElementById("ab-id").value = "";
    document.getElementById("modal-abertura-titulo").textContent = "Abrir Nova Safra";
    document.getElementById("aviso-bloqueio").classList.add("hidden");
    
    // CORREÇÃO: Status liberado e limpo para escolha inicial do técnico
    const statusSelect = document.getElementById("ab-status");
    statusSelect.disabled = false;
    statusSelect.classList.remove("opacity-50", "cursor-not-allowed");
    statusSelect.value = "Planejada"; 

    ["ab-talhao","ab-variedade","ab-inicio","ab-colheita"].forEach(id => {
        document.getElementById(id).disabled = false;
        document.getElementById(id).classList.remove("opacity-50", "cursor-not-allowed");
    });
    document.getElementById("modal-abertura").classList.remove("hidden");
}

// Modal de Edição (RFS06) - OTIMIZADO PARA AUDITORIA
function abrirModalEdicao(safra) {
    if (localStorage.getItem("user_perfil") === "Gestor") return;

    if (safra.status === "Colhida/Finalizada") {
        alert("Erro de Consistência: Esta safra já foi colhida e finalizada. O histórico é imutável para auditoria.");
        return;
    }

    document.getElementById("ab-id").value            = safra.id;
    document.getElementById("ab-variedade").value     = safra.variedade_cultura;
    document.getElementById("ab-inicio").value        = safra.data_inicio_prevista;
    document.getElementById("ab-colheita").value      = safra.data_colheita_prevista;
    document.getElementById("ab-status").value        = safra.status;
    document.getElementById("modal-abertura-titulo").textContent = "Editar Safra";

    const selTalhao = document.getElementById("ab-talhao");
    selTalhao.value = safra.id_talhao;

    const statusSelect = document.getElementById("ab-status");

    if (safra.status === "Em andamento") {
        // Se já iniciou, congela o status e os dados de planejamento (Trava de auditoria)
        statusSelect.disabled = true;
        statusSelect.classList.add("opacity-50", "cursor-not-allowed");
        
        document.getElementById("aviso-bloqueio").classList.remove("hidden");
        ["ab-talhao","ab-variedade","ab-inicio"].forEach(id => {
            const el = document.getElementById(id);
            el.disabled = true;
            el.classList.add("opacity-50", "cursor-not-allowed");
        });
    } else {
        // Se ainda for "Planejada", permite mudar para "Em andamento" ou corrigir os dados iniciais
        statusSelect.disabled = false;
        statusSelect.classList.remove("opacity-50", "cursor-not-allowed");
        
        document.getElementById("aviso-bloqueio").classList.add("hidden");
        ["ab-talhao","ab-variedade","ab-inicio"].forEach(id => {
            const el = document.getElementById(id);
            el.disabled = false;
            el.classList.remove("opacity-50", "cursor-not-allowed");
        });
    }

    document.getElementById("modal-abertura").classList.remove("hidden");
}

function fecharModalAbertura() {
    document.getElementById("modal-abertura").classList.add("hidden");
}

// Salvar safra (POST ou PUT)
async function salvarSafra() {
    if (localStorage.getItem("user_perfil") === "Gestor") {
        alert("Operação negada: Seu perfil possui permissão apenas de leitura.");
        return;
    }

    const token = localStorage.getItem("agro_token");
    const id    = document.getElementById("ab-id").value;

    const dados = {
        id_talhao:             parseInt(document.getElementById("ab-talhao").value),
        variedade_cultura:     document.getElementById("ab-variedade").value.trim(),
        data_inicio_prevista:  document.getElementById("ab-inicio").value,
        data_colheita_prevista:document.getElementById("ab-colheita").value,
        status:                document.getElementById("ab-status").value,
    };

    if (!dados.id_talhao || !dados.variedade_cultura || !dados.data_inicio_prevista || !dados.data_colheita_prevista) {
        alert("Preencha todos os campos obrigatórios (*).");
        return;
    }
    if (dados.data_colheita_prevista <= dados.data_inicio_prevista) {
        alert("A data de colheita prevista deve ser posterior à data de plantio.");
        return;
    }

    const url    = id ? `${URL_API_SAFRAS}/${id}` : `${URL_API_SAFRAS}/`;
    const method = id ? "PUT" : "POST";

    try {
        const resp = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
            body: JSON.stringify(dados)
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao salvar safra.");
        }
        fecharModalAbertura();
        carregarSafras();
    } catch (err) {
        alert(err.message);
    }
}

// Modal de Encerramento (PATCH /encerrar)
function abrirModalEncerramento(id, nomeTalhao, variedade, dataInicio) {
    if (localStorage.getItem("user_perfil") === "Gestor") return;

    document.getElementById("enc-id").value        = id;
    document.getElementById("enc-nome-talhao").textContent = nomeTalhao;
    document.getElementById("enc-variedade").textContent   = variedade;
    document.getElementById("enc-inicio").textContent      = _formatarData(dataInicio);
    document.getElementById("enc-data-real").value        = "";
    document.getElementById("enc-produtividade").value    = "";
    document.getElementById("enc-data-real").min = dataInicio;
    document.getElementById("modal-encerramento").classList.remove("hidden");
}

function fecharModalEncerramento() {
    document.getElementById("modal-encerramento").classList.add("hidden");
}

async function confirmarEncerramento() {
    if (localStorage.getItem("user_perfil") === "Gestor") return;

    const token        = localStorage.getItem("agro_token");
    const id           = document.getElementById("enc-id").value;
    const produtividade = parseFloat(document.getElementById("enc-produtividade").value);
    const dataReal     = document.getElementById("enc-data-real").value;

    if (!dataReal) { alert("Informe a data real de colheita."); return; }
    if (!produtividade || produtividade <= 0) { alert("Informe uma produtividade válida (sc/ha)."); return; }

    try {
        const resp = await fetch(`${URL_API_SAFRAS}/${id}/encerrar`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
            body: JSON.stringify({
                produtividade_safra:   produtividade,
                data_colheita_prevista: dataReal
            })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao encerrar safra.");
        }
        fecharModalEncerramento();
        carregarSafras();
    } catch (err) {
        alert(err.message);
    }
}

// RFS08 - EXCLUIR SAFRA
async function solicitarExclusao(id, statusSafra) {
    if (localStorage.getItem("user_perfil") === "Gestor") return;

    if (statusSafra === "Em andamento" || statusSafra === "Colhida/Finalizada") {
        alert(`Operação Retida por Segurança: Não é permitido excluir uma safra com status de "${statusSafra}". Apenas safras com status "Planejada" e livres de lançamentos de atividades podem ser removidas.`);
        return;
    }

    if (!confirm("Confirmar a remoção desta safra? Só é possível excluir safras sem atividades registradas.")) return;
    const token = localStorage.getItem("agro_token");
    try {
        const resp = await fetch(`${URL_API_SAFRAS}/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao excluir safra.");
        }
        carregarSafras();
    } catch (err) {
        alert(err.message);
    }
}

// Helpers
function _esc(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
}

function _formatarData(iso) {
    if (!iso) return "—";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
}