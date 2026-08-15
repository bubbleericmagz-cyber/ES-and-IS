/* Dashboard charts, using the Guavoco colour palette.
 *
 * The numbers come from the Django view and are placed in the page inside a
 * <script id="chart-data" type="application/json"> tag, so no data is hardcoded
 * here.
 *
 * Each chart is a single measure, so the card title names it and no legend box
 * is needed. On the order status chart every bar is labelled on its own axis,
 * so the colours group the stages (in progress / completed / cancelled) rather
 * than being the only way to tell the bars apart.
 */

(function () {
    const dataTag = document.getElementById('chart-data');
    if (!dataTag || typeof Chart === 'undefined') {
        return;
    }
    const data = JSON.parse(dataTag.textContent);

    /* ---- Guavoco palette ---- */
    const PRIMARY = '#3F5A1A';   // deep Guavoco green
    const SECONDARY = '#6E8B2C'; // fresh leaf green
    const SAGE = '#A8B39A';      // soft botanical sage
    const GUAVA = '#F27F6A';     // guava coral, used sparingly
    const PRIMARY_FILL = 'rgba(63, 90, 26, 0.08)';

    /* ---- Neutrals ---- */
    const TEXT_PRIMARY = '#26311F';
    const TEXT_MUTED = '#87917F';
    const GRID = '#E5E8E0';
    const SURFACE = '#FFFFFF';

    /* Order statuses grouped by what they mean, in the order the view sends
       them: Pending, Processing, Ready for Distribution, Distributed,
       Delivered, Cancelled. */
    const ORDER_STATUS_COLOURS = [
        SECONDARY,  // Pending               - in progress
        SECONDARY,  // Processing            - in progress
        SECONDARY,  // Ready for Distribution - in progress
        SECONDARY,  // Distributed           - in progress
        PRIMARY,    // Delivered             - completed
        GUAVA       // Cancelled             - needs attention
    ];

    Chart.defaults.font.family =
        "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
    Chart.defaults.font.size = 11.5;
    Chart.defaults.color = TEXT_MUTED;

    // Shared look: recessive grid, no legend, a clean tooltip on hover.
    function baseOptions(extra) {
        return Object.assign({
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: SURFACE,
                    titleColor: TEXT_PRIMARY,
                    bodyColor: TEXT_PRIMARY,
                    borderColor: GRID,
                    borderWidth: 1,
                    padding: 10,
                    cornerRadius: 8,
                    displayColors: false
                }
            }
        }, extra || {});
    }

    function verticalScales(unitLabel) {
        return {
            x: {
                grid: { display: false },
                border: { color: GRID },
                ticks: { maxRotation: 0, autoSkipPadding: 12 }
            },
            y: {
                beginAtZero: true,
                grid: { color: GRID, drawTicks: false },
                border: { display: false },
                title: { display: true, text: unitLabel, color: TEXT_MUTED }
            }
        };
    }

    function horizontalScales(unitLabel) {
        return {
            x: {
                beginAtZero: true,
                grid: { color: GRID, drawTicks: false },
                border: { display: false },
                title: { display: true, text: unitLabel, color: TEXT_MUTED },
                ticks: { precision: 0 }
            },
            y: {
                grid: { display: false },
                border: { color: GRID },
                ticks: { color: TEXT_PRIMARY }
            }
        };
    }

    function drawChart(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (canvas) {
            new Chart(canvas, config);
        }
    }

    // 1. Units packaged per day
    drawChart('packagingChart', {
        type: 'bar',
        data: {
            labels: data.packaging.labels,
            datasets: [{
                label: 'Units packaged',
                data: data.packaging.values,
                backgroundColor: SECONDARY,
                borderRadius: 4,
                borderSkipped: 'bottom',
                borderColor: SURFACE,
                borderWidth: { top: 0, left: 1, right: 1, bottom: 0 },
                maxBarThickness: 26
            }]
        },
        options: baseOptions({ scales: verticalScales('Units') })
    });

    // 2. Current inventory per product
    drawChart('inventoryChart', {
        type: 'bar',
        data: {
            labels: data.inventory.labels,
            datasets: [{
                label: 'Units in stock',
                data: data.inventory.values,
                backgroundColor: PRIMARY,
                borderRadius: 4,
                borderSkipped: 'left',
                maxBarThickness: 30
            }]
        },
        options: baseOptions({
            indexAxis: 'y',
            scales: horizontalScales('Units available')
        })
    });

    // 3. How many orders sit at each status
    drawChart('orderStatusChart', {
        type: 'bar',
        data: {
            labels: data.orders.labels,
            datasets: [{
                label: 'Orders',
                data: data.orders.values,
                backgroundColor: ORDER_STATUS_COLOURS,
                borderRadius: 4,
                borderSkipped: 'left',
                maxBarThickness: 22
            }]
        },
        options: baseOptions({
            indexAxis: 'y',
            scales: horizontalScales('Number of orders')
        })
    });

    // 4. Units distributed per day
    drawChart('distributionChart', {
        type: 'line',
        data: {
            labels: data.distribution.labels,
            datasets: [{
                label: 'Units distributed',
                data: data.distribution.values,
                borderColor: PRIMARY,
                backgroundColor: PRIMARY_FILL,
                borderWidth: 2,
                fill: true,
                tension: 0.25,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: PRIMARY,
                pointBorderColor: SURFACE,
                pointBorderWidth: 2
            }]
        },
        options: baseOptions({
            interaction: { mode: 'index', intersect: false },
            scales: verticalScales('Units')
        })
    });

    // SAGE is kept available for any additional series added later.
    void SAGE;
})();
