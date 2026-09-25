document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector("[data-log-search]");
    const rows = Array.from(document.querySelectorAll("[data-log-row]"));
    const emptyState = document.querySelector("[data-empty-filter]");

    if (!searchInput || rows.length === 0) return;

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        let visibleCount = 0;

        rows.forEach((row) => {
            const searchValue = (row.dataset.searchValue || "").toLowerCase();
            const visible = searchValue.includes(query);
            row.hidden = !visible;
            if (visible) visibleCount += 1;
        });

        if (emptyState) {
            emptyState.hidden = visibleCount !== 0;
        }
    });
});
