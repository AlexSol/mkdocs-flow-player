(() => {
  "use strict";
  const STATES = ["active", "success", "warning", "error", "waiting"];
  let renderSequence = 0;
  let mermaidConfigured = false;

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  class FlowPlayer {
    constructor(element, clock = {
      now: () => performance.now(),
      request: (callback) => requestAnimationFrame(callback),
      cancel: (id) => cancelAnimationFrame(id),
    }) {
      this.element = element;
      this.clock = clock;
      this.scenario = JSON.parse(element.querySelector(".flow-player__scenario").textContent);
      this.source = JSON.parse(element.querySelector(".flow-player__mermaid").textContent);
      this.currentStep = -1;
      this.playing = false;
      this.elapsed = 0;
      this.frame = null;
      this.lastTime = null;
      this.marker = null;
      this.svg = null;
      this.ready = false;
      this.duration = this.scenario.settings?.step_duration ?? 1500;
      this.bindControls();
      this.element.addEventListener("keydown", (event) => this.handleKey(event));
      this.updateButtons();
    }

    async init() {
      if (!window.mermaid) throw new Error("Mermaid is not available");
      if (!mermaidConfigured) {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        mermaidConfigured = true;
      }
      const { svg } = await window.mermaid.render(`flow-player-${++renderSequence}`, this.source);
      this.element.querySelector(".flow-player__canvas").innerHTML = svg;
      this.svg = this.element.querySelector("svg");
      for (const step of this.scenario.steps) {
        if (step.node && !this.findNode(step.node)) throw new Error(`SVG node not found: ${step.node}`);
        if (step.edge && !this.findEdge(step.edge.from, step.edge.to)) {
          throw new Error(`SVG edge not found: ${step.edge.from} → ${step.edge.to}`);
        }
      }
      this.ready = true;
      this.render(false);
    }

    bindControls() {
      for (const button of this.element.querySelectorAll("[data-action]")) {
        const action = button.dataset.action;
        if (["reset", "previous", "next", "play"].includes(action)) {
          button.addEventListener("click", () => { if (this.ready) this[action](); });
        }
      }
    }

    handleKey(event) {
      if (!this.ready || event.ctrlKey || event.metaKey || event.altKey) return;
      const moves = {
        ArrowRight: "next", ArrowDown: "next",
        ArrowLeft: "previous", ArrowUp: "previous",
        Home: "reset", End: "last",
      };
      const move = moves[event.key];
      if (!move) return;
      event.preventDefault();
      if (move === "last") {
        this.pause();
        this.goTo(this.scenario.steps.length - 1, false);
      } else {
        this[move]();
      }
    }

    goTo(index, animate = true) {
      this.stopClock();
      this.currentStep = index;
      this.elapsed = 0;
      this.render(animate);
      this.startClock();
    }

    next() {
      this.pause();
      if (this.currentStep < this.scenario.steps.length - 1) this.goTo(this.currentStep + 1);
    }

    previous() {
      this.pause();
      this.goTo(Math.max(-1, this.currentStep - 1), false);
    }

    reset() {
      this.pause();
      this.goTo(-1, false);
    }

    play() {
      if (this.playing) return this.pause();
      this.playing = true;
      if (this.currentStep < 0 || (this.currentStep === this.scenario.steps.length - 1 && this.elapsed >= this.duration)) {
        this.goTo(0);
      } else {
        // Resume the same step and its remaining animation/dwell time.
        this.startClock();
      }
      this.updateButtons();
    }

    pause() {
      this.playing = false;
      this.stopClock();
      this.updateButtons();
    }

    stopClock() {
      if (this.frame !== null) this.clock.cancel(this.frame);
      this.frame = null;
      this.lastTime = null;
    }

    startClock() {
      if (this.frame !== null || (!this.playing && !this.marker)) return;
      this.lastTime = this.clock.now();
      this.frame = this.clock.request((now) => this.tick(now));
    }

    tick(now) {
      this.frame = null;
      if (!this.element.isConnected) return this.pause();
      this.elapsed += Math.max(0, now - this.lastTime);
      this.lastTime = now;
      this.positionMarker();
      if (this.playing && this.elapsed >= this.duration) {
        if (this.currentStep < this.scenario.steps.length - 1) this.goTo(this.currentStep + 1);
        else this.pause();
      } else {
        this.startClock();
      }
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
      for (const node of this.svg.querySelectorAll("g.node")) {
        node.classList.remove(...STATES.map((state) => `flow-state-${state}`));
      }
      if (this.marker) this.marker.remove();
      this.marker = null;
    }

    applyStep(step, animate) {
      if (step.node) {
        const node = this.findNode(step.node);
        node.classList.remove(...STATES.map((state) => `flow-state-${state}`));
        node.classList.add(`flow-state-${step.state ?? "active"}`);
      } else if (step.edge && animate) {
        this.animateEdge(step.edge.from, step.edge.to);
      }
    }

    findNode(id) {
      const nodePattern = new RegExp(`(?:^|[-_:])flowchart-${escapeRegExp(id)}-\\d+$`);
      return Array.from(this.svg.querySelectorAll("g.node")).find((node) => {
        if (node.dataset?.id === id) return true;
        if (node.id === id) return true;
        return nodePattern.test(node.id);
      });
    }

    findEdge(from, to) {
      const edgeId = `L_${from}_${to}`;
      const edgePattern = new RegExp(`(?:^|[-_:])${escapeRegExp(edgeId)}_\\d+$`);
      return Array.from(this.svg.querySelectorAll("path")).find((path) => {
        if (path.dataset?.id === edgeId) return true;
        return edgePattern.test(path.id);
      });
    }

    animateEdge(from, to) {
      if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
      this.path = this.findEdge(from, to);
      this.pathLength = this.path.getTotalLength();
      this.marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      this.marker.setAttribute("r", "6");
      this.marker.setAttribute("class", "flow-traveller");
      this.markerLayer().appendChild(this.marker);
      this.positionMarker();
    }

    markerLayer() {
      // The traveller must paint above edge labels and nodes. Mermaid puts no
      // transform on `g.edgePaths` or its parent, so path coordinates stay valid
      // in an overlay group appended last to that shared parent.
      const container = this.path.parentNode.parentNode ?? this.path.parentNode;
      let layer = container.querySelector?.(":scope > .flow-player__marker-layer");
      if (!layer) {
        layer = document.createElementNS("http://www.w3.org/2000/svg", "g");
        layer.setAttribute("class", "flow-player__marker-layer");
        container.appendChild(layer);
      }
      return layer;
    }

    positionMarker() {
      if (!this.marker) return;
      const progress = Math.min(this.elapsed / Math.min(this.duration, 1200), 1);
      const point = this.path.getPointAtLength(this.pathLength * progress);
      this.marker.setAttribute("cx", point.x);
      this.marker.setAttribute("cy", point.y);
      if (progress >= 1) {
        this.marker.remove();
        this.marker = null;
      }
    }

    renderDetails() {
      const step = this.scenario.steps[this.currentStep];
      this.element.querySelector(".flow-player__counter").textContent = step
        ? `Step ${this.currentStep + 1}/${this.scenario.steps.length}` : "Ready";
      this.element.querySelector(".flow-player__step-title").textContent = step
        ? (step.title ?? `Step ${this.currentStep + 1}`) : "Select Next to start";
      this.element.querySelector(".flow-player__description").textContent = step?.description ?? "";
      const payload = this.element.querySelector(".flow-player__payload");
      const hasPayload = step && Object.prototype.hasOwnProperty.call(step, "payload");
      payload.hidden = !hasPayload;
      payload.textContent = hasPayload ? JSON.stringify(step.payload, null, 2) : "";
    }

    updateButtons() {
      const active = this.element.ownerDocument?.activeElement;
      for (const button of this.element.querySelectorAll("[data-action]")) {
        const disabled = !this.ready
          || (button.dataset.action === "previous" && this.currentStep < 0)
          || (button.dataset.action === "next" && this.currentStep >= this.scenario.steps.length - 1);
        // Keep keyboard focus in the control bar when the focused button self-disables.
        if (disabled && this.ready && button === active) {
          this.element.querySelector('[data-action="play"]')?.focus?.();
        }
        button.disabled = disabled;
        if (button.dataset.action === "play") {
          button.textContent = this.playing ? "Pause" : "Play";
          button.setAttribute("aria-pressed", String(this.playing));
        }
      }
    }
  }

  async function initialize(root = document) {
    for (const element of root.querySelectorAll(".flow-player")) {
      if (element.dataset.initialized || element.classList.contains("flow-player--invalid")) continue;
      element.dataset.initialized = "true";
      let player;
      try {
        // Constructor errors and asynchronous renderer errors are isolated alike.
        player = new FlowPlayer(element);
        await player.init();
      } catch (error) {
        if (player) { player.ready = false; player.pause(); }
        element.classList.add("flow-player--invalid");
        const target = element.querySelector(".flow-player__canvas") ?? element;
        target.textContent = `Flow rendering failed: ${error.message}`;
        element.querySelectorAll("[data-action]").forEach((button) => { button.disabled = true; });
      }
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { FlowPlayer, initialize };
  } else {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => initialize());
    else initialize();
    if (typeof document$ !== "undefined") document$.subscribe(() => initialize());
  }
})();
