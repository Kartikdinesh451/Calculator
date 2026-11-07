// History panel (stored on the server in SQLite).

async function loadHistory() {
    try {
        const data = await getHistory();
        renderHistory(data.history);
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function renderHistory(history) {
    const list = document.getElementById('history-list');
    list.replaceChildren();

    if (history.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'history-empty';
        empty.textContent = 'No calculations yet';
        list.append(empty);
        return;
    }

    history.forEach((item) => {
        const row = document.createElement('div');
        row.className = 'history-item';
        row.title = new Date(item.timestamp).toLocaleString();

        // textContent (not innerHTML): history text is never interpreted as HTML.
        const expression = document.createElement('div');
        expression.className = 'history-expression';
        const isMath = item.calculator_type === 'basic' || item.calculator_type === 'scientific';
        expression.textContent = isMath ? calculator.pretty(item.expression) : item.expression;

        const result = document.createElement('div');
        result.className = 'history-result';
        result.textContent = `= ${item.result}`;
        row.append(expression, result);

        // Only plain numeric answers can be loaded back into the calculator.
        const isNumber = /^-?\d+(\.\d+)?(e[+-]\d+)?$/.test(item.result);
        if (isNumber && isMath) {
            row.addEventListener('click', () => recallResult(item));
        } else {
            row.classList.add('not-recallable');
        }
        list.append(row);
    });
}

function recallResult(item) {
    // Switch to the tab the calculation came from, then load the answer to keep calculating.
    const mode = item.calculator_type === 'scientific' ? 'scientific' : 'basic';
    if (calculator.mode !== mode) {
        document.querySelector(`.tab-btn[data-mode="${mode}"]`).click();
    }
    calculator.reset();
    calculator.expression = item.result;
    calculator.resultText = item.result;
    calculator.historyLine = `${calculator.pretty(item.expression.replace(/\s+\[(deg|rad)\]$/, ''))} =`;
    calculator.justEvaluated = true;
    calculator.render();
}

document.getElementById('clear-history').addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear all history?')) return;
    try {
        await clearHistory();
        loadHistory();
    } catch (error) {
        alert('Failed to clear history: ' + error.message);
    }
});

document.getElementById('export-history').addEventListener('click', async () => {
    try {
        const data = await getHistory();
        if (data.history.length === 0) {
            alert('No history to export');
            return;
        }
        const blob = new Blob([JSON.stringify(data.history, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'calculator_history.json';
        document.body.append(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('Failed to export history: ' + error.message);
    }
});

document.addEventListener('DOMContentLoaded', loadHistory);
