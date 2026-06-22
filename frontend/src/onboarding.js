const STORAGE_KEY = "kernel_onboarding_dismissed_v1";

/**
 * Banner único para novos utilizadores — 3 passos, dispensável.
 */
export function initOnboarding() {
    try {
        if (localStorage.getItem(STORAGE_KEY) === "1") return;
    } catch {
        return;
    }

    const anchor = document.querySelector(".input-area");
    if (!anchor) return;

    const banner = document.createElement("aside");
    banner.className = "onboarding-banner";
    banner.setAttribute("role", "region");
    banner.setAttribute("aria-label", "Como usar o Kernel");

    banner.innerHTML = `
        <div class="onboarding-banner__body">
            <p class="onboarding-banner__title">Primeira vez aqui?</p>
            <ol class="onboarding-banner__steps">
                <li>Escolha a <strong>matéria</strong> no botão de grade à esquerda.</li>
                <li>Escreva sua dúvida — <kbd>Enter</kbd> envia.</li>
                <li>Confira as <strong>fontes</strong> abaixo de cada resposta.</li>
            </ol>
        </div>
        <button type="button" class="onboarding-banner__dismiss">Entendi</button>
    `;

    anchor.insertAdjacentElement("beforebegin", banner);

    banner.querySelector(".onboarding-banner__dismiss")?.addEventListener("click", () => {
        try {
            localStorage.setItem(STORAGE_KEY, "1");
        } catch {
            /* ignora */
        }
        banner.remove();
    });
}
