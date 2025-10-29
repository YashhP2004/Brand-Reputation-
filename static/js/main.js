document.addEventListener('DOMContentLoaded', () => {
    const companyList = document.getElementById('company-list');
    const searchInput = document.getElementById('search-input');
    const newCompanyForm = document.getElementById('new-company-form');
    const companyNameInput = document.getElementById('company-name-input');
    const keywordsInput = document.getElementById('keywords-input');
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loader-text');

    let companies = [];
    let analysisInterval;

    // Fetch and display companies
    const fetchCompanies = async () => {
        try {
            const response = await fetch('/api/companies');
            companies = await response.json();
            displayCompanies(companies);
        } catch (error) {
            console.error('Error fetching companies:', error);
            companyList.innerHTML = '<p>Could not load companies.</p>';
        }
    };

    // Display companies
    const displayCompanies = (companiesToDisplay) => {
        companyList.innerHTML = '';
        if (companiesToDisplay.length === 0) {
            companyList.innerHTML = '<p>No companies found. Analyze a new one to get started!</p>';
            return;
        }
        companiesToDisplay.forEach(company => {
            const card = document.createElement('div');
            card.className = 'company-card';
            card.innerHTML = `<h3>${company.display_name}</h3>`;
            card.addEventListener('click', () => {
                window.location.href = `/dashboard/${company.id}`;
            });
            companyList.appendChild(card);
        });
    };

    // Search functionality
    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filteredCompanies = companies.filter(company =>
            company.display_name.toLowerCase().includes(searchTerm)
        );
        displayCompanies(filteredCompanies);
    });

    // --- NEW: Polling function to check analysis status ---
    const checkAnalysisStatus = (companyId, companyName) => {
        analysisInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/analysis_status/${companyId}`);
                const data = await response.json();

                if (data.status === 'complete') {
                    clearInterval(analysisInterval);
                    loaderText.textContent = `Analysis complete! Redirecting to dashboard...`;
                    window.location.href = `/dashboard/${companyId}`;
                } else {
                    // Still pending, keep loader text as is.
                    console.log(`Analysis for ${companyName} is still pending...`);
                }
            } catch (error) {
                console.error('Error checking analysis status:', error);
                clearInterval(analysisInterval);
                loaderText.textContent = 'Error checking status. Please refresh and check the list.';
            }
        }, 5000); // Check every 5 seconds
    };

    // Handle new company analysis form
    newCompanyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const companyName = companyNameInput.value.trim();
        const keywords = keywordsInput.value;

        loaderText.textContent = `Starting analysis for ${companyName}... This may take several minutes.`;
        loader.classList.remove('hidden');

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company_name: companyName, keywords: keywords })
            });

            const result = await response.json();

            if (response.status === 202) { // Analysis started
                checkAnalysisStatus(result.company_id, companyName);
            } else if (response.status === 200) { // Already done
                 loaderText.textContent = `Analysis recently completed! Redirecting...`;
                 window.location.href = `/dashboard/${result.company_id}`;
            }
            else {
                alert(`Error: ${result.error || 'Something went wrong.'}`);
                loader.classList.add('hidden');
            }
        } catch (error) {
            console.error('Error starting analysis:', error);
            alert('An error occurred. Check the console for details.');
            loader.classList.add('hidden');
        }
    });

    // Initial fetch
    fetchCompanies();
});