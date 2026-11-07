// Financial calculators (loan EMI, interest, mortgage, ROI).

const CURRENCY_SYMBOL = '$';     // change to '₹', '€', ... - the maths does not depend on it

function formatMoney(amount) {
    const sign = amount < 0 ? '-' : '';
    const text = Math.abs(amount).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return `${sign}${CURRENCY_SYMBOL}${text}`;
}

function formatPercent(value) {
    return `${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

// Read a number input. Returns NaN for empty / invalid fields.
function readNumber(id) {
    const text = document.getElementById(id).value.trim();
    return text === '' ? NaN : Number(text);
}

// Show "Label: value" rows (built with textContent, so nothing is interpreted as HTML).
function showRows(elementId, rows) {
    const box = document.getElementById(elementId);
    box.classList.remove('error');
    box.replaceChildren(...rows.map(([label, value]) => {
        const row = document.createElement('div');
        row.className = 'result-row';
        const name = document.createElement('span');
        name.textContent = label;
        const amount = document.createElement('strong');
        amount.textContent = value;
        row.append(name, amount);
        return row;
    }));
}

function showError(elementId, message) {
    const box = document.getElementById(elementId);
    box.classList.add('error');
    box.textContent = message;
}

// Wire one calculator: validate -> call API -> show result.
function setupFinancialForm(name, run) {
    const resultId = `${name}-result`;
    document.querySelector(`.btn-calculate[data-calc="${name}"]`).addEventListener('click', async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
            await run(resultId);
            loadHistory();
        } catch (err) {
            showError(resultId, err.message);
        } finally {
            button.disabled = false;
        }
    });
}

function requireNumbers(...values) {
    if (values.some(v => !Number.isFinite(v))) throw new Error('Please fill in every field with a valid number');
}

function requireWhole(value, label) {
    if (!Number.isInteger(value)) throw new Error(`${label} must be a whole number`);
}

// ---- sub-tabs ----------------------------------------------------------
document.querySelectorAll('.financial-tab-btn').forEach((button) => {
    button.addEventListener('click', () => {
        document.querySelectorAll('.financial-tab-btn').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        document.querySelectorAll('.financial-calc').forEach(c => c.classList.remove('active'));
        document.getElementById(`${button.dataset.calc}-calc`).classList.add('active');
    });
});

// ---- Loan (EMI) --------------------------------------------------------
setupFinancialForm('loan', async (resultId) => {
    const principal = readNumber('loan-principal');
    const rate = readNumber('loan-rate');
    const term = readNumber('loan-term');
    requireNumbers(principal, rate, term);
    requireWhole(term, 'Term (months)');

    const result = await calculateLoan(principal, rate, term);
    showRows(resultId, [
        ['Monthly EMI', formatMoney(result.emi)],
        ['Total Payment', formatMoney(result.total_payment)],
        ['Total Interest', formatMoney(result.total_interest)],
    ]);
});

// ---- Simple / compound interest ----------------------------------------
const interestTypeSelect = document.getElementById('interest-type');
interestTypeSelect.addEventListener('change', () => {
    document.getElementById('compounding-group').hidden = interestTypeSelect.value !== 'compound';
});

setupFinancialForm('interest', async (resultId) => {
    const principal = readNumber('interest-principal');
    const rate = readNumber('interest-rate');
    const time = readNumber('interest-time');
    const type = interestTypeSelect.value;
    const compounds = Number(document.getElementById('interest-compounding').value);
    requireNumbers(principal, rate, time);

    const result = await calculateInterest(principal, rate, time, type, compounds);
    showRows(resultId, [
        ['Interest Earned', formatMoney(result.interest)],
        ['Total Amount', formatMoney(result.total_amount)],
    ]);
});

// ---- Mortgage ----------------------------------------------------------
setupFinancialForm('mortgage', async (resultId) => {
    const price = readNumber('mortgage-price');
    const down = readNumber('mortgage-down');
    const rate = readNumber('mortgage-rate');
    const term = readNumber('mortgage-term');
    requireNumbers(price, down, rate, term);
    requireWhole(term, 'Loan term (years)');

    const result = await calculateMortgage(price, down, rate, term);
    showRows(resultId, [
        ['Loan Amount', formatMoney(result.loan_amount)],
        ['Monthly Payment', formatMoney(result.monthly_payment)],
        ['Total Payment', formatMoney(result.total_payment)],
        ['Total Interest', formatMoney(result.total_interest)],
    ]);
});

// ---- ROI ---------------------------------------------------------------
setupFinancialForm('roi', async (resultId) => {
    const initial = readNumber('roi-initial');
    const final = readNumber('roi-final');
    requireNumbers(initial, final);

    const result = await calculateROI(initial, final);
    showRows(resultId, [
        ['Profit / Loss', formatMoney(result.profit)],
        ['ROI', formatPercent(result.roi_percentage)],
    ]);
});
