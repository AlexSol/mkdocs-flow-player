(() => {
  "use strict";
  const STATES = ["active", "success", "warning", "error", "waiting"];
  const ZOOM_MIN = 0.6;
  const ZOOM_MAX = 1.8;
  const ZOOM_STEP = 0.2;
  let renderSequence = 0;
  let mermaidConfigured = false;

  function escapeRegExp(value) {
    return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function parseSequenceEdges(source) {
    const lines = String(source).split(/\r?\n|;/).map((line) => line.trim()).filter(Boolean);
    if (lines[0] !== "sequenceDiagram") return [];
    const id = "[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*";
    const message = new RegExp(`^(${id})\\s*[-.=x)]*>>[+-]?\\s*(${id})\\s*:`);
    const counts = new Map();
    const edges = [];
    for (const line of lines.slice(1)) {
      const match = message.exec(line);
      if (!match) continue;
      const key = `${match[1]}\\u0000${match[2]}`;
      const nth = (counts.get(key) ?? 0) + 1;
      counts.set(key, nth);
      edges.push({ from: match[1], to: match[2], nth });
    }
    return edges;
  }

  class FlowPlayer {
    constructor(element, clock = {
      now: () => performance.now(),
      request: (callback) => requestAnimationFrame(callback),
      cancel: (id) => cancelAnimationFrame(id),
    }) {
      this.element = element;
      this.clock = clock;
      const scenarioData = JSON.parse(element.querySelector(".flow-player__scenario").textContent);
      this.scenarios = Array.isArray(scenarioData) ? scenarioData : [scenarioData];
      this.scenario = this.scenarios[0];
      this.metadata = JSON.parse(element.querySelector(".flow-player__metadata")?.textContent ?? '{"nodes":{}}');
      this.source = JSON.parse(element.querySelector(".flow-player__mermaid").textContent);
      this.sequenceEdges = parseSequenceEdges(this.source);
      this.currentStep = -1;
      this.playing = false;
      this.elapsed = 0;
      this.frame = null;
      this.lastTime = null;
      this.marker = null;
      this.svg = null;
      this.ready = false;
      this.zoom = 1;
      this.scenarioSelect = this.element.querySelector(".flow-player__scenario-select");
      this.zoomValue = this.element.querySelector(".flow-player__zoom-value");
      this.duration = this.scenario.settings?.step_duration ?? 1500;
      this.bindScenarioPicker();
      this.bindZoomControls();
      this.bindControls();
      this.element.addEventListener("keydown", (event) => this.handleKey(event));
      this.applyZoom();
      this.updateButtons();
    }

    async init() {
      if (!window.mermaid) throw new Error("Mermaid is not available");
      if (!mermaidConfigured) {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
        mermaidConfigured = true;
      }
      const { svg } = await window.mermaid.render(`flow-player-${++renderSequence}`, this.source);
      (this.element.querySelector(".flow-player__diagram") ?? this.element.querySelector(".flow-player__canvas")).innerHTML = svg;
      this.svg = this.element.querySelector("svg");
      this.validateScenarioSvg();
      this.ready = true;
      this.render(false);
    }

    validateScenarioSvg() {
      for (const step of this.scenario.steps) {
        if (step.node && !this.findNode(step.node)) throw new Error(`SVG node not found: ${step.node}`);
        if (step.edge && !this.findEdge(step.edge.from, step.edge.to, step.edge.nth)) {
          throw new Error(`SVG edge not found: ${step.edge.from} → ${step.edge.to}`);
        }
      }
    }

    bindScenarioPicker() {
      if (!this.scenarioSelect) return;
      this.scenarioSelect.addEventListener("change", () => {
        const next = this.scenarios[Number(this.scenarioSelect.value)];
        if (next && this.ready) this.selectScenario(next);
      });
    }

    bindControls() {
      for (const button of this.element.querySelectorAll("[data-action]")) {
        const action = button.dataset.action;
        if (["reset", "previous", "next", "play"].includes(action)) {
          button.addEventListener("click", () => { if (this.ready) this[action](); });
        }
      }
    }

    bindZoomControls() {
      for (const button of this.element.querySelectorAll("[data-zoom]")) {
        button.addEventListener("click", () => this.changeZoom(button.dataset.zoom));
      }
    }

    changeZoom(action) {
      if (action === "in") this.setZoom(this.zoom + ZOOM_STEP);
      else if (action === "out") this.setZoom(this.zoom - ZOOM_STEP);
      else if (action === "reset") this.setZoom(1);
    }

    setZoom(value) {
      const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, value));
      this.zoom = Math.round(clamped * 100) / 100;
      this.applyZoom();
    }

    applyZoom() {
      this.element.style.setProperty("--flow-zoom", String(this.zoom));
      if (this.zoomValue) this.zoomValue.textContent = `${Math.round(this.zoom * 100)}%`;
      this.updateZoomButtons();
    }

    updateZoomButtons() {
      for (const button of this.element.querySelectorAll("[data-zoom]")) {
        button.disabled = (button.dataset.zoom === "out" && this.zoom <= ZOOM_MIN)
          || (button.dataset.zoom === "in" && this.zoom >= ZOOM_MAX)
          || (button.dataset.zoom === "reset" && this.zoom === 1);
      }
    }

    selectScenario(scenario) {
      this.pause();
      this.scenario = scenario;
      this.duration = this.scenario.settings?.step_duration ?? 1500;
      this.element.dataset.flowId = this.scenario.id;
      this.validateScenarioSvg();
      this.goTo(-1, false);
    }

    handleKey(event) {
      if (!this.ready || event.ctrlKey || event.metaKey || event.altKey) return;
      if (["SELECT", "INPUT", "TEXTAREA"].includes(event.target?.tagName)) return;
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
      const stateClasses = STATES.map((state) => `flow-state-${state}`);
      // Flowchart state lands on `g.node`; sequence state lands on an actor's
      // wrapper `<g>`, which is not a `g.node`. Clear both, matched by class so a
      // Reset or a backwards step never leaves a stale highlight behind.
      const stale = new Set([
        ...this.svg.querySelectorAll("g.node"),
        ...this.svg.querySelectorAll(stateClasses.map((name) => `.${name}`).join(",")),
      ]);
      for (const node of stale) node.classList.remove(...stateClasses);
      if (this.marker) this.marker.remove();
      this.marker = null;
    }

    applyStep(step, animate) {
      if (step.node) {
        const stateClasses = STATES.map((state) => `flow-state-${state}`);
        // Mermaid mirrors a sequence actor at both ends of its lifeline; highlight
        // every box that carries the id, not just the first one found.
        for (const node of this.findNodes(step.node)) {
          node.classList.remove(...stateClasses);
          node.classList.add(`flow-state-${step.state ?? "active"}`);
        }
      } else if (step.edge && animate) {
        this.animateEdge(step.edge.from, step.edge.to, step.edge.nth);
      }
    }

    findNode(id) {
      return this.findNodes(id)[0];
    }

    findNodes(id) {
      const pattern = new RegExp(`(?:^|[-_:])flowchart-${escapeRegExp(id)}-\\d+$`);
      const matches = (node) => node.dataset?.id === id || node.id === id
        || node.textContent?.trim() === id || pattern.test(node.id);
      const groups = [];
      for (const node of this.svg.querySelectorAll("g.node, g[id^='root-'], text.actor, .actor")) {
        if (!matches(node)) continue;
        const group = node.closest?.("g") ?? node;
        if (group && !groups.includes(group)) groups.push(group);
      }
      if (groups.length) return groups;
      const fallback = Array.from(this.svg.querySelectorAll("g.node")).find(matches);
      return fallback ? [fallback] : [];
    }

    findEdge(from, to, nth = 1) {
      const edgeId = `L_${from}_${to}`;
      const edgeIndex = Number.isInteger(nth) && nth > 0 ? nth - 1 : 0;
      const edgePattern = new RegExp(`(?:^|[-_:])${escapeRegExp(edgeId)}_${edgeIndex}$`);
      const idMatch = Array.from(this.svg.querySelectorAll("path, line")).find((path) => {
        if (path.dataset?.id === edgeId && Number(path.dataset?.edgeIndex ?? edgeIndex) === edgeIndex) return true;
        return edgePattern.test(path.id);
      });
      if (idMatch) return idMatch;
      const sequenceIndex = this.sequenceEdges.findIndex((edge) => edge.from === from && edge.to === to && edge.nth === nth);
      if (sequenceIndex < 0) return undefined;
      return Array.from(this.svg.querySelectorAll("line[class^='messageLine'], path[class^='messageLine']"))[sequenceIndex];
    }

    animateEdge(from, to, nth) {
      if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
      this.path = this.findEdge(from, to, nth);
      this.pathGeometry = this.edgeGeometry(this.path);
      this.pathLength = this.pathGeometry.length;
      this.marker = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      this.marker.setAttribute("r", "6");
      this.marker.setAttribute("class", "flow-traveller");
      this.markerLayer().appendChild(this.marker);
      this.positionMarker();
    }

    edgeGeometry(edge) {
      if (edge.getTotalLength && edge.getPointAtLength) {
        return { length: edge.getTotalLength(), pointAt: (distance) => edge.getPointAtLength(distance) };
      }
      const x1 = Number(edge.getAttribute("x1"));
      const y1 = Number(edge.getAttribute("y1"));
      const x2 = Number(edge.getAttribute("x2"));
      const y2 = Number(edge.getAttribute("y2"));
      const length = Math.hypot(x2 - x1, y2 - y1);
      return {
        length,
        pointAt: (distance) => {
          const progress = length ? distance / length : 1;
          return { x: x1 + (x2 - x1) * progress, y: y1 + (y2 - y1) * progress };
        },
      };
    }

    markerLayer() {
      // The traveller must paint above edge labels and nodes. Mermaid puts no
      // transform on `g.edgePaths` or its parent, so path coordinates stay valid
      // in an overlay group appended last to that shared parent. Sequence message
      // lines, though, sit directly under `<svg>`, so the grandparent is the HTML
      // wrapper - an SVG group appended there never renders. Clamp to the SVG.
      const SVG_NS = "http://www.w3.org/2000/svg";
      let container = this.path.parentNode?.parentNode ?? this.path.parentNode;
      if (container?.namespaceURI && container.namespaceURI !== SVG_NS) {
        container = this.path.ownerSVGElement ?? this.path.parentNode;
      }
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
      const point = this.pathGeometry.pointAt(this.pathLength * progress);
      this.marker.setAttribute("cx", point.x);
      this.marker.setAttribute("cy", point.y);
      if (progress >= 1) {
        this.marker.remove();
        this.marker = null;
      }
    }

    renderDetails() {
      const step = this.scenario.steps[this.currentStep];
      const node = step?.node ? this.metadata.nodes?.[step.node] : null;
      this.element.querySelector(".flow-player__counter").textContent = step
        ? `Step ${this.currentStep + 1}/${this.scenario.steps.length}` : "Ready";
      this.element.querySelector(".flow-player__step-title").textContent = step
        ? (step.title ?? step.edge?.label ?? `Step ${this.currentStep + 1}`) : "Select Next to start";
      const summary = this.element.querySelector(".flow-player__node-summary");
      summary.hidden = !node?.summary;
      summary.textContent = node?.summary ?? "";
      const doc = this.element.querySelector(".flow-player__node-doc");
      const link = doc.querySelector("a");
      doc.hidden = !node?.doc_href;
      if (node?.doc_href) {
        link.href = node.doc_href;
        link.textContent = "Learn more";
        if (node.doc_external) {
          link.target = "_blank";
          link.rel = "noopener noreferrer";
        } else {
          link.removeAttribute("target");
          link.removeAttribute("rel");
        }
      } else {
        link.removeAttribute("href");
        link.removeAttribute("target");
        link.removeAttribute("rel");
        link.textContent = "";
      }
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
      this.updateZoomButtons();
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
        const target = element.querySelector(".flow-player__diagram") ?? element.querySelector(".flow-player__canvas") ?? element;
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
