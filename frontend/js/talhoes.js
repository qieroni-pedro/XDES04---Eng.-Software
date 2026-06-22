const URL_API_TALHOES = "http://127.0.0.1:8000/api/v1/talhoes";

document.addEventListener("DOMContentLoaded", () => {
    // Garante travas RBAC de interface visual
    aplicarRestricoesRBAC();
    
    // Dispara a carga de dados protegida
    carregarTalhoes();

    document.getElementById("form-talhao").addEventListener("submit", (e) => {
        e.preventDefault();
        salvarDadosTalhao();
    });
});

function aplicarRestricoesRBAC() {
    const perfil = localStorage.getItem("user_perfil");
    // RFS01 - Apenas o gestor insere talhão. O botão some para o Técnico
    if (perfil !== "Gestor") {
        const btnNovo = document.getElementById("btn-novo-talhao");
        if (btnNovo) btnNovo.classList.add("hidden");
    }
}

async function carregarTalhoes() {
    const token = localStorage.getItem("agro_token");
    
    // Travamento preventivo caso o cliente esteja sem credenciais válidas na sessão
    if (!token) {
        console.warn("[Auth] Token ausente. Redirecionando para a raiz.");
        window.location.href = "index.html";
        return;
    }

    const nome = document.getElementById("filtro-nome").value;
    const areaMin = document.getElementById("filtro-area-min").value;
    const areaMax = document.getElementById("filtro-area-max").value;

    // Monta query params para os filtros do RFS03
    let urlCompleta = `${URL_API_TALHOES}/?`;
    if (nome) urlCompleta += `nome=${encodeURIComponent(nome)}&`;
    if (areaMin) urlCompleta += `area_min=${areaMin}&`;
    if (areaMax) urlCompleta += `area_max=${areaMax}&`;

    try {
        const resposta = await fetch(urlCompleta, {
            method: "GET",
            headers: { 
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        // Captura respostas de erro explícitas do FastAPI (401, 403, 500)
        if (!resposta.ok) {
            const erroCorpo = await resposta.json().catch(() => ({}));
            throw new Error(erroCorpo.detail || `Erro do Servidor (Status ${resposta.status})`);
        }

        const dados = await resposta.json();
        renderizarGradeTalhoes(dados);
    } catch (err) {
        console.error("[Erro na requisição]", err);
        // Exibe o erro real enviado pelo back-end
        alert(`Falha na listagem: ${err.message}`);
    }
}

function renderizarGradeTalhoes(lista) {
    const tbody = document.getElementById("tbody-talhoes");
    const perfil = localStorage.getItem("user_perfil");
    tbody.innerHTML = "";

    if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-slate-400 font-mono text-[11px]">Nenhum talhão ativo foi localizado para os parâmetros informados.</td></tr>`;
        return;
    }

    lista.forEach(t => {
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50/50 transition-all";

        // RFS04 - Apenas Gestor pode deletar talhões
        const btnDeletar = perfil === "Gestor" 
            ? `<button onclick="solicitarRemocaoLogica(${t.id})" class="text-slate-400 hover:text-red-600 px-2 py-1 transition-all cursor-pointer" title="Remover"><i class="bi bi-trash3"></i></button>`
            : ``;

        tr.innerHTML = `
            <td class="px-6 py-4 font-semibold text-slate-800">${t.nome}</td>
            <td class="px-6 py-4 font-mono text-slate-600">${t.area_ha.toFixed(2)} ha</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded text-[11px] font-medium border border-slate-200/60">
                    ${t.tipo_solo}
                </span>
            </td>
            <td class="px-6 py-4 text-right space-x-1">
                <button onclick="abrirModalEdicao(${t.id}, '${t.nome}', ${t.area_ha}, '${t.tipo_solo}')" class="text-slate-400 hover:text-emerald-700 px-2 py-1 transition-all cursor-pointer" title="Editar"><i class="bi bi-pencil-square"></i></button>
                ${btnDeletar}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function abrirModalCadastro() {
    document.getElementById("form-talhao").reset();
    document.getElementById("txt-id").value = "";
    document.getElementById("modal-titulo").textContent = "Inserir Talhão";
    document.getElementById("modal-talhao").classList.remove("hidden");
}

function abrirModalEdicao(id, nome, area, solo) {
    document.getElementById("txt-id").value = id;
    document.getElementById("txt-nome").value = nome;
    document.getElementById("txt-area").value = area;
    document.getElementById("cmb-solo").value = solo;
    document.getElementById("modal-titulo").textContent = "Editar Talhão";
    document.getElementById("modal-talhao").classList.remove("hidden");
}

function fecharModal() {
    document.getElementById("modal-talhao").classList.add("hidden");
}

async function salvarDadosTalhao() {
    const token = localStorage.getItem("agro_token");
    const id = document.getElementById("txt-id").value;

    const dadosForm = {
        nome: document.getElementById("txt-nome").value,
        area_ha: parseFloat(document.getElementById("txt-area").value),
        tipo_solo: document.getElementById("cmb-solo").value
    };

    const url = id ? `${URL_API_TALHOES}/${id}` : URL_API_TALHOES;
    const metodoHTTP = id ? "PUT" : "POST";

    try {
        const resposta = await fetch(url, {
            method: metodoHTTP,
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(dadosForm)
        });

        if (!resposta.ok) {
            const erroApi = await resposta.json().catch(() => ({}));
            throw new Error(erroApi.detail || "Erro interno ao submeter formulário.");
        }

        fecharModal();
        carregarTalhoes();
    } catch (err) {
        alert(err.message);
    }
}

async function solicitarRemocaoLogica(id) {
    if (!confirm("Confirmar a remoção lógica deste talhão do ecossistema da fazenda?")) return;

    const token = localStorage.getItem("agro_token");

    try {
        const resposta = await fetch(`${URL_API_TALHOES}/${id}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!resposta.ok) {
            const erroApi = await resposta.json().catch(() => ({}));
            throw new Error(erroApi.detail || "Falha ao processar exclusão.");
        }

        carregarTalhoes();
    } catch (err) {
        alert(err.message);
    }
}