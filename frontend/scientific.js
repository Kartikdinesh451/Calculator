// Scientific-only behaviour. (The old version of this file replaced calculator.calculate()
// for ALL modes, which is what broke the basic calculator.) Nothing here overrides core logic.

// DEG <-> RAD toggle: flip the flag in the calculator and update the button label.
calculator.toggleAngleMode = function toggleAngleMode() {
    this.isDegree = !this.isDegree;
    const button = document.getElementById('deg-rad');
    button.textContent = this.isDegree ? 'DEG' : 'RAD';
    button.classList.toggle('active-mode', !this.isDegree);
};
