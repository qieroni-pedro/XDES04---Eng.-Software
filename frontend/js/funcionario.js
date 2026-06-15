const URL_API_USUARIOS = "http://127.0.0.1:8000/api/v1/usuarios";

document.addEventListener("DOMContentLoaded", () => {
    carregarEquipe();

    document.getElementById("form-funcionario").addEventListener("submit", (e) => {
        e.preventDefault();
        salvarDadosFuncionario();
    });
});

async function carregarEquipe() {
    const token = localStorage.getItem("agro_token");
    const idFazenda = localStorage.getItem("user_fazenda_id");

    if (!token || !idFazenda) {
        window.location.href = "index.html";
        return;
    }

    try {
        const resposta = await fetch(`${URL_API_USUARIOS}/listar?id_fazenda=${idFazenda}`, {
            method: "GET",
            headers: { 
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (!resposta.ok) {
            const erroApi = await resposta.json().catch(() => ({}));
            throw new Error(erroApi.detail || "Falha na leitura dos dados de RH.");
        }

        const dados = await resposta.json();
        renderizarTabelaEquipe(dados);
    } catch (err) {
        console.error(err);
        alert(err.message);
    }
}

function renderizarTabelaEquipe(lista) {
    const tbody = document.getElementById("tbody-funcionarios");
    tbody.innerHTML = "";

    if (lista.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-slate-400 font-mono text-[11px]">Nenhum técnico agrícola associado a esta fazenda atualmente.</td></tr>`;
        return;
    }

    lista.forEach(func => {
        const dataFormatada = new Date(func.data_criacao).toLocaleDateString("pt-BR");
        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50/50 transition-all";

        tr.innerHTML = `
            <td class="px-6 py-4 font-semibold text-slate-800">${func.nome}</td>
            <td class="px-6 py-4 font-mono text-slate-600">${func.email}</td>
            <td class="px-6 py-4">
                <span class="inline-flex items-center bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border border-blue-200/50 font-mono">
                    ${func.papel}
                </span>
            </td>
            <td class="px-6 py-4 text-slate-500 font-mono">${dataFormatada}</td>
            <td class="px-6 py-4">
                <button onclick="removerTecnico(${func.id})" class="text-red-600 hover:text-red-800 cursor-pointer transition-all">
                    <i class="bi bi-trash3-fill"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function abrirModalCadastro() {
    document.getElementById("form-funcionario").reset();
    document.getElementById("modal-funcionario").classList.remove("hidden");
}

function fecharModal() {
    document.getElementById("modal-funcionario").classList.add("hidden");
}

async function salvarDadosFuncionario() {
    const token = localStorage.getItem("agro_token");
    const idFazenda = localStorage.getItem("user_fazenda_id");

    const payload = {
        nome: document.getElementById("txt-nome").value,
        email: document.getElementById("txt-email").value,
        senha_inicial: document.getElementById("txt-senha").value,
        id_fazenda: parseInt(idFazenda)
    };

    try {
        const resposta = await fetch(`${URL_API_USUARIOS}/cadastrar`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        if (!resposta.ok) {
            const erroApi = await resposta.json().catch(() => ({}));
            throw new Error(erroApi.detail || "Erro interno ao salvar colaborador.");
        }

        fecharModal();
        carregarEquipe();
    } catch (err) {
        alert(err.message);
    }
}

// Função para deletar o vínculo do funcionário com a fazenda
async function removerTecnico(idUsuario) {
    if (!confirm("Deseja realmente remover este integrante da equipe?")) return;

    const token = localStorage.getItem("agro_token");
    const idFazenda = localStorage.getItem("user_fazenda_id");

    try {
        const resposta = await fetch(`${URL_API_USUARIOS}/desvincular/${idUsuario}?id_fazenda=${idFazenda}`, {
            method: "DELETE",
            headers: { 
                "Authorization": `Bearer ${token}` 
            }
        });

        if (!resposta.ok) {
            const erroApi = await resposta.json().catch(() => ({}));
            throw new Error(erroApi.detail || "Não foi possível remover o funcionário.");
        }

        carregarEquipe();
    } catch (err) {
        alert(err.message);
    }
}