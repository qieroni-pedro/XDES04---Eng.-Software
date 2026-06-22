document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "http://127.0.0.1:8000/api/v1";

    const selectSafra = document.getElementById("id_safra");
    const formEvento = document.getElementById("form-evento");
    const tbodyEventos = document.getElementById("tbody-eventos");
    
    // Elementos de Filtro Superior
    const filtroSafra = document.getElementById("filtro-safra");
    const filtroTipo = document.getElementById("filtro-tipo");

    let listaSafrasServidor = [];
    let listaEventosServidor = [];

    // Busca e armazena safras para alimentar os filtros e validações
    async function buscarSafras() {
        try {
            const tokenAtual = localStorage.getItem("agro_token");
            const res = await fetch(`${API_BASE}/safras/`, { 
                headers: { "Authorization": `Bearer ${tokenAtual}` } 
            });
            if (res.ok) {
                listaSafrasServidor = await res.json();
                popularDropdownFiltroSafras();
            }
        } catch (e) { console.error("Erro ao carregar mapeamento de safras"); }
    }

    function popularDropdownFiltroSafras() {
        if (!filtroSafra) return;
        filtroSafra.innerHTML = '<option value="">Todas as safras</option>';
        listaSafrasServidor.forEach(s => {
            filtroSafra.innerHTML += `<option value="${s.id}">${s.variedade_cultura}</option>`;
        });
    }

    // Filtra e renderiza a tabela de ocorrências registradas em tempo real
    function aplicarFiltrosERenderizar() {
        const valSafra = filtroSafra ? filtroSafra.value : "";
        const valTipo = filtroTipo ? filtroTipo.value : "";

        const eventosFiltrados = listaEventosServidor.filter(ev => {
            const matchSafra = valSafra === "" || Number(ev.id_safra) === Number(valSafra);
            const matchTipo = valTipo === "" || ev.tipo_evento === valTipo;
            return matchSafra && matchTipo;
        });

        tbodyEventos.innerHTML = "";
        if (eventosFiltrados.length === 0) {
            tbodyEventos.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 font-medium">Nenhum evento extremo localizado com os filtros aplicados.</td></tr>`;
            return;
        }

        eventosFiltrados.forEach(ev => {
            const dataFormatada = ev.data_ocorrência
                ? new Date(ev.data_ocorrência).toLocaleDateString('pt-BR', { timeZone: 'UTC' })
                : '---';
            
            tbodyEventos.innerHTML += `
                <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="px-6 py-3.5 font-medium text-slate-900">${ev.nome_safra || 'Safra Vinculada'}</td>
                    <td class="px-6 py-3.5">
                        <span class="inline-flex items-center gap-1.5 font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-100 text-xs">
                            <i class="bi bi-exclamation-triangle-fill"></i> ${ev.tipo_evento}
                        </span>
                    </td>
                    <td class="px-6 py-3.5 font-mono text-[11px] text-slate-500">${dataFormatada}</td>
                    <td class="px-6 py-3.5 text-slate-600 text-sm max-w-xs truncate" title="${ev.descricao_danos}">${ev.descricao_danos}</td>
                    <td class="px-6 py-3.5 text-center">
                        <button
                            onclick="abrirModalVisualizar(${ev.id})"
                            title="Visualizar detalhes"
                            class="inline-flex items-center justify-center w-7 h-7 rounded-md text-slate-400 hover:text-rose-700 hover:bg-rose-50 border border-transparent hover:border-rose-100 transition-all cursor-pointer"
                        >
                            <i class="bi bi-eye text-sm"></i>
                        </button>
                    </td>
                </tr>`;
        });
    }

    async function carregarHistoricoEventos() {
        try {
            const tokenAtual = localStorage.getItem("agro_token");
            const res = await fetch(`${API_BASE}/eventos`, { 
                headers: { "Authorization": `Bearer ${tokenAtual}` } 
            });
            if (!res.ok) throw new Error();
            listaEventosServidor = await res.json();
            aplicarFiltrosERenderizar();
        } catch (err) {
            exibirToast("Erro de sincronização com o banco de Safra/Eventos.", "error");
        }
    }

    if (filtroSafra) filtroSafra.addEventListener("change", aplicarFiltrosERenderizar);
    if (filtroTipo) filtroTipo.addEventListener("change", aplicarFiltrosERenderizar);

    // Envio do formulário (Apenas inserção)
    formEvento.addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btn-submit");
        if (btn) btn.disabled = true;

        const formData = new FormData(formEvento);
        const tokenAtual = localStorage.getItem("agro_token");

        try {
            const res = await fetch(`${API_BASE}/eventos`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${tokenAtual}` },
                body: formData
            });
            const data = await res.json();

            if (res.status === 201) {
                exibirToast("Ocorrência de evento extremo registrada com sucesso!", "success");
                fecharModalEvento();
                await carregarHistoricoEventos();
            } else {
                exibirToast(data.detail || "Erro ao processar registro de sinistro.", "error");
            }
        } catch (err) {
            exibirToast("Falha de comunicação com o servidor.", "error");
        } finally {
            if (btn) btn.disabled = false;
        }
    });

    // Inicializador Inicial da Janela
    buscarSafras().then(() => {
        carregarHistoricoEventos();
    });

    // --- MÉTODOS DE CONTROLE DA MODAL DE REGISTRO ---
    window.abrirModalEvento = function() {
        if (formEvento) formEvento.reset();
        
        if (selectSafra) {
            selectSafra.innerHTML = '<option value="">-- Selecione uma Safra Operacional --</option>';
            // REGRA CRÍTICA: Filtra exibindo APENAS as safras "Em andamento"
            const safrasAtivas = listaSafrasServidor.filter(s => s.status === "Em andamento");
            
            if (safrasAtivas.length === 0) {
                selectSafra.innerHTML = '<option value="">Nenhuma safra em andamento localizada</option>';
            } else {
                safrasAtivas.forEach(s => {
                    selectSafra.innerHTML += `<option value="${s.id}">${s.variedade_cultura} [Talhão: ${s.nome_talhao || s.id_talhao}]</option>`;
                });
            }
        }
        document.getElementById("modal-evento").classList.remove("hidden");
    };

    window.fecharModalEvento = function() {
        document.getElementById("modal-evento").classList.add("hidden");
    };

    // --- MÉTODOS DE CONTROLE DA MODAL DE VISUALIZAÇÃO ---
    window.abrirModalVisualizar = async function(idEvento) {
        const modal = document.getElementById("modal-visualizar");
        const elLoading = document.getElementById("modal-vis-loading");
        const elErro = document.getElementById("modal-vis-erro");
        const elConteudo = document.getElementById("modal-vis-conteudo");

        // Reseta para o estado de carregamento
        elLoading.classList.remove("hidden");
        elErro.classList.add("hidden");
        elConteudo.classList.add("hidden");
        modal.classList.remove("hidden");

        try {
            const tokenAtual = localStorage.getItem("agro_token");
            const res = await fetch(`${API_BASE}/eventos/${idEvento}`, {
                headers: { "Authorization": `Bearer ${tokenAtual}` }
            });

            if (!res.ok) throw new Error();
            const ev = await res.json();

            // Preenche os campos com os dados retornados
            document.getElementById("vis-id").textContent = String(ev.id).padStart(5, "0");
            document.getElementById("vis-tipo").textContent = ev.tipo_evento;
            document.getElementById("vis-safra").textContent = ev.nome_safra || "—";
            document.getElementById("vis-talhao").textContent = ev.nome_talhao ? `Talhão: ${ev.nome_talhao}` : "";
            document.getElementById("vis-descricao").textContent = ev.descricao_danos;
            document.getElementById("vis-data").textContent = ev["data_ocorrência"]
                ? new Date(ev["data_ocorrência"]).toLocaleDateString("pt-BR", { timeZone: "UTC" })
                : "—";

            elLoading.classList.add("hidden");
            elConteudo.classList.remove("hidden");

        } catch (err) {
            elLoading.classList.add("hidden");
            elErro.classList.remove("hidden");
        }
    };

    window.fecharModalVisualizar = function() {
        document.getElementById("modal-visualizar").classList.add("hidden");
    };
});