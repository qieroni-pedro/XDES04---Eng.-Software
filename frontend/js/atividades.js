document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "http://127.0.0.1:8000/api/v1";

    const selectSafra = document.getElementById("id_safra");
    const tipoAtividade = document.getElementById("tipo_atividade");
    const formAtividade = document.getElementById("form-atividade");
    const tbodyAtividades = document.getElementById("tbody-atividades");
    
    // Elementos de Filtro da Interface Superior
    const filtroSafra = document.getElementById("filtro-safra");
    const filtroStatus = document.getElementById("filtro-status");
    const filtroTipo = document.getElementById("filtro-tipo");

    // Cache Global de dados para filtragem em tempo real e renderização
    let listaSafrasServidor = [];
    let listaAtividadesServidor = [];

    // Elementos dos submenus específicos de Atividades (modo edição)
    const divIrrigacao = document.getElementById("sub-irrigacao");
    const divInsumos = document.getElementById("sub-insumos");
    const divPraga = document.getElementById("div-praga");

    // =========================================================================
    // REGRAS DE CONTROLE DE PERFIL (RBAC FRONT-END)
    // =========================================================================
    function obterPerfilUsuario() {
        try {
            const token = localStorage.getItem("agro_token");
            if (!token) return null;
            const payloadBase64 = token.split('.')[1];
            const payloadDecodificado = JSON.parse(atob(payloadBase64));
            return payloadDecodificado.perfil;
        } catch (e) {
            return null;
        }
    }

    const perfilUsuario = obterPerfilUsuario();
    const ehGestor = (perfilUsuario === "Gestor");

    // Se for Gestor, esconde o botão de criar novas atividades
    const btnNovoRegistro = document.getElementById("btn-nova-atividade") || document.querySelector("[onclick='abrirModalAtividade()']");
    if (ehGestor && btnNovoRegistro) {
        btnNovoRegistro.style.display = "none";
    }

    // =========================================================================
    // CONTROLE DE SUBMENUS (modo edição — só relevante para Técnico)
    // =========================================================================
    function gerenciarExibicaoSubmenus() {
        if (!tipoAtividade) return;
        const tipo = tipoAtividade.value;

        if (divIrrigacao) divIrrigacao.classList.add("hidden");
        if (divInsumos) divInsumos.classList.add("hidden");
        if (divPraga) divPraga.classList.add("hidden");

        if (tipo === "Irrigação") {
            if (divIrrigacao) divIrrigacao.classList.remove("hidden");
        } else if (tipo === "Adubação" || tipo === "Pulverização" || tipo === "Manejo de pragas/doenças") {
            if (divInsumos) divInsumos.classList.remove("hidden");
            if (tipo === "Manejo de pragas/doenças" && divPraga) divPraga.classList.remove("hidden");
        }
    }

    if (tipoAtividade) {
        tipoAtividade.addEventListener("change", gerenciarExibicaoSubmenus);
    }

    // =========================================================================
    // BUSCA E CACHE DE SAFRAS
    // =========================================================================
    async function buscarSafras() {
        try {
            const tokenAtual = localStorage.getItem("agro_token");
            const res = await fetch(`${API_BASE}/safras/`, { 
                headers: { "Authorization": `Bearer ${tokenAtual}` } 
            });
            if (res.ok) {
                listaSafrasServidor = await res.json();
                populadoFiltroDropdownSafras();
            }
        } catch (e) { console.error("Erro ao cachear safras"); }
    }

    if (filtroSafra) filtroSafra.addEventListener("change", aplicarFiltrosERenderizar);
    if (filtroStatus) filtroStatus.addEventListener("change", aplicarFiltrosERenderizar);
    if (filtroTipo) filtroTipo.addEventListener("change", aplicarFiltrosERenderizar);

    function populadoFiltroDropdownSafras() {
        if (!filtroSafra) return;
        filtroSafra.innerHTML = '<option value="">Todas as safras</option>';
        listaSafrasServidor.forEach(s => {
            filtroSafra.innerHTML += `<option value="${s.id}">${s.variedade_cultura}</option>`;
        });
    }

    function renderizarSelectBoxSafras(idSafraAtividadeAtual = null) {
        if (!selectSafra) return;
        selectSafra.innerHTML = '<option value="">-- Selecione uma Safra Operacional --</option>';
        
        listaSafrasServidor.forEach(s => {
            const ehFinalizada = (s.status === "Colhida/Finalizada");
            if (!ehFinalizada || s.id === Number(idSafraAtividadeAtual)) {
                selectSafra.innerHTML += `
                    <option value="${s.id}">
                        ${s.variedade_cultura} [Talhão: ${s.nome_talhao || s.id_talhao}] ${ehFinalizada ? '(CONCLUÍDA)' : ''}
                    </option>`;
            }
        });
    }

    // =========================================================================
    // FILTRAGEM E RENDERIZAÇÃO DA TABELA
    // =========================================================================
    function aplicarFiltrosERenderizar() {
        const valSafra = filtroSafra ? filtroSafra.value : "";
        const valStatus = filtroStatus ? filtroStatus.value : "";
        const valTipo = filtroTipo ? filtroTipo.value : "";

        const atividadesFiltradas = listaAtividadesServidor.filter(atv => {
            const matchSafra = valSafra === "" || Number(atv.id_safra) === Number(valSafra);
            const matchStatus = valStatus === "" || atv.status === valStatus;
            const matchTipo = valTipo === "" || atv.tipo_atividade === valTipo;
            return matchSafra && matchStatus && matchTipo;
        });

        tbodyAtividades.innerHTML = "";
        if (atividadesFiltradas.length === 0) {
            tbodyAtividades.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-slate-400 font-medium">Nenhuma atividade corresponde aos filtros aplicados.</td></tr>`;
            return;
        }

        atividadesFiltradas.forEach(atv => {
            const dataFormatada = atv.data_execucao
                ? new Date(atv.data_execucao).toLocaleDateString('pt-BR', { timeZone: 'UTC' })
                : '---';

            let badgeStyle = "bg-slate-100 text-slate-700 border-slate-200";
            if (atv.status === "Agendado")     badgeStyle = "bg-amber-50 text-amber-700 border-amber-200/60";
            if (atv.status === "Em andamento") badgeStyle = "bg-blue-50 text-blue-700 border-blue-200/60";
            if (atv.status === "Realizado")    badgeStyle = "bg-emerald-50 text-emerald-700 border-emerald-200/60";

            // =========================================================================
            // REGRA DO GESTOR NA TABELA: botão "Ver" → abre painel de leitura
            // =========================================================================
            let botoesAcao = "";

            if (ehGestor) {
                botoesAcao = `
                    <button onclick="verAtividade(${atv.id})"
                            class="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md
                                   bg-slate-100 text-slate-600 hover:bg-emerald-50 hover:text-emerald-700
                                   border border-slate-200 hover:border-emerald-200 transition-colors cursor-pointer"
                            title="Visualizar Detalhes">
                        <i class="bi bi-eye"></i> Ver
                    </button>`;
            } else {
                // Fluxo normal do Técnico Agrícola
                if (atv.status === "Agendado") {
                    botoesAcao = `
                        <button onclick="editarAtividade(${atv.id})" class="p-1 text-slate-400 hover:text-emerald-700 rounded transition-colors cursor-pointer" title="Editar Registro"><i class="bi bi-pencil"></i></button>
                        <button onclick="excluirAtividade(${atv.id})" class="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors cursor-pointer" title="Excluir Registro"><i class="bi bi-trash"></i></button>
                    `;
                } else if (atv.status === "Em andamento") {
                    botoesAcao = `
                        <button onclick="editarAtividade(${atv.id})" class="p-1 text-slate-400 hover:text-blue-700 rounded transition-colors cursor-pointer" title="Concluir Operação"><i class="bi bi-check-circle"></i></button>
                    `;
                } else if (atv.status === "Realizado") {
                    botoesAcao = `<span class="text-xs text-slate-400 font-medium"><i class="bi bi-lock-fill"></i> Trancado</span>`;
                }
            }

            tbodyAtividades.innerHTML += `
                <tr class="hover:bg-slate-50/80 transition-colors">
                    <td class="px-6 py-3.5 font-medium text-slate-900">${atv.nome_safra || 'Safra Alvo'}</td>
                    <td class="px-6 py-3.5"><span class="inline-flex items-center gap-1.5 font-medium">${atv.tipo_atividade}</span></td>
                    <td class="px-6 py-3.5 text-slate-500">${atv.responsavel || 'Técnico Operador'}</td>
                    <td class="px-6 py-3.5 font-mono text-[11px] text-slate-500">${dataFormatada}</td>
                    <td class="px-6 py-3.5">
                        <div class="flex items-center justify-between gap-2">
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${badgeStyle}">${atv.status}</span>
                            <div class="flex items-center gap-1.5 row-actions">${botoesAcao}</div>
                        </div>
                    </td>
                </tr>`;
        });
    }

    // =========================================================================
    // CARREGAMENTO DE ATIVIDADES
    // =========================================================================
    async function carregarAtividades() {
        try {
            const tokenAtual = localStorage.getItem("agro_token");
            const res = await fetch(`${API_BASE}/atividades`, { 
                headers: { "Authorization": `Bearer ${tokenAtual}` } 
            });
            if (!res.ok) throw new Error();
            listaAtividadesServidor = await res.json();
            aplicarFiltrosERenderizar();
        } catch (err) {
            exibirToast("Não foi possível carregar o histórico de atividades.", "error");
        }
    }

    // =========================================================================
    // SUBMIT DO FORMULÁRIO (somente Técnico chega aqui)
    // =========================================================================
    formAtividade.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (ehGestor) {
            exibirToast("Gestores não possuem permissão para salvar ou alterar atividades.", "error");
            return;
        }

        const btn = document.getElementById("btn-submit");
        if (btn) btn.disabled = true;

        const travados = formAtividade.querySelectorAll("select[disabled], input[disabled]");
        travados.forEach(el => el.disabled = false);

        const formData = new FormData(formAtividade);
        const idAtividade = formAtividade.dataset.id;
        const url = idAtividade ? `${API_BASE}/atividades/${idAtividade}` : `${API_BASE}/atividades`;
        const method = idAtividade ? "PUT" : "POST";
        const tokenAtual = localStorage.getItem("agro_token");

        travados.forEach(el => el.disabled = true);

        try {
            const res = await fetch(url, {
                method: method,
                headers: { "Authorization": `Bearer ${tokenAtual}` },
                body: formData
            });
            const data = await res.json();

            if (res.status === 201 || res.status === 200) {
                exibirToast(idAtividade ? "Status modificado com sucesso!" : "Atividade cadastrada!", "success");
                fecharModalAtividade();
                await carregarAtividades();
            } else {
                exibirToast(data.detail || "Erro ao processar requisição.", "error");
            }
        } catch (err) {
            exibirToast("Falha de comunicação com o servidor.", "error");
        } finally {
            if (btn) btn.disabled = false;
        }
    });

    buscarSafras().then(() => {
        renderizarSelectBoxSafras();
        carregarAtividades();
    });

    // Torna variáveis acessíveis aos métodos globais fora do escopo do DOMContentLoaded
    window.__ehGestor = ehGestor;
    window.__API_BASE = API_BASE;
});

// =============================================================================
// HELPERS INTERNOS DO MODAL
// =============================================================================

/** Alterna a visibilidade entre o painel de leitura (gestor) e o formulário (técnico) */
function _mostrarPainelLeitura(visivel) {
    const painel = document.getElementById("painel-visualizacao");
    const form   = document.getElementById("form-atividade");
    if (visivel) {
        painel.classList.remove("hidden");
        form.classList.add("hidden");
    } else {
        painel.classList.add("hidden");
        form.classList.remove("hidden");
    }
}

/** Preenche o painel de leitura com os dados da atividade retornados pela API */
function _preencherPainelVisualizacao(atv) {
    const API_BASE = window.__API_BASE || "http://127.0.0.1:8000/api/v1";

    // Dados principais
    document.getElementById("vis-tipo").textContent = atv.tipo_atividade || "—";
    document.getElementById("vis-safra").textContent = atv.nome_safra || `Safra #${atv.id_safra}`;
    document.getElementById("vis-responsavel").textContent = atv.responsavel || "Técnico Operador";
    document.getElementById("vis-data").textContent = atv.data_execucao
        ? new Date(atv.data_execucao).toLocaleDateString('pt-BR', { timeZone: 'UTC' })
        : "—";

    // Badge de status
    const badge = document.getElementById("vis-status-badge");
    badge.textContent = atv.status;
    badge.className = "px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ";
    if (atv.status === "Agendado")     badge.className += "bg-amber-50 text-amber-700 border-amber-200/60";
    else if (atv.status === "Em andamento") badge.className += "bg-blue-50 text-blue-700 border-blue-200/60";
    else if (atv.status === "Realizado")    badge.className += "bg-emerald-50 text-emerald-700 border-emerald-200/60";
    else badge.className += "bg-slate-100 text-slate-700 border-slate-200";

    // Oculta todos os blocos específicos antes de decidir quais mostrar
    document.getElementById("vis-bloco-irrigacao").classList.add("hidden");
    document.getElementById("vis-bloco-insumos").classList.add("hidden");
    document.getElementById("vis-praga-row").classList.add("hidden");
    document.getElementById("vis-nf-row").classList.add("hidden");
    document.getElementById("vis-receita-row").classList.add("hidden");
    document.getElementById("vis-sem-docs").classList.add("hidden");

    if (atv.tipo_atividade === "Irrigação") {
        document.getElementById("vis-bloco-irrigacao").classList.remove("hidden");
        document.getElementById("vis-lamina").textContent = atv.lamina_mm != null ? `${atv.lamina_mm} mm` : "—";
        document.getElementById("vis-horas").textContent = atv.horas_aplicacao != null ? `${atv.horas_aplicacao} h` : "—";
    }

    const tiposInsumo = ["Adubação", "Pulverização", "Manejo de pragas/doenças"];
    if (tiposInsumo.includes(atv.tipo_atividade)) {
        document.getElementById("vis-bloco-insumos").classList.remove("hidden");
        document.getElementById("vis-produto").textContent = atv.produto_usado || "—";
        document.getElementById("vis-qtd-ha").textContent = atv.quantidade_por_ha != null ? `${atv.quantidade_por_ha}` : "—";

        if (atv.tipo_atividade === "Manejo de pragas/doenças" && atv.praga_doenca_identificada) {
            document.getElementById("vis-praga-row").classList.remove("hidden");
            document.getElementById("vis-praga").textContent = atv.praga_doenca_identificada;
        }

        // Links de download dos arquivos
        // Token como query param: links <a target="_blank"> não enviam header Authorization.
        const tokenDownload = localStorage.getItem("agro_token") || "";
        let temDoc = false;

        if (atv.caminho_foto_nota_fiscal) {
            temDoc = true;
            document.getElementById("vis-nf-row").classList.remove("hidden");
            const nomeArquivoNf = atv.caminho_foto_nota_fiscal.split("/").pop() || "Nota Fiscal";
            document.getElementById("vis-nome-nf").textContent = `Nota Fiscal — ${nomeArquivoNf}`;
            document.getElementById("vis-link-nf").href =
                `${API_BASE}/atividades/${atv.id}/arquivo/nota_fiscal?token=${tokenDownload}`;
        }

        if (atv.caminho_foto_receita_agronomica) {
            temDoc = true;
            document.getElementById("vis-receita-row").classList.remove("hidden");
            const nomeArquivoRec = atv.caminho_foto_receita_agronomica.split("/").pop() || "Receita Agronômica";
            document.getElementById("vis-nome-receita").textContent = `Receita Agronômica — ${nomeArquivoRec}`;
            document.getElementById("vis-link-receita").href =
                `${API_BASE}/atividades/${atv.id}/arquivo/receita_agronomica?token=${tokenDownload}`;
        }

        if (!temDoc) {
            document.getElementById("vis-sem-docs").classList.remove("hidden");
        }
    }
}

// =============================================================================
// MÉTODOS GLOBAIS DO MODAL
// =============================================================================

/**
 * verAtividade — exclusivo para Gestor.
 * Busca os dados da atividade na API e exibe no painel de leitura (sem formulário).
 */
window.verAtividade = async function(id) {
    const tokenAtual = localStorage.getItem("agro_token");
    try {
        const res = await fetch(`${window.__API_BASE || "http://127.0.0.1:8000/api/v1"}/atividades/${id}`, {
            headers: { "Authorization": `Bearer ${tokenAtual}` }
        });
        if (!res.ok) throw new Error();
        const atv = await res.json();

        document.getElementById("modal-titulo").innerText = "Visualizar Atividade Agrícola";

        _preencherPainelVisualizacao(atv);
        _mostrarPainelLeitura(true);

        document.getElementById("modal-atividade").classList.remove("hidden");
    } catch (err) {
        window.exibirToast("Erro ao carregar dados da atividade.", "error");
    }
};

window.abrirModalAtividade = function() {
    if (window.__ehGestor) {
        window.exibirToast("Acesso negado. Apenas técnicos podem registrar atividades.", "error");
        return;
    }

    const form = document.getElementById("form-atividade");
    if (form) {
        form.reset();
        delete form.dataset.id;
    }

    liberarCamposFormulario(true);
    _mostrarPainelLeitura(false); // garante que o formulário está visível

    const divIrrigacao = document.getElementById("sub-irrigacao");
    const divInsumos   = document.getElementById("sub-insumos");
    const divPraga     = document.getElementById("div-praga");
    if (divIrrigacao) divIrrigacao.classList.add("hidden");
    if (divInsumos)   divInsumos.classList.add("hidden");
    if (divPraga)     divPraga.classList.add("hidden");

    const selectSafra = document.getElementById("id_safra");
    if (selectSafra) selectSafra.removeAttribute("disabled");

    const tokenAtual = localStorage.getItem("agro_token");
    fetch(`${window.__API_BASE || "http://127.0.0.1:8000/api/v1"}/safras/`, {
        headers: { "Authorization": `Bearer ${tokenAtual}` }
    }).then(res => res.json()).then(safras => {
        if (selectSafra) {
            selectSafra.innerHTML = '<option value="">-- Selecione uma Safra Operacional --</option>';
            safras.forEach(s => {
                if (s.status !== "Colhida/Finalizada") {
                    selectSafra.innerHTML += `<option value="${s.id}">${s.variedade_cultura} [Talhão: ${s.nome_talhao || s.id_talhao}]</option>`;
                }
            });
        }
    });

    const selectStatus = document.getElementById("status");
    if (selectStatus) {
        selectStatus.innerHTML = `
            <option value="Agendado">Agendado</option>
            <option value="Em andamento">Em andamento</option>
            <option value="Realizado">Realizado</option>
        `;
        selectStatus.disabled = false;
    }

    const btnSalvar = document.getElementById("btn-submit");
    if (btnSalvar) btnSalvar.classList.remove("hidden");

    document.getElementById("modal-titulo").innerText = "Registrar Nova Operação";
    document.getElementById("modal-atividade").classList.remove("hidden");
};

window.editarAtividade = async function(id) {
    const tokenAtual = localStorage.getItem("agro_token");
    try {
        const res = await fetch(`${window.__API_BASE || "http://127.0.0.1:8000/api/v1"}/atividades/${id}`, {
            headers: { "Authorization": `Bearer ${tokenAtual}` }
        });
        if (!res.ok) throw new Error();
        const atv = await res.json();

        const form = document.getElementById("form-atividade");
        form.dataset.id = id;

        _mostrarPainelLeitura(false); // garante que o formulário está visível
        document.getElementById("modal-titulo").innerText = "Editar Registro Operacional";

        const selectSafra = document.getElementById("id_safra");
        const resSafras = await fetch(`${window.__API_BASE || "http://127.0.0.1:8000/api/v1"}/safras/`, {
            headers: { "Authorization": `Bearer ${tokenAtual}` }
        });
        if (resSafras.ok && selectSafra) {
            const safras = await resSafras.json();
            selectSafra.innerHTML = '';
            safras.forEach(s => {
                const inativa = (s.status === "Colhida/Finalizada");
                if (!inativa || s.id === atv.id_safra) {
                    selectSafra.innerHTML += `<option value="${s.id}">${s.variedade_cultura} ${inativa ? '[SAFRA CONCLUÍDA]' : ''}</option>`;
                }
            });
            selectSafra.value = atv.id_safra;
        }

        document.getElementById("tipo_atividade").value = atv.tipo_atividade;
        document.getElementById("data_execucao").value  = atv.data_execucao;

        const divIrrigacao = document.getElementById("sub-irrigacao");
        const divInsumos   = document.getElementById("sub-insumos");
        const divPraga     = document.getElementById("div-praga");

        if (divIrrigacao) divIrrigacao.classList.add("hidden");
        if (divInsumos)   divInsumos.classList.add("hidden");
        if (divPraga)     divPraga.classList.add("hidden");

        if (atv.tipo_atividade === "Irrigação" && divIrrigacao)
            divIrrigacao.classList.remove("hidden");
        if (["Adubação", "Pulverização", "Manejo de pragas/doenças"].includes(atv.tipo_atividade) && divInsumos)
            divInsumos.classList.remove("hidden");
        if (atv.tipo_atividade === "Manejo de pragas/doenças" && divPraga)
            divPraga.classList.remove("hidden");

        if (atv.lamina_mm              && document.getElementById("lamina_mm"))              document.getElementById("lamina_mm").value              = atv.lamina_mm;
        if (atv.horas_aplicacao        && document.getElementById("horas_aplicacao"))        document.getElementById("horas_aplicacao").value        = atv.horas_aplicacao;
        if (atv.produto_usado          && document.getElementById("produto_usado"))          document.getElementById("produto_usado").value          = atv.produto_usado;
        if (atv.quantidade_por_ha      && document.getElementById("quantidade_por_ha"))      document.getElementById("quantidade_por_ha").value      = atv.quantidade_por_ha;
        if (atv.praga_doenca_identificada && document.getElementById("praga_doenca_identificada")) document.getElementById("praga_doenca_identificada").value = atv.praga_doenca_identificada;

        const selectStatus = document.getElementById("status");
        const btnSalvar    = document.getElementById("btn-submit");

        if (btnSalvar) btnSalvar.classList.remove("hidden");

        if (atv.status === "Em andamento") {
            liberarCamposFormulario(false);
            if (selectStatus) {
                selectStatus.innerHTML = `
                    <option value="Em andamento">Em andamento</option>
                    <option value="Realizado">✓ Mudar para Concluído</option>
                `;
                selectStatus.value    = "Em andamento";
                selectStatus.disabled = false;
            }
        } else {
            liberarCamposFormulario(true);
            if (selectStatus) {
                selectStatus.innerHTML = `
                    <option value="Agendado">Agendado</option>
                    <option value="Em andamento">Em andamento</option>
                    <option value="Realizado">Realizado</option>
                `;
                selectStatus.value    = atv.status;
                selectStatus.disabled = false;
            }
        }

        document.getElementById("modal-atividade").classList.remove("hidden");
    } catch (err) {
        window.exibirToast("Erro ao carregar dados da atividade.", "error");
    }
};

function liberarCamposFormulario(permitido) {
    const idSafra  = document.getElementById("id_safra");
    const tipoAtv  = document.getElementById("tipo_atividade");
    const dataExec = document.getElementById("data_execucao");

    if (!permitido) {
        if (idSafra)  idSafra.setAttribute("disabled", "true");
        if (tipoAtv)  tipoAtv.setAttribute("disabled", "true");
        if (dataExec) dataExec.setAttribute("disabled", "true");
        document.querySelectorAll("#sub-irrigacao input, #sub-insumos input, #div-praga input, #sub-irrigacao select, #sub-insumos select").forEach(el => {
            el.setAttribute("readonly", "true");
            el.setAttribute("disabled", "true");
        });
    } else {
        if (idSafra)  idSafra.removeAttribute("disabled");
        if (tipoAtv)  tipoAtv.removeAttribute("disabled");
        if (dataExec) dataExec.removeAttribute("disabled");
        document.querySelectorAll("#sub-irrigacao input, #sub-insumos input, #div-praga input, #sub-irrigacao select, #sub-insumos select").forEach(el => {
            el.removeAttribute("readonly");
            el.removeAttribute("disabled");
        });
    }
}

window.fecharModalAtividade = function() {
    document.getElementById("modal-atividade").classList.add("hidden");
    const form = document.getElementById("form-atividade");
    if (form) {
        form.reset();
        delete form.dataset.id;
    }
    // Restaura estado padrão: formulário visível (para próxima abertura pelo técnico)
    _mostrarPainelLeitura(false);
    liberarCamposFormulario(true);
};

window.excluirAtividade = async function(id) {
    if (window.__ehGestor) {
        window.exibirToast("Gestores não possuem permissão para excluir registros.", "error");
        return;
    }
    if (!confirm("Deseja realmente excluir esta atividade?")) return;
    const tokenAtual = localStorage.getItem("agro_token");
    try {
        const res = await fetch(`${window.__API_BASE || "http://127.0.0.1:8000/api/v1"}/atividades/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${tokenAtual}` }
        });
        if (res.ok) {
            window.exibirToast("Atividade removida com sucesso.", "success");
            location.reload();
        } else {
            window.exibirToast("Não foi possível excluir o registro.", "error");
        }
    } catch (e) {
        window.exibirToast("Erro de rede ao excluir.", "error");
    }
};

window.exibirToast = function(msg, tipo) {
    const alertBox = document.getElementById("alert-container");
    if (alertBox) {
        alertBox.className = `p-4 rounded-xl text-xs font-medium mb-4 ${tipo === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'}`;
        alertBox.innerHTML = msg;
        alertBox.classList.remove("hidden");
        setTimeout(() => alertBox.classList.add("hidden"), 5000);
    }
};