/**
 * AgroGestor – relatorios.js
 * Relatório de Histórico de Safra (Linha do Tempo)
 */

const API_BASE = "http://127.0.0.1:8000/api/v1";

document.addEventListener("DOMContentLoaded", async () => {
    const token = localStorage.getItem("agro_token");
    if (!token) { window.location.href = "index.html"; return; }
    await carregarSafrasEncerradas();
});

// ─────────────────────────────────────────────────────────────────────────────
// Popula o select com safras Colhida/Finalizada
// ─────────────────────────────────────────────────────────────────────────────
async function carregarSafrasEncerradas() {
    const token = localStorage.getItem("agro_token");
    const sel = document.getElementById("sel-historico-safra");
    try {
        const resp = await fetch(`${API_BASE}/relatorios/safras-encerradas`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error("Falha ao buscar safras encerradas.");
        const safras = await resp.json();

        sel.innerHTML = "";
        if (safras.length === 0) {
            sel.innerHTML = `<option value="">Nenhuma safra encerrada disponível</option>`;
        } else {
            sel.innerHTML = `<option value="">Selecione uma safra...</option>`;
            safras.forEach(s => sel.appendChild(new Option(s.label, s.id)));
        }
    } catch (err) {
        sel.innerHTML = `<option value="">Erro ao carregar — verifique se a API está rodando</option>`;
        console.error(err);
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Visualizar relatório (JSON → tela)
// ─────────────────────────────────────────────────────────────────────────────
async function gerarRelatorioHistorico() {
    const token = localStorage.getItem("agro_token");
    const idSafra = document.getElementById("sel-historico-safra").value;

    if (!idSafra) { alert("Selecione uma safra encerrada."); return; }

    try {
        const resp = await fetch(`${API_BASE}/relatorios/historico/${idSafra}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao gerar relatório.");
        }
        const dados = await resp.json();
        renderizarHistorico(dados);

        // Habilita botão de PDF
        const btn = document.getElementById("btn-download-historico");
        btn.disabled = false;
        btn.classList.remove("bg-slate-100", "text-slate-400", "cursor-not-allowed");
        btn.classList.add("bg-rose-600", "hover:bg-rose-700", "text-white", "cursor-pointer");

    } catch (err) {
        alert(err.message);
    }
}

function renderizarHistorico(dados) {
    const { safra, linha_tempo, verificacao } = dados;

    // Dados gerais
    const grid = document.getElementById("grid-dados-gerais");
    const itens = [
        ["Talhão de cultivo",    safra.talhao],
        ["Variedade",            safra.variedade],
        ["Data de semeadura",    safra.data_semeadura_br],
        ["Data da colheita",     safra.data_colheita_br],
        ["Duração do ciclo",     `${safra.duracao_dias} dias`],
        ["Produtividade obtida", safra.produtividade_safra != null ? `${safra.produtividade_safra} sc/ha` : "—"],
    ];
    grid.innerHTML = itens.map(([k, v]) => `
        <div class="bg-slate-50 rounded-lg border border-slate-100 px-3 py-2">
            <p class="text-[9px] font-mono text-slate-400 uppercase">${k}</p>
            <p class="font-semibold text-slate-800 text-xs mt-0.5">${_esc(String(v))}</p>
        </div>
    `).join("");

    // Linha do tempo
    const lista = document.getElementById("lista-timeline");
    if (linha_tempo.length === 0) {
        lista.innerHTML = `<p class="text-[11px] text-slate-400">Nenhuma atividade ou evento registrado para esta safra.</p>`;
    } else {
        lista.innerHTML = linha_tempo.map((ev, i) => {
            const isEvento = ev.origem === "evento_extremo";
            const isLast   = i === linha_tempo.length - 1;

            const comprovantes = [];
            if (ev.tem_nota_fiscal) comprovantes.push(
                `<span class="inline-flex items-center gap-1 text-[10px] bg-blue-50 text-blue-700 border border-blue-200 px-1.5 py-0.5 rounded"><i class="bi bi-receipt"></i> NF</span>`
            );
            if (ev.tem_receita) comprovantes.push(
                `<span class="inline-flex items-center gap-1 text-[10px] bg-purple-50 text-purple-700 border border-purple-200 px-1.5 py-0.5 rounded"><i class="bi bi-file-medical"></i> Receita</span>`
            );

            return `
                <div class="timeline-item relative ${isEvento ? "evento" : ""}">
                    ${!isLast ? '<div class="timeline-line"></div>' : ""}
                    <div class="flex items-start justify-between gap-3">
                        <div>
                            <p class="text-xs font-semibold ${isEvento ? "text-rose-700" : "text-slate-800"}">${_esc(ev.tipo)}</p>
                            <p class="text-[11px] text-slate-500 mt-0.5">${_esc(ev.detalhes)}</p>
                            <p class="text-[10px] text-slate-400 mt-1">Responsável: ${_esc(ev.responsavel)}</p>
                        </div>
                        <div class="text-right shrink-0">
                            <p class="text-[11px] font-mono text-slate-600">${ev.data_br}</p>
                            <div class="flex gap-1 mt-1 justify-end">${comprovantes.join("")}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join("");
    }

    // QR Code via serviço público (sem dependência JS adicional)
    document.getElementById("qr-historico").src =
        `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(verificacao.url)}`;
    document.getElementById("link-historico-autenticidade").href = verificacao.url;

    // Exibe resultado e esconde estado vazio
    document.getElementById("estado-vazio").classList.add("hidden");
    document.getElementById("resultado-historico").classList.remove("hidden");
}

// ─────────────────────────────────────────────────────────────────────────────
// Baixar PDF
// ─────────────────────────────────────────────────────────────────────────────
function baixarRelatorioHistorico() {
    const token   = localStorage.getItem("agro_token");
    const idSafra = document.getElementById("sel-historico-safra").value;
    if (!idSafra) return;
    window.open(`${API_BASE}/relatorios/historico/${idSafra}/pdf?token=${encodeURIComponent(token)}`, "_blank");
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────────────────────────────────────
function _esc(str) {
    const d = document.createElement("div");
    d.textContent = str ?? "—";
    return d.innerHTML;
}
