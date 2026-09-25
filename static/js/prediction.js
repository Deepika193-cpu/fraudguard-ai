document.addEventListener("DOMContentLoaded", () => {
    const stepInput = document.querySelector("[data-step-input]");
    const dayPreview = document.querySelector("[data-preview-day]");
    const hourPreview = document.querySelector("[data-preview-hour]");
    const form = document.querySelector("[data-prediction-form]");

    const updateTimePreview = () => {
        if (!stepInput || !dayPreview || !hourPreview) return;

        const parsedStep = Number.parseInt(stepInput.value, 10);
        const step = Number.isFinite(parsedStep) && parsedStep >= 1 ? parsedStep : 1;
        const day = Math.floor((step - 1) / 24) + 1;
        const hour = (step - 1) % 24;

        dayPreview.textContent = `Day ${day}`;
        hourPreview.textContent = `${String(hour).padStart(2, "0")}:00`;
    };

    stepInput?.addEventListener("input", updateTimePreview);
    updateTimePreview();

    form?.addEventListener("submit", (event) => {
        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        form.classList.add("is-submitting");
        const submitButton = form.querySelector("button[type='submit']");
        if (submitButton) submitButton.disabled = true;
    });
});
