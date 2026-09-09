(() => {
  const STATES = ["active", "success", "warning", "error", "waiting"];

  class FlowPlayer {
    constructor(element) {
      this.element = element;
      this.scenario = JSON.parse(element.querySelector(".flow-player__scenario").textContent);
      this.source = element.querySelector(".flow-player__mermaid").textContent;
      this.currentStep = -1;
      this.playing = false;
      this.timer = null;
      this.svg = null;
      this.bindControls();
    }

    async init() {
      if (!window.mermaid) {
        this.fail("Mermaid is not available");
        return;
      }
      window.mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });
      const renderId = `flow-player-${this.scenario.id}-${Math.random().toString(36).slice(2)}`;
      const { svg } = await window.mermaid.render(renderId, this.source);
      this.element.querySelector(".flow-player__canvas").innerHTML = svg;
      this.svg = this.element.querySelector("svg");
      this.render();
    }

    bindControls() {
      this.element.querySelectorAll("[data-action]").forEach((button) => {
        button.addEventListener("click", () => this[button.dataset.action]());
      });
    }

    next() {
      if (this.currentStep < this.scenario.steps.length - 1) {
        this.currentStep += 1;
        this.render(true);
      } else {
        this.pause();
      }
    }

    previous() {
      this.pause();
      if (this.currentStep >= 0) this.currentStep -= 1;
      this.render(false);
    }

    reset() {
      this.pause();
      this.currentStep = -1;
      this.render(false);
    }

    play() {
      if (this.playing) {
        this.pause();
        return;
      }
      if (this.currentStep >= this.scenario.steps.length - 1) this.currentStep = -1;
      this.playing = true;
      this.updatePlayButton();
      this.next();
      this.scheduleNext();
    }

    pause() {
      this.playing = false;
      window.clearTimeout(this.timer);
      this.timer = null;
      this.updatePlayButton();
    }

    scheduleNext() {
      if (!this.playing) return;
      const delay = this.scenario.settings?.step_duration ?? 1500;
      this.timer = window.setTimeout(() => {
        this.next();
        this.scheduleNext();
      }, delay);
    }

    render(animate) {
      if (!this.svg) return;
      this.clearVisualState();
      for (let index = 0; index <= this.currentStep; index += 1) {
        this.applyStep(this.scenario.steps[index], animate && index === this.currentStep);
      }
      this.renderDetails();
      this.updateButtons();
    }

    clearVisualState() {
      this.svg.querySelectorAll(".flow-state-active,.flow-state-success,.flow-state-warning,.flow-state-error,.flow-state-waiting")
        .forEach((node) => STATES.forEach((state) => node.classList.remove(`flow-state-${state}`)));
      this.element.querySelectorAll(".flow-traveller").forEach((item) => item.remove());
    }

    applyStep(step, animate) {
      if (step.node) {
        const node = this.findNode(step.node);
        if (node) node.classList.add(`flow-state-${step.state ?? "active"}`);
      } else if (step.edge && animate && step.action === "travel") {
        this.animateEdge(step.edge.from, step.edge.to);
      }
    }

    findNode(id) {
      return this.svg.querySelector(`[id^="flowchart-${CSS.escape(id)}-"]`)
        || this.svg.querySelector(`[data-id="${CSS.escape(id)}"]`);
    }

    findEdge(from, to) {
      return this.svg.querySelector(`[id^="L_${CSS.escape(from)}_${CSS.escape(to)}_"]`);
    }

    animateEdge(from, to) {
      const path = this.findEdge(from, to);
      if (!path || typeof path.getTotalLength !== "function") return;
      const marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      marker.setAttribute("r", "6");
      marker.setAttribute("class", "flow-traveller");
      path.parentNode.appendChild(marker);
      const length = path.getTotalLength();
      const started = performance.now();
      const duration = Math.min(this.scenario.settings?.step_duration ?? 1500, 1200);
      const frame = (now) => {
        if (!marker.isConnected) return;
        const progress = Math.min((now - started) / duration, 1);
        const point = path.getPointAtLength(length * progress);
        marker.setAttribute("cx", point.x);
        marker.setAttribute("cy", point.y);
        if (progress < 1) requestAnimationFrame(frame);
        else marker.remove();
      };
      requestAnimationFrame(frame);
    }

    renderDetails() {
      const step = this.scenario.steps[this.currentStep];
      this.element.querySelector(".flow-player__counter").textContent = step
        ? `Step ${this.currentStep + 1}/${this.scenario.steps.length}` : "Ready";
      this.element.querySelector(".flow-player__step-title").textContent = step?.title ?? "Select Next to start";
      this.element.querySelector(".flow-player__description").textContent = step?.description ?? "";
      const payload = this.element.querySelector(".flow-player__payload");
      payload.hidden = !step?.payload;
      payload.textContent = step?.payload ? JSON.stringify(step.payload, null, 2) : "";
    }

    updateButtons() {
      this.element.querySelector('[data-action="previous"]').disabled = this.currentStep < 0;
      this.element.querySelector('[data-action="next"]').disabled = this.currentStep >= this.scenario.steps.length - 1;
    }

    updatePlayButton() {
      this.element.querySelector('[data-action="play"]').textContent = this.playing ? "Pause" : "Play";
    }

    fail(message) {
      this.element.classList.add("flow-player--invalid");
      this.element.querySelector(".flow-player__canvas").textContent = message;
    }
  }

  const initialize = () => {
    document.querySelectorAll(".flow-player").forEach((element) => {
      if (element.dataset.initialized) return;
      element.dataset.initialized = "true";
      new FlowPlayer(element).init().catch((error) => {
        element.querySelector(".flow-player__canvas").textContent = `Flow rendering failed: ${error.message}`;
      });
    });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
  if (typeof document$ !== "undefined") document$.subscribe(initialize);
})();

