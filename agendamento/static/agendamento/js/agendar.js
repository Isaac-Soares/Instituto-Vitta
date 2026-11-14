/* ==========================================================================
   Instituto Vitta — Interação da tela de Agendar Consulta
   Controla a seleção de horários (pílulas), recarregamento dinâmico por data
   via API e habilita o botão de confirmação.
   ========================================================================== */

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("form-agendamento");
    const grade = document.getElementById("grade-horarios");
    const inputHorario = document.getElementById("id_horario_consulta");
    const inputData = document.getElementById("id_data_consulta");
    const resumo = document.getElementById("resumo-selecao");
    const textoResumo = document.getElementById("texto-horario-selecionado");
    const textoDataResumo = document.getElementById("texto-data-selecionada");
    const btnConfirmar = document.getElementById("btn-confirmar-agendamento");

    if (!grade) return;

    function formatarDataBR(isoDate) {
        if (!isoDate || !isoDate.includes("-")) return isoDate || "";
        const partes = isoDate.split("-");
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }

    function limparSelecao() {
        if (inputHorario) inputHorario.value = "";
        if (resumo) resumo.classList.add("d-none");
        if (btnConfirmar) btnConfirmar.disabled = true;
    }

    grade.addEventListener("click", function (evento) {
        const pilula = evento.target.closest(".horario-pill");
        if (!pilula || pilula.disabled) return;

        grade.querySelectorAll(".horario-pill.selecionado").forEach(function (el) {
            el.classList.remove("selecionado");
        });

        pilula.classList.add("selecionado");
        const hora = pilula.dataset.hora;
        inputHorario.value = hora;

        if (textoDataResumo && inputData) {
            textoDataResumo.textContent = formatarDataBR(inputData.value);
        }
        if (textoResumo) {
            textoResumo.textContent = hora;
        }
        if (resumo) {
            resumo.classList.remove("d-none");
        }
        if (btnConfirmar) {
            btnConfirmar.disabled = false;
        }
    });

    function renderizarHorarios(horarios, mensagem) {
        if (!horarios || horarios.length === 0) {
            const textoAviso = mensagem || "Nenhum horário disponível para a data selecionada.";
            grade.innerHTML = `
                <div class="col-12">
                    <div class="text-center py-4 px-3 bg-vitta-mint rounded-4">
                        <i class="bi bi-calendar-x text-vitta fs-3"></i>
                        <p class="mb-0 mt-2 section-subtitle">${textoAviso}</p>
                    </div>
                </div>
            `;
            return;
        }

        grade.innerHTML = horarios.map(function (h) {
            const ocupadoClass = h.ocupado ? "ocupado" : "";
            const disabledAttr = h.ocupado ? "disabled" : "";
            const titleAttr = h.motivo ? `title="${h.motivo}"` : "";
            return `
                <div class="col-4 col-sm-3 col-md-2">
                    <button type="button"
                            class="horario-pill ${ocupadoClass}"
                            data-hora="${h.hora}"
                            ${titleAttr}
                            ${disabledAttr}>
                        ${h.hora}
                    </button>
                </div>
            `;
        }).join("");
    }

    if (inputData) {
        inputData.addEventListener("change", function () {
            limparSelecao();
            const novaData = inputData.value;
            const apiUrl = form ? form.dataset.apiUrl : null;

            if (!novaData) {
                renderizarHorarios([], "Selecione uma data para ver os horários disponíveis.");
                return;
            }

            if (!apiUrl) return;

            grade.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div class="spinner-border text-vitta" role="status">
                        <span class="visually-hidden">Carregando horários...</span>
                    </div>
                    <p class="small section-subtitle mt-2 mb-0">Consultando disponibilidade...</p>
                </div>
            `;

            fetch(`${apiUrl}?data=${encodeURIComponent(novaData)}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" }
            })
                .then(function (resp) { return resp.json(); })
                .then(function (dados) {
                    renderizarHorarios(dados.horarios, dados.mensagem);
                })
                .catch(function () {
                    renderizarHorarios([], "Não foi possível carregar os horários. Tente novamente.");
                });
        });
    }
});
