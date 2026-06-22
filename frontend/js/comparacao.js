/**
 * AgroGestor – comparacao.js
 * Relatório Comparativo de Produtividade e Duração de Ciclos (RFS16)
 *
 * Conectado à API real do backend (substitui o mock original).
 * Segue a mesma lógica de QR Code e página de autenticidade do
 * Relatório de Histórico de Safra, com código HMAC gerado no servidor.
 */

const API_BASE = "http://127.0.0.1:8000/api/v1";

let safrasDisponiveis = [];
let safrasSelecionadasIds = [];

// ─────────────────────────────────────────────────────────────────────────────
// Inicialização — verifica login e carrega safras encerradas da API
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem("agro_token");
    if (!token) { window.location.href = "index.html"; return; }
    await carregarSafrasEncerradas();
});

async function carregarSafrasEncerradas() {
    const token = localStorage.getItem("agro_token");
    const container = document.getElementById('selector-container');

    try {
        const resp = await fetch(`${API_BASE}/relatorios/safras-encerradas`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error("Falha ao buscar safras encerradas.");
        safrasDisponiveis = await resp.json();

        if (safrasDisponiveis.length === 0) {
            container.innerHTML = `<p class="text-xs text-slate-400">Nenhuma safra encerrada disponível para comparação.</p>`;
            return;
        }

        inicializarFiltros();

    } catch (err) {
        console.error(err);
        container.innerHTML = `<p class="text-xs text-red-500">Erro ao carregar safras. Verifique se a API está rodando.</p>`;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Inicializa os checkboxes de seleção de safra (dados reais da API)
// ─────────────────────────────────────────────────────────────────────────────
function inicializarFiltros() {
    const container = document.getElementById('selector-container');
    container.innerHTML = '';

    safrasDisponiveis.forEach(safra => {
        const label = document.createElement('label');
        label.className = "safra-label flex items-center gap-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-3 py-2.5 rounded-lg cursor-pointer transition-all";
        label.innerHTML = `
            <input type="checkbox" value="${safra.id}" class="safra-checkbox h-3.5 w-3.5 accent-emerald-700 rounded">
            <div>
                <p class="text-xs font-semibold text-slate-800">${_esc(safra.label)}</p>
                <p class="text-[10px] text-slate-400 font-mono">${safra.produtividade_safra ?? "—"} sc/ha</p>
            </div>
        `;
        container.appendChild(label);
    });

    document.querySelectorAll('.safra-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const checked = document.querySelectorAll('.safra-checkbox:checked');
            // RN09 — limite de 5 safras por relatório
            if (checked.length > 5) {
                e.target.checked = false;
                alert("Limite máximo atingido. É permitido comparar até 5 safras por relatório.");
                return;
            }
            safrasSelecionadasIds = Array.from(checked).map(c => parseInt(c.value));
            const n = checked.length;
            document.getElementById('counter-msg').textContent =
                n === 0 ? "Nenhuma safra selecionada." : `${n} de 5 safras selecionadas.`;
        });
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Gera a matriz comparativa e a linha do tempo a partir da API
// ─────────────────────────────────────────────────────────────────────────────
async function gerarComparativo() {
    const token = localStorage.getItem("agro_token");

    if (safrasSelecionadasIds.length < 2) {
        alert("Selecione ao menos 2 safras para comparar.");
        return;
    }

    try {
        const resp = await fetch(`${API_BASE}/relatorios/comparativo?ids=${safrasSelecionadasIds.join(",")}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || "Erro ao gerar relatório comparativo.");
        }
        const dados = await resp.json();
        renderizarComparativo(dados);

    } catch (err) {
        alert(err.message);
    }
}

function renderizarComparativo(dados) {
    const { safras, alerta_variedades, alerta_mensagem, verificacao } = dados;

    // ── Alerta de variedades distintas (RN11) ──────────────────────────
    let alertaEl = document.getElementById('alerta-variedades');
    if (!alertaEl) {
        // Cria o bloco de alerta dinamicamente se ainda não existir no HTML
        alertaEl = document.createElement('div');
        alertaEl.id = 'alerta-variedades';
        alertaEl.className = "hidden bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 text-[11px] text-amber-800 flex items-start gap-2";
        alertaEl.innerHTML = `<i class="bi bi-exclamation-triangle-fill mt-0.5"></i><span id="texto-alerta-variedades"></span>`;
        document.getElementById('resultado-comparacao').prepend(alertaEl);
    }
    if (alerta_variedades) {
        document.getElementById('texto-alerta-variedades').textContent = alerta_mensagem;
        alertaEl.classList.remove('hidden');
    } else {
        alertaEl.classList.add('hidden');
    }

    // ── Identifica a safra de maior produtividade ──────────────────────
    const produtividades = safras.map(s => s.produtividade_safra ?? 0);
    const maiorProd = Math.max(...produtividades);
    const melhorId  = safras.find(s => (s.produtividade_safra ?? 0) === maiorProd)?.id;

    // ── Cabeçalho da tabela ──────────────────────────────────────────────
    const headerRow = document.getElementById('table-header');
    headerRow.innerHTML = '<th class="px-4 py-3 border-r border-slate-200 w-44">Indicador</th>';

    safras.forEach(safra => {
        const th = document.createElement('th');
        th.className = "px-4 py-3 border-r border-slate-200 text-center min-w-[160px]";
        if (safra.id === melhorId) {
            th.innerHTML = `
                <span class="font-semibold text-slate-700">${_esc(safra.talhao)}</span><br>
                <span class="inline-block mt-1 px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-[9px] font-semibold uppercase tracking-wide">★ Melhor Desempenho</span>
            `;
        } else {
            th.innerHTML = `<span class="font-semibold text-slate-700">${_esc(safra.talhao)}</span>`;
        }
        headerRow.appendChild(th);
    });

    // ── Linhas da tabela ─────────────────────────────────────────────────
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    const indicadores = [
        { label: "Variedade",        key: "variedade" },
        { label: "Semeadura",        key: "data_semeadura_br" },
        { label: "Colheita Real",    key: "data_colheita_br" },
        { label: "Duração do Ciclo", key: "duracao_dias", sufixo: " dias" },
        { label: "Produtividade",    key: "produtividade_safra", sufixo: " sc/ha" }
    ];

    indicadores.forEach((ind, i) => {
        const tr = document.createElement('tr');
        const bgRow = i % 2 === 0 ? '' : 'bg-slate-50/60';
        let cells = `<td class="px-4 py-3 border-r border-slate-200 font-medium text-slate-600 ${bgRow}">${ind.label}</td>`;

        safras.forEach(safra => {
            let valor = safra[ind.key] ?? "—";
            if (ind.sufixo && valor !== "—") valor += ind.sufixo;
            const destaque = (safra.id === melhorId && ind.key === 'produtividade_safra')
                ? 'font-bold text-emerald-700' : '';
            cells += `<td class="px-4 py-3 text-center border-r border-slate-100 ${bgRow} ${destaque}">${_esc(String(valor))}</td>`;
        });

        tr.innerHTML = cells;
        tbody.appendChild(tr);
    });

    // ── Linha do tempo consolidada ──────────────────────────────────────
    const timelineBody = document.getElementById('timeline-body');
    timelineBody.innerHTML = '';

    const todosEventos = [];
    safras.forEach(safra => {
        (safra.linha_tempo || []).forEach(evt => {
            todosEventos.push({ ...evt, safraTalhao: safra.talhao });
        });
    });
    todosEventos.sort((a, b) => (a.data || "").localeCompare(b.data || ""));

    if (todosEventos.length === 0) {
        timelineBody.innerHTML = `<tr><td colspan="4" class="px-4 py-6 text-center text-slate-400 text-xs">Nenhuma atividade ou evento registrado nas safras selecionadas.</td></tr>`;
    } else {
        todosEventos.forEach(evt => {
            const tr = document.createElement('tr');
            const isExtremo = evt.origem === "evento_extremo";
            const badgeClass = isExtremo
                ? "bg-red-100 text-red-700 border border-red-200"
                : "bg-blue-50 text-blue-700 border border-blue-200";
            const rowClass = isExtremo ? "bg-red-50/40" : "hover:bg-slate-50/50";

            tr.className = rowClass;
            tr.innerHTML = `
                <td class="px-4 py-3 whitespace-nowrap font-mono text-[11px] text-slate-500">${evt.data_br}</td>
                <td class="px-4 py-3">
                    <p class="font-semibold text-slate-800 text-[11px]">${_esc(evt.safraTalhao)}</p>
                    <p class="text-[10px] text-slate-400 font-mono">${_esc(evt.responsavel || "—")}</p>
                </td>
                <td class="px-4 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase font-semibold tracking-wide ${badgeClass}">
                        ${isExtremo ? '<i class="bi bi-exclamation-triangle-fill mr-1"></i>' : ''}${_esc(evt.tipo)}
                    </span>
                </td>
                <td class="px-4 py-3 text-slate-600 text-[11px]">${_esc(evt.detalhes)}</td>
            `;
            timelineBody.appendChild(tr);
        });
    }

    // ── QR Code de autenticidade — código HMAC vindo do backend ────────
    document.getElementById('qr-comparativo').src =
        `https://api.qrserver.com/v1/create-qr-code/?size=160x160&data=${encodeURIComponent(verificacao.url)}`;
    document.getElementById('link-autenticidade').href = verificacao.url;

    // ── Exibe resultado ──────────────────────────────────────────────────
    document.getElementById('estado-vazio').classList.add('hidden');
    document.getElementById('resultado-comparacao').classList.remove('hidden');
    document.getElementById('btn-pdf').classList.remove('hidden');
    document.getElementById('resultado-comparacao').scrollIntoView({ behavior: 'smooth' });
}

// ─────────────────────────────────────────────────────────────────────────────
// Baixar PDF — usa o endpoint do backend (ReportLab), não html2pdf
// Mantém consistência visual com o PDF do Histórico de Safra
// ─────────────────────────────────────────────────────────────────────────────
function baixarPDF() {
    const token = localStorage.getItem("agro_token");
    if (safrasSelecionadasIds.length < 2) return;

    const url = `${API_BASE}/relatorios/comparativo/pdf?ids=${safrasSelecionadasIds.join(",")}&token=${encodeURIComponent(token)}`;
    window.open(url, "_blank");
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────────────────────────────────────
function _esc(str) {
    const d = document.createElement("div");
    d.textContent = str ?? "—";
    return d.innerHTML;
}

// ─────────────────────────────────────────────────────────────────────────────
// Listeners
// ─────────────────────────────────────────────────────────────────────────────
document.getElementById('btn-comparar').addEventListener('click', gerarComparativo);
document.getElementById('btn-pdf').addEventListener('click', baixarPDF);
