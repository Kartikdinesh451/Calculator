// Calculator controller (basic + scientific).
//
// The old version kept "previous number / operator / current number" state and tried to
// calculate after every operator. That broke chained calculations (an un-awaited async call
// raced with the next key) and, worse, scientific.js replaced calculate() for *every* mode so
// "3 + 5" sent only "5" to the server.
//
// Now the calculator just builds ONE expression string ("2+3×4"), shows it, and sends the
// whole thing to the server when "=" is pressed. The server does the maths (with correct
// precedence), so there is nothing to get out of sync.

const OPERATORS = '+-*/%^';
const FUNCTION_TOKEN = /(?:asin|acos|atan|sin|cos|tan|log|ln|sqrt|cbrt|abs|exp)\($/;

class Calculator {
    constructor() {
        this.expressionEl = document.getElementById('input-display');
        this.resultEl = document.getElementById('result-display');
        this.mode = 'basic';        // 'basic' | 'scientific' | 'financial'
        this.isDegree = true;
        this.busy = false;
        this.reset();
    }

    // ---- state -----------------------------------------------------------
    reset() {
        this.expression = '';       // what the user is typing, with ASCII operators (* / -)
        this.resultText = '';       // last answer
        this.historyLine = '';      // "2+3 =" shown above the answer
        this.error = '';
        this.justEvaluated = false;
        this.render();
    }

    setMode(mode) {
        this.mode = mode;
        this.reset();
    }

    get isScientific() {
        return this.mode === 'scientific';
    }

    // ---- helpers ---------------------------------------------------------
    // Called before the user types something that starts a *new* calculation.
    _startNewIfNeeded() {
        this.error = '';
        if (this.justEvaluated) {
            this.expression = '';
            this.justEvaluated = false;
        }
        this.resultText = '';
        this.historyLine = '';
    }

    // Called before an operator / backspace: keep working with the current answer.
    _continue() {
        this.error = '';
        this.justEvaluated = false;
        this.resultText = '';
        this.historyLine = '';
    }

    _lastChar() {
        return this.expression.slice(-1);
    }

    // After ')', '!' or a constant, a digit/constant/function needs an explicit '×'
    // (so "2" then "e" is "2×e", never the number "2e").
    _needsMultiply() {
        return /[0-9.)!πe]$/.test(this.expression);
    }

    _isOperator(ch) {
        return ch !== '' && OPERATORS.includes(ch);
    }

    _openParens() {
        return (this.expression.match(/\(/g) || []).length - (this.expression.match(/\)/g) || []).length;
    }

    // ---- key handlers ----------------------------------------------------
    appendDigit(digit) {
        this._startNewIfNeeded();
        if (/[πe)!]$/.test(this.expression)) {
            this.expression += '*';
        }
        // "0" followed by a digit replaces the zero (no "007"), but "0.5" and "10" are kept.
        if (/(^|[^0-9.])0$/.test(this.expression)) {
            this.expression = this.expression.slice(0, -1);
        }
        this.expression += digit;
        this.render();
    }

    appendDecimal() {
        this._startNewIfNeeded();
        if (/[πe)!]$/.test(this.expression)) {
            this.expression += '*';
        }
        const trailingNumber = this.expression.match(/[0-9.]*$/)[0];
        if (trailingNumber.includes('.')) return;           // already has a decimal point
        this.expression += trailingNumber === '' ? '0.' : '.';
        this.render();
    }

    appendOperator(op) {
        if (op === '^' && !this.isScientific) return;
        this._continue();
        let expr = this.expression;
        const last = this._lastChar();

        if (expr === '') {
            // Nothing typed yet: "-" starts a negative number, anything else works on 0.
            expr = op === '-' ? '-' : (op === '+' ? '' : `0${op}`);
        } else if (last === '(') {
            if (op === '-') expr += '-';                    // "(-5"
        } else if (this._isOperator(last)) {
            const beforeLast = expr.slice(-2, -1);
            const alreadyUnary = this._isOperator(beforeLast);
            if (op === '-' && '*/^%'.includes(last) && !alreadyUnary) {
                expr += '-';                                // "5*-3"
            } else {
                // replace the trailing operator(s): "5+" then "*" -> "5*"
                const base = expr.replace(/[+\-*\/%^]+$/, '');
                expr = base === '' || base.endsWith('(') ? (op === '-' ? `${base}-` : base) : base + op;
            }
        } else {
            expr += op;
        }
        this.expression = expr;
        this.render();
    }

    appendFunction(name) {
        this._startNewIfNeeded();
        this.expression += name;                            // e.g. "sin(" - server handles 2sin(30)
        this.render();
    }

    appendConstant(symbol) {
        this._startNewIfNeeded();
        if (this._needsMultiply()) this.expression += '*';
        this.expression += symbol;
        this.render();
    }

    appendPostfix(text) {                                   // "!" and "^2"
        if (!this.isScientific) return;
        this._continue();
        if (/[0-9)πe!]$/.test(this.expression)) {
            this.expression += text;
            this.render();
        }
    }

    openParen() {
        this._startNewIfNeeded();
        this.expression += '(';
        this.render();
    }

    closeParen() {
        this._continue();
        if (this._openParens() > 0 && /[0-9.)πe!]$/.test(this.expression)) {
            this.expression += ')';
            this.render();
        }
    }

    backspace() {
        if (this.error) {                                   // first backspace just dismisses the message
            this.error = '';
            this.render();
            return;
        }
        this._continue();
        if (FUNCTION_TOKEN.test(this.expression)) {
            this.expression = this.expression.replace(FUNCTION_TOKEN, '');
        } else {
            this.expression = this.expression.slice(0, -1);
        }
        this.render();
    }

    clear() {
        this.reset();
    }

    toggleAngleMode() {                                     // overridden/extended in scientific.js
        this.isDegree = !this.isDegree;
    }

    // ---- evaluate --------------------------------------------------------
    // What gets sent to the server: no dangling operator, all parentheses closed.
    _expressionToSend() {
        let expr = this.expression;
        let previous;
        do {                                                // "5+sin(" -> "5"
            previous = expr;
            expr = expr.replace(/[+\-*\/%^]+$/, '')
                       .replace(/(?:asin|acos|atan|sin|cos|tan|log|ln|sqrt|cbrt|abs|exp)?\($/, '');
        } while (expr !== previous);
        const missing = (expr.match(/\(/g) || []).length - (expr.match(/\)/g) || []).length;
        return missing > 0 ? expr + ')'.repeat(missing) : expr;
    }

    async calculate() {
        if (this.busy || this.mode === 'financial') return;
        const expression = this._expressionToSend();
        if (expression === '') return;

        this.busy = true;
        try {
            const data = this.isScientific
                ? await calculateScientific(expression, this.isDegree)
                : await calculateBasic(expression);

            this.historyLine = `${this.pretty(expression)} =`;
            this.resultText = data.result;
            this.expression = data.result;                  // keep going from the answer
            this.error = '';
            this.justEvaluated = true;
            loadHistory();
        } catch (err) {
            this.error = err.message;                       // keep the expression so it can be fixed
        } finally {
            this.busy = false;
            this.render();
        }
    }

    // ---- display ---------------------------------------------------------
    pretty(expr) {
        return expr.replace(/\*/g, '×').replace(/\//g, '÷').replace(/-/g, '−').replace(/%/g, ' mod ');
    }

    render() {
        this.expressionEl.textContent = this.historyLine || this.pretty(this.expression);
        const shown = this.error || this.resultText || (this.expression === '' ? '0' : '');
        this.resultEl.textContent = shown;
        this.resultEl.classList.toggle('error', Boolean(this.error));
    }
}

const calculator = new Calculator();

// ---- clicks: one delegated listener for every calculator button ----------
document.querySelector('.calculator-container').addEventListener('click', (event) => {
    const button = event.target.closest('button[data-kind]');
    if (!button) return;
    const value = button.dataset.value;

    switch (button.dataset.kind) {
        case 'digit':     calculator.appendDigit(value); break;
        case 'decimal':   calculator.appendDecimal(); break;
        case 'operator':  calculator.appendOperator(value); break;
        case 'function':  calculator.appendFunction(value); break;
        case 'constant':  calculator.appendConstant(value); break;
        case 'postfix':   calculator.appendPostfix(value); break;
        case 'open':      calculator.openParen(); break;
        case 'close':     calculator.closeParen(); break;
        case 'backspace': calculator.backspace(); break;
        case 'clear':     calculator.clear(); break;
        case 'equals':    calculator.calculate(); break;
        case 'degrad':    calculator.toggleAngleMode(); break;
    }
});

// ---- mode tabs ------------------------------------------------------------
document.querySelectorAll('.tab-btn').forEach((button) => {
    button.addEventListener('click', () => {
        const mode = button.dataset.mode;
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        document.querySelectorAll('.calculator-mode').forEach(panel => panel.classList.remove('active'));
        document.getElementById(`${mode}-mode`).classList.add('active');
        document.getElementById('display').hidden = (mode === 'financial');
        calculator.setMode(mode);
    });
});

// ---- keyboard -------------------------------------------------------------
document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    // Typing in the financial form fields must not drive the calculator.
    if (event.target.closest && event.target.closest('input, select, textarea')) return;
    if (calculator.mode === 'financial') return;
    // Enter on a focused tab / Clear / Export button should keep its normal meaning.
    if (event.key === 'Enter' && event.target.matches && event.target.matches('button') &&
        !event.target.closest('.button-grid')) return;

    const key = event.key;
    let handled = true;

    if (key >= '0' && key <= '9' && key.length === 1) {
        calculator.appendDigit(key);
    } else if (key === '.' || key === ',') {
        calculator.appendDecimal();
    } else if (['+', '-', '*', '/', '%'].includes(key)) {
        calculator.appendOperator(key);
    } else if (key === '^') {
        calculator.appendOperator('^');
    } else if (key === '!' && calculator.isScientific) {
        calculator.appendPostfix('!');
    } else if (key === '(') {
        calculator.openParen();
    } else if (key === ')') {
        calculator.closeParen();
    } else if (key === 'Enter' || key === '=') {
        calculator.calculate();
    } else if (key === 'Backspace') {
        calculator.backspace();
    } else if (key === 'Escape' || key === 'Delete') {
        calculator.clear();
    } else {
        handled = false;
    }
    if (handled) event.preventDefault();   // also stops Enter from "clicking" the focused button twice
});

// After a mouse click, drop focus from non-keypad buttons so a later Enter means "equals".
document.addEventListener('click', (event) => {
    const button = event.target.closest && event.target.closest('button');
    if (button && event.detail > 0 && !button.closest('.button-grid')) button.blur();
});
