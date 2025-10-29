document.addEventListener('DOMContentLoaded', async () => {
    // --- Helper Functions ---
    const fetchData = async (endpoint) => {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching from ${endpoint}:`, error);
            return null;
        }
    };

    const renderChartMessage = (containerId, message) => {
        const container = document.getElementById(containerId);
        if(container) container.innerHTML = `<p class="chart-message">${message}</p>`;
    };
    
    // --- Chart Rendering Functions ---

    // 1. Sentiment Chart (Horizontal Bar)
    const renderSentimentChart = async () => {
        const data = await fetchData(`/api/sentiment/${companyId}`);
        const canvas = document.getElementById('sentiment-chart');
        if (!data || !canvas || (data.positive === 0 && data.neutral === 0 && data.negative === 0)) {
            renderChartMessage(canvas.parentElement.id, 'No sentiment data available.');
            return;
        }

        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Positive', 'Neutral', 'Negative'],
                datasets: [{
                    label: 'Mention Count',
                    data: [data.positive, data.neutral, data.negative],
                    backgroundColor: ['#2ECC71', '#F1C40F', '#E74C3C'],
                    borderColor: ['#27AE60', '#F39C12', '#C0392B'],
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { beginAtZero: true } }
            }
        });
    };
    
    // 2. Word Cloud (FIXED)
    const renderWordCloud = async () => {
        const data = await fetchData(`/api/keywords/${companyId}`);
        const container = document.getElementById('word-cloud');
        if (!data || data.length === 0) {
            renderChartMessage('word-cloud', 'No keywords extracted.');
            return;
        }
        
        // Scale keywords by count (from extracted_keywords.csv: keyword,count)
        const maxCount = Math.max(...data.map(d => parseFloat(d.count) || 0), 1);
        const minSize = 12;
        const maxSize = 60;
        const words = data.map(d => {
            const count = parseFloat(d.count);
            const size = isNaN(count) ? minSize : (minSize + (count / maxCount) * (maxSize - minSize));
            return { text: d.keyword, size };
        });

        const layout = d3.layout.cloud()
            .size([container.clientWidth, container.clientHeight])
            .words(words)
            .padding(5)
            .rotate(() => Math.random() > 0.5 ? 0 : 90) // More dynamic rotation
            .fontSize(d => d.size)
            .on("end", draw);
        layout.start();

        function draw(words) {
            // Clear previous SVG to prevent overlapping
            d3.select(container).html(""); 
            
            d3.select(container).append("svg")
                .attr("width", layout.size()[0])
                .attr("height", layout.size()[1])
                .append("g")
                .attr("transform", `translate(${layout.size()[0] / 2},${layout.size()[1] / 2})`)
                .selectAll("text").data(words).enter().append("text")
                .style("font-size", d => d.size + "px")
                .style("font-family", "Poppins")
                .style("fill", (d, i) => d3.schemeCategory10[i % 10])
                .attr("text-anchor", "middle")
                .attr("transform", d => `translate(${d.x}, ${d.y})rotate(${d.rotate})`)
                .text(d => d.text);
        }
    };
    
    // 3. Treemap
    const renderTreemap = async () => {
        const data = await fetchData(`/api/themes/${companyId}`);
        const container = document.getElementById('treemap');
        if (!data || data.length === 0) {
            renderChartMessage('treemap', 'No perception themes available.');
            return;
        }
        
        const themeCounts = data.reduce((acc, theme) => {
            acc[theme] = (acc[theme] || 0) + 1;
            return acc;
        }, {});
        const root = { name: "themes", children: Object.entries(themeCounts).map(([name, value]) => ({ name, value })) };

        const treemapLayout = d3.treemap().size([container.clientWidth, container.clientHeight]).padding(2);
        const nodes = d3.hierarchy(root).sum(d => d.value);
        treemapLayout(nodes);
        
        const svg = d3.select(container).append("svg").attr("width", "100%").attr("height", "100%");
        const cell = svg.selectAll("g").data(nodes.leaves()).enter().append("g")
            .attr("transform", d => `translate(${d.x0},${d.y0})`);
        
        const color = d3.scaleOrdinal(d3.schemeTableau10);
        cell.append("rect")
            .attr("width", d => d.x1 - d.x0)
            .attr("height", d => d.y1 - d.y0)
            .attr("fill", d => color(d.data.name));
        cell.append("text").selectAll("tspan")
            .data(d => d.data.name.split(/(?=[A-Z][^A-Z])/g))
            .enter().append("tspan")
            .attr("x", 4).attr("y", (d, i) => 13 + i * 10)
            .text(d => d).attr("font-size", "12px").attr("fill", "white");
    };

    // 4. Data Tables
    const renderTable = async (source) => {
        const data = await fetchData(`/api/${source}/${companyId}`);
        const container = document.getElementById(`${source}-table`);
        if (!data || data.length === 0) {
             renderChartMessage(container.id, `No mentions found from ${source}.`);
             return;
        }
        
        const headers = Object.keys(data[0]);
        let tableHTML = '<table><thead><tr>';
        headers.forEach(h => tableHTML += `<th>${h}</th>`);
        tableHTML += '</tr></thead><tbody>';

        data.slice(0, 100).forEach(row => { // Limit to 100 rows for performance
            tableHTML += '<tr>';
            headers.forEach(h => {
                let cell = row[h] || '';
                // Make links clickable
                if (typeof cell === 'string' && cell.startsWith('http')) {
                    cell = `<a href="${cell}" target="_blank" rel="noopener noreferrer">Link</a>`;
                }
                tableHTML += `<td>${cell}</td>`;
            });
            tableHTML += '</tr>';
        });
        tableHTML += '</tbody></table>';
        container.innerHTML = tableHTML;
    };
    
    // --- Initial Load ---
    renderSentimentChart();
    renderWordCloud();
    renderTreemap();
    renderTable('news');
    renderTable('reddit');
    renderTable('twitter');
});