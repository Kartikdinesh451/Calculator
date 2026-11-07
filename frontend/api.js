// API layer: one small helper, one function per endpoint.

// Served by the FastAPI app itself (http://localhost:8000)  -> same-origin "/api".
// Opened from file:// or another dev server (e.g. :8080)    -> talk to http://localhost:8000.
// Override from the console / a script tag with: window.CALCULATOR_API_URL = 'https://host/api'
const API_BASE_URL = window.CALCULATOR_API_URL ||
    ((location.protocol === 'http:' || location.protocol === 'https:') &&
        (location.port === '8000' || location.port === '')
        ? '/api'
        : 'http://localhost:8000/api');

// Turn FastAPI's error body into one readable sentence.
function extractErrorMessage(data, status) {
    if (data && typeof data.detail === 'string') return data.detail;
    if (data && Array.isArray(data.detail) && data.detail.length) {
        // 422 validation errors: [{loc: ['body','rate'], msg: '...'}]
        return data.detail
            .map(e => {
                const field = Array.isArray(e.loc) ? e.loc.filter(p => p !== 'body').join(' ') : '';
                return field ? `${field}: ${e.msg}` : e.msg;
            })
            .join('; ');
    }
    return `Request failed (HTTP ${status})`;
}

async function apiRequest(path, options = {}) {
    let response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, options);
    } catch (networkError) {
        throw new Error('Cannot reach the server. Start the backend: uvicorn main:app --reload');
    }

    let data = null;
    try {
        data = await response.json();
    } catch (parseError) {
        data = null;
    }

    if (!response.ok) {
        throw new Error(extractErrorMessage(data, response.status));
    }
    return data;
}

function postJSON(path, body) {
    return apiRequest(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
}

// Basic / scientific -------------------------------------------------------
function calculateBasic(expression) {
    return postJSON('/calculator/calculate', { expression });
}

function calculateScientific(expression, isDegree = true) {
    return postJSON('/scientific/calculate', { expression, is_degree: isDegree });
}

// Financial ----------------------------------------------------------------
function calculateLoan(principal, rate, term) {
    return postJSON('/financial/loan', { principal, rate, term });
}

function calculateInterest(principal, rate, time, type, compoundsPerYear = 1) {
    return postJSON('/financial/interest', {
        principal, rate, time, type, compounds_per_year: compoundsPerYear,
    });
}

function calculateMortgage(price, downPayment, rate, term) {
    return postJSON('/financial/mortgage', { price, down_payment: downPayment, rate, term });
}

function calculateROI(initialInvestment, finalValue) {
    return postJSON('/financial/roi', { initial_investment: initialInvestment, final_value: finalValue });
}

// History ------------------------------------------------------------------
function getHistory() {
    return apiRequest('/history/');
}

function clearHistory() {
    return apiRequest('/history/', { method: 'DELETE' });
}
