// 产线三维孪生：Workshop 自定义组件（契约见《Workshop 自定义组件开发规范》第四节）。
// 每行数据是一台设备：按工厂 → 工作中心排成车间与工位，按设备类型程序化建模；
// 状态、加工中与排队工序数都来自数据源（知识网络的属性与关联计数），组件只负责画出来。
// 哪个状态算正常由配置 normalStatus 给出，代码里不写业务判断。

import {
  AmbientLight,
  Box3,
  BoxGeometry,
  Color,
  CylinderGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  MathUtils,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PCFSoftShadowMap,
  PerspectiveCamera,
  PlaneGeometry,
  Raycaster,
  RingGeometry,
  Scene,
  ShadowMaterial,
  SRGBColorSpace,
  Vector2,
  Vector3,
  WebGLRenderer,
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

const TEXT = {
  "zh-CN": {
    empty: "没有设备数据",
    missing: "数据源缺少字段：",
    noGl: "这个浏览器不能显示三维画面",
    truncated: (n) => `只显示前 ${n} 台设备`,
    running: "加工中",
    idle: "待机",
    attention: "需关注",
    queued: "排队工序",
    units: (n) => `${n} 台`,
    queuedN: (n) => `排队 ${n} 道`,
    runningN: (n) => `加工中 ${n} 道`,
    reset: "回到全景",
    pickOff: "构建与预览中点击不联动",
    summary: ({ sites, groups, machines, running, attention, busiest, selected }) =>
      [
        `三维产线：${sites} 个工厂、${groups} 个工作中心、${machines} 台设备`,
        running.length ? `加工中 ${running.length} 台（${running.join("、")}）` : "没有设备在加工",
        attention.length ? `需关注 ${attention.length} 台（${attention.join("、")}）` : "没有需关注的设备",
        busiest ? `排队工序最多的是${busiest.name}（${busiest.queued} 道）` : "",
        selected ? `已选中${selected}` : "",
      ]
        .filter(Boolean)
        .join("；") + "。",
  },
  "en-US": {
    empty: "No machines",
    missing: "The source is missing fields: ",
    noGl: "This browser cannot show 3D",
    truncated: (n) => `Showing the first ${n} machines`,
    running: "Running",
    idle: "Idle",
    attention: "Needs attention",
    queued: "Queued operations",
    units: (n) => `${n} machines`,
    queuedN: (n) => `${n} queued`,
    runningN: (n) => `${n} running`,
    reset: "Back to overview",
    pickOff: "Clicks do nothing while building or previewing",
    summary: ({ sites, groups, machines, running, attention, busiest, selected }) =>
      [
        `3D line: ${sites} sites, ${groups} work centers, ${machines} machines`,
        running.length ? `${running.length} running (${running.join(", ")})` : "none running",
        attention.length ? `${attention.length} need attention (${attention.join(", ")})` : "none need attention",
        busiest ? `most queued: ${busiest.name} (${busiest.queued})` : "",
        selected ? `selected: ${selected}` : "",
      ]
        .filter(Boolean)
        .join("; ") + ".",
  },
};

const STYLE = `
:host { display: block; height: 100%; position: relative; overflow: hidden;
  color: var(--workshop-color-text, #203043);
  font-family: var(--workshop-font-family, system-ui, sans-serif);
  font-size: var(--workshop-font-size, 13px); }
.root { position: absolute; inset: 0; }
canvas { display: block; width: 100%; height: 100%; touch-action: none; outline: none; }
.layer { position: absolute; inset: 0; pointer-events: none; }
.tag { position: absolute; left: 0; top: 0; white-space: nowrap; transform: translate(-50%, -100%);
  will-change: transform; }
.bay { color: var(--workshop-color-text-muted, #607086); font-size: 12px; }
.bay b { color: var(--workshop-color-text, #203043); font-weight: 600; margin-right: 6px; }
.site { font-size: 14px; font-weight: 600; letter-spacing: .02em; transform: translate(0, -100%); }
.callout { padding: 6px 10px; border-radius: var(--workshop-radius, 8px);
  background: var(--workshop-color-surface, #fff); border: 1px solid var(--workshop-color-border, #dfe5ec);
  box-shadow: 0 6px 18px rgba(15, 23, 42, .12); line-height: 1.45; margin-top: -10px; }
.callout .name { font-weight: 600; }
.callout .meta { color: var(--workshop-color-text-muted, #607086); font-size: 12px; }
.chip { padding: 1px 8px; border-radius: 999px; font-size: 12px; line-height: 18px; margin-top: -6px;
  color: var(--workshop-color-surface, #fff); background: var(--workshop-color-warning, #9b4e12); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: 0; }
.legend { position: absolute; left: 14px; top: 12px; display: flex; gap: 14px; flex-wrap: wrap;
  color: var(--workshop-color-text-muted, #607086); font-size: 12px; pointer-events: none; }
.legend .cube { display: inline-block; width: 8px; height: 8px; margin-right: 5px; border-radius: 2px; }
.tools { position: absolute; right: 10px; top: 10px; display: flex; gap: 6px; }
.tools button { all: unset; box-sizing: border-box; width: 32px; height: 32px; border-radius: var(--workshop-radius, 8px);
  display: grid; place-items: center; cursor: pointer; color: var(--workshop-color-text-muted, #607086);
  background: var(--workshop-color-surface, #fff); border: 1px solid var(--workshop-color-border, #dfe5ec); }
.tools button:hover, .tools button:focus-visible { color: var(--workshop-color-primary, #255db0);
  border-color: var(--workshop-color-primary, #255db0); }
.note { position: absolute; right: 56px; top: 18px; color: var(--workshop-color-text-muted, #607086); font-size: 12px; }
[hidden] { display: none !important; }
.hint { position: absolute; inset: 0; display: grid; place-items: center; color: var(--workshop-color-text-muted, #607086); }
.root.narrow .legend { gap: 10px; left: 10px; right: 10px; }
.root.narrow .tools button { width: 44px; height: 44px; }
.root.narrow .bay span { display: none; }
`;

const RESET_ICON = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>`;

// 设备类型 → 造型。只影响外观；认不出的类型画成通用机柜。
const SHAPES = [
  { shape: "mill", words: ["加工中心", "铣", "mill", "machining"] },
  { shape: "lathe", words: ["车床", "车削", "lathe", "turn"] },
  { shape: "cmm", words: ["测量", "三坐标", "cmm", "measur"] },
  { shape: "tester", words: ["测试", "试验", "test"] },
  { shape: "laser", words: ["打标", "激光", "laser", "mark"] },
];
const shapeOf = (kind) => {
  const text = String(kind ?? "").toLowerCase();
  return SHAPES.find((item) => item.words.some((word) => text.includes(word)))?.shape ?? "generic";
};
// 造型的占地（宽 × 深），排布工位用。
const FOOTPRINT = {
  mill: [2.0, 1.5],
  lathe: [2.4, 1.2],
  cmm: [1.8, 1.4],
  tester: [1.8, 1.0],
  laser: [1.0, 0.9],
  generic: [1.6, 1.2],
};

const SPACING = 3.0;
const BAY_DEPTH = 3.6;
const BAY_GAP = 1.5;
const HALL_PAD = 0.8;
const HALL_GAP = 3.2;
const MAX_MACHINES = 400;

class LineTwinElement extends HTMLElement {
  #config = {};
  #data = null;
  #variables = {};
  #theme = null;
  #locale = "zh-CN";
  #mode = "run";
  #workshop = null;

  #root;
  #canvas;
  #layer;
  #legend;
  #note;
  #hint;
  #resize;
  #visible = true;
  #io;

  #renderer = null;
  #scene = null;
  #camera = null;
  #controls = null;
  #world = null;
  #palette = null;
  #machines = []; // { row, group, body[], lamp, ring, focus, spinners, probe, beam, anchor }
  #labels = []; // { el, point }
  #callout = null;
  #chips = [];
  #hovered = null;
  #selectedKey = null;
  #bounds = { radius: 10, center: new Vector3() };
  #fitPoints = [];
  #frame = 0;
  #clock = 0;
  #intro = null;
  #down = null;
  #dirty = true;
  #built = false;
  #reduced = false;

  constructor() {
    super();
    const shadow = this.attachShadow({ mode: "open" });
    shadow.innerHTML = `<style>${STYLE}</style>
      <div class="root">
        <canvas tabindex="0"></canvas>
        <div class="layer"></div>
        <div class="legend"></div>
        <div class="tools"><button type="button" class="reset">${RESET_ICON}</button></div>
        <div class="note"></div>
        <div class="hint" hidden></div>
      </div>`;
    this.#root = shadow.querySelector(".root");
    this.#canvas = shadow.querySelector("canvas");
    this.#layer = shadow.querySelector(".layer");
    this.#legend = shadow.querySelector(".legend");
    this.#note = shadow.querySelector(".note");
    this.#hint = shadow.querySelector(".hint");
    shadow.querySelector(".reset").addEventListener("click", () => this.#fit(true));
    this.#canvas.addEventListener("pointerdown", (event) => {
      this.#down = { x: event.clientX, y: event.clientY };
    });
    this.#canvas.addEventListener("pointerup", (event) => this.#onPointerUp(event));
    this.#canvas.addEventListener("pointermove", (event) => this.#onHover(event));
    this.#canvas.addEventListener("pointerleave", () => this.#setHovered(null));
    this.#canvas.addEventListener("keydown", (event) => this.#onKey(event));
  }

  // Workshop 设置的属性：可能在挂载之前或之后设置，重复设置时只更新变化的部分。
  set config(value) {
    this.#config = value ?? {};
    this.#rebuild();
  }
  set data(value) {
    this.#data = value;
    this.#rebuild();
  }
  set theme(value) {
    this.#theme = value ?? null;
    this.#rebuild();
  }
  set locale(value) {
    this.#locale = TEXT[value] ? value : "zh-CN";
    this.#rebuild();
  }
  set mode(value) {
    this.#mode = value ?? "run";
    this.#chrome();
  }
  set workshop(value) {
    this.#workshop = value;
  }
  set variables(value) {
    this.#variables = value ?? {};
    const key = selectedKeyOf(this.#variables[this.#config.selection]);
    if (key !== this.#selectedKey) {
      this.#selectedKey = key;
      this.#paintStates();
      this.#describe();
    }
  }

  connectedCallback() {
    this.#reduced = matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    this.#resize = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      this.#root.classList.toggle("narrow", width < 600);
      this.#sizeTo(width, height);
    });
    this.#resize.observe(this);
    this.#io = new IntersectionObserver(([entry]) => {
      this.#visible = entry.isIntersecting;
      if (this.#visible) this.#loop();
    });
    this.#io.observe(this);
    this.#rebuild();
  }

  disconnectedCallback() {
    this.#resize?.disconnect();
    this.#io?.disconnect();
    cancelAnimationFrame(this.#frame);
    this.#frame = 0;
    this.#controls?.dispose();
    this.#disposeWorld();
    this.#renderer?.dispose();
    this.#renderer = null;
    this.#controls = null;
    this.#built = false;
  }

  get #text() {
    return TEXT[this.#locale];
  }

  // ---- 数据 ----

  #rows() {
    const roles = this.#config.fieldRoles ?? {};
    const keys = new Set((this.#data?.fields ?? []).map((field) => field.key));
    const missing = ["name", "group"].filter((role) => !roles[role] || !keys.has(roles[role]));
    if (missing.length) return { missing };
    const read = (row, role) => (roles[role] && keys.has(roles[role]) ? row[roles[role]] : undefined);
    const normal = this.#config.normalStatus ?? "";
    const rows = (this.#data?.rows ?? []).slice(0, MAX_MACHINES).map((row, index) => {
      const status = read(row, "status");
      const running = Number(read(row, "running")) || 0;
      const queued = Number(read(row, "queued")) || 0;
      const attention = status != null && status !== "" && normal !== "" && String(status) !== normal;
      return {
        index,
        key: row._object?.id ?? String(read(row, "name") ?? index),
        object: row._object,
        name: String(read(row, "name") ?? ""),
        group: String(read(row, "group") ?? "—"),
        site: String(read(row, "site") ?? ""),
        kind: String(read(row, "kind") ?? ""),
        status: status == null ? "" : String(status),
        running,
        queued,
        state: attention ? "attention" : running > 0 ? "running" : "idle",
      };
    });
    return { rows };
  }

  // ---- 场景 ----

  #ensureRenderer() {
    if (this.#renderer) return true;
    try {
      this.#renderer = new WebGLRenderer({ canvas: this.#canvas, antialias: true, alpha: true });
    } catch {
      this.#renderer = null;
      return false;
    }
    this.#renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    this.#renderer.outputColorSpace = SRGBColorSpace;
    this.#renderer.shadowMap.enabled = true;
    this.#renderer.shadowMap.type = PCFSoftShadowMap;
    this.#scene = new Scene();
    this.#camera = new PerspectiveCamera(24, 1, 0.1, 800);
    this.#controls = new OrbitControls(this.#camera, this.#canvas);
    this.#controls.enableDamping = true;
    this.#controls.dampingFactor = 0.08;
    this.#controls.maxPolarAngle = MathUtils.degToRad(80);
    this.#controls.minPolarAngle = MathUtils.degToRad(12);
    this.#controls.screenSpacePanning = false;
    this.#controls.addEventListener("change", () => {
      this.#dirty = true;
      this.#loop();
    });
    const rect = this.getBoundingClientRect();
    this.#sizeTo(rect.width, rect.height);
    return true;
  }

  #readPalette() {
    const css = getComputedStyle(this);
    const pick = (key, name, fallback) =>
      (this.#theme && typeof this.#theme[key] === "string" && this.#theme[key]) ||
      css.getPropertyValue(name).trim() ||
      fallback;
    const dark = (this.#theme?.mode ?? "light") === "dark";
    const surface = new Color(pick("colorSurface", "--workshop-color-surface", "#ffffff"));
    const text = new Color(pick("colorText", "--workshop-color-text", "#203043"));
    const bg = new Color(pick("colorBg", "--workshop-color-bg", "#f3f5f8"));
    const mix = (a, b, t) => a.clone().lerp(b, t);
    return {
      dark,
      primary: new Color(pick("colorPrimary", "--workshop-color-primary", "#255db0")),
      success: new Color(pick("colorSuccess", "--workshop-color-success", "#267257")),
      warning: new Color(pick("colorWarning", "--workshop-color-warning", "#9b4e12")),
      danger: new Color(pick("colorDanger", "--workshop-color-danger", "#b42318")),
      info: new Color(pick("colorInfo", "--workshop-color-info", "#1f6f9f")),
      muted: new Color(pick("colorTextMuted", "--workshop-color-text-muted", "#607086")),
      border: new Color(pick("colorBorder", "--workshop-color-border", "#dfe5ec")),
      surface,
      text,
      bg,
      hall: dark ? mix(surface, text, 0.04) : mix(bg, text, 0.035),
      bay: dark ? mix(surface, text, 0.1) : surface.clone(),
      body: dark ? mix(surface, text, 0.26) : mix(surface, text, 0.07),
      trim: dark ? mix(surface, text, 0.08) : mix(surface, text, 0.62),
      metal: mix(surface, text, dark ? 0.5 : 0.35),
      granite: mix(surface, text, dark ? 0.06 : 0.5),
    };
  }

  #rebuild() {
    if (!this.isConnected) return;
    const text = this.#text;
    const { rows, missing } = this.#rows();
    this.#chrome();
    if (missing) {
      this.#showHint(`${text.missing}${missing.join("、")}`);
      return;
    }
    if (!rows.length) {
      this.#showHint(text.empty);
      this.#describe();
      return;
    }
    if (!this.#ensureRenderer()) {
      this.#showHint(text.noGl);
      return;
    }
    this.#hint.hidden = true;
    this.#canvas.hidden = false;
    this.#palette = this.#readPalette();
    const first = !this.#built;
    this.#disposeWorld();
    this.#buildWorld(rows);
    this.#built = true;
    this.#selectedKey = selectedKeyOf(this.#variables[this.#config.selection]);
    this.#paintStates();
    this.#legendHtml();
    if (first) this.#fit(false, true);
    this.#dirty = true;
    this.#loop();
    this.#describe();
  }

  #showHint(message) {
    this.#hint.hidden = false;
    this.#hint.textContent = message;
    this.#canvas.hidden = true;
    this.#layer.innerHTML = "";
    this.#legend.innerHTML = "";
  }

  #chrome() {
    const text = this.#text;
    const reset = this.#root.querySelector(".reset");
    reset.title = text.reset;
    reset.setAttribute("aria-label", text.reset);
    const notes = [];
    if (this.#data?.truncated) notes.push(text.truncated(this.#data.rows?.length ?? 0));
    if (this.#mode !== "run") notes.push(text.pickOff);
    this.#note.textContent = notes.join(" · ");
  }

  #legendHtml() {
    const p = this.#palette;
    const text = this.#text;
    const css = (color) => `#${color.getHexString()}`;
    const dot = (color, label) => `<span><i class="dot" style="background:${css(color)}"></i>${label}</span>`;
    this.#legend.innerHTML = [
      dot(p.success, text.running),
      dot(p.muted, text.idle),
      dot(p.warning, text.attention),
      `<span><i class="cube" style="background:${css(p.primary.clone().lerp(p.surface, 0.35))}"></i>${text.queued}</span>`,
    ].join("");
  }

  #buildWorld(rows) {
    const p = this.#palette;
    const scene = this.#scene;
    const world = new Group();
    this.#world = world;
    scene.add(world);

    world.add(new HemisphereLight(0xffffff, p.bg, p.dark ? 1.0 : 1.05));
    world.add(new AmbientLight(0xffffff, p.dark ? 0.3 : 0.2));
    const sun = new DirectionalLight(0xffffff, p.dark ? 1.6 : 2.3);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.bias = -0.0004;
    sun.shadow.radius = 4;
    world.add(sun, sun.target);

    // 按工厂 → 工作中心分组，保持数据里第一次出现的先后。
    const sites = new Map();
    for (const row of rows) {
      if (!sites.has(row.site)) sites.set(row.site, new Map());
      const bays = sites.get(row.site);
      if (!bays.has(row.group)) bays.set(row.group, []);
      bays.get(row.group).push(row);
    }

    const shared = {
      hall: new MeshStandardMaterial({ color: p.hall, roughness: 0.95 }),
      bay: new MeshStandardMaterial({ color: p.bay, roughness: 0.9 }),
      stripe: new MeshStandardMaterial({ color: p.border, roughness: 0.9 }),
      trim: new MeshStandardMaterial({ color: p.trim, roughness: 0.55, metalness: 0.15 }),
      metal: new MeshStandardMaterial({ color: p.metal, roughness: 0.35, metalness: 0.6 }),
      granite: new MeshStandardMaterial({ color: p.granite, roughness: 0.7 }),
      glass: new MeshStandardMaterial({ color: p.info, roughness: 0.1, metalness: 0.1, transparent: true, opacity: 0.32 }),
      brand: new MeshStandardMaterial({ color: p.primary, roughness: 0.5 }),
      screen: new MeshStandardMaterial({ color: p.info, emissive: p.info, emissiveIntensity: 0.6 }),
      wip: new MeshStandardMaterial({ color: p.primary.clone().lerp(p.surface, 0.35), roughness: 0.6 }),
      pallet: new MeshStandardMaterial({ color: p.trim.clone().lerp(p.body, 0.4), roughness: 0.8 }),
      beam: new MeshBasicMaterial({ color: p.danger, transparent: true, opacity: 0.85 }),
    };
    this.#shared = shared;

    const machines = [];
    const labels = [];
    let x = 0;
    let maxDepth = 0;
    for (const [site, bays] of sites) {
      const widest = Math.max(...[...bays.values()].map((list) => list.length));
      const hallWidth = widest * SPACING + HALL_PAD * 2;
      const hallDepth = bays.size * BAY_DEPTH + (bays.size - 1) * BAY_GAP + HALL_PAD * 2;
      maxDepth = Math.max(maxDepth, hallDepth);
      const hall = new Mesh(new RoundedBoxGeometry(hallWidth, 0.12, hallDepth, 2, 0.06), shared.hall);
      hall.position.set(x + hallWidth / 2, -0.06, hallDepth / 2);
      hall.receiveShadow = true;
      world.add(hall);
      if (site) labels.push({ html: `<div class="tag site"></div>`, text: site, point: new Vector3(x + 0.2, 0.05, -0.25) });

      let z = HALL_PAD;
      for (const [group, list] of bays) {
        const bayWidth = list.length * SPACING;
        const bayX = x + HALL_PAD + (widest * SPACING - bayWidth) / 2;
        const pad = new Mesh(new RoundedBoxGeometry(bayWidth, 0.06, BAY_DEPTH, 2, 0.03), shared.bay);
        pad.position.set(bayX + bayWidth / 2, 0.03, z + BAY_DEPTH / 2);
        pad.receiveShadow = true;
        world.add(pad);
        labels.push({
          html: `<div class="tag bay"><b></b><span></span></div>`,
          text: group,
          sub: this.#text.units(list.length),
          point: new Vector3(bayX + 0.25, 0.07, z + BAY_DEPTH - 0.2),
        });
        list.forEach((row, i) => {
          const cx = bayX + SPACING * (i + 0.5);
          const cz = z + BAY_DEPTH / 2 - 0.35;
          machines.push(this.#buildMachine(row, cx, cz));
        });
        z += BAY_DEPTH + BAY_GAP;
      }
      x += hallWidth + HALL_GAP;
    }
    const totalWidth = x - HALL_GAP;
    // 居中到原点，相机与光照都按中心计算。
    world.position.set(-totalWidth / 2, 0, -maxDepth / 2);
    for (const label of labels) label.point.add(world.position);
    world.updateMatrixWorld(true);
    const points = [];
    world.children.forEach((child) => {
      if (!child.isMesh && !child.userData.machine && child.userData.machine !== 0) return;
      const box = new Box3().setFromObject(child);
      if (box.isEmpty()) return;
      for (const x of [box.min.x, box.max.x])
        for (const y of [box.min.y, box.max.y])
          for (const z of [box.min.z, box.max.z]) points.push(new Vector3(x, y, z));
    });
    for (const label of labels) points.push(label.point.clone().add(new Vector3(0, 0.5, 0)));
    this.#fitPoints = points;
    this.#bounds = {
      radius: Math.hypot(totalWidth, maxDepth) / 2,
      center: new Vector3(0, 0.3, 0),
      width: totalWidth,
      depth: maxDepth,
    };

    const radius = this.#bounds.radius;
    sun.position.set(radius * 0.6, radius * 1.4, radius * 0.9).sub(world.position);
    sun.target.position.copy(world.position).negate();
    const cam = sun.shadow.camera;
    cam.left = -radius * 1.1;
    cam.right = radius * 1.1;
    cam.top = radius * 1.1;
    cam.bottom = -radius * 1.1;
    cam.near = 0.5;
    cam.far = radius * 5;
    cam.updateProjectionMatrix();

    const ground = new Mesh(new PlaneGeometry(radius * 6, radius * 6), new ShadowMaterial({ opacity: p.dark ? 0.3 : 0.08 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(totalWidth / 2, -0.121, maxDepth / 2);
    ground.receiveShadow = true;
    world.add(ground);

    this.#machines = machines;
    this.#layer.innerHTML = "";
    this.#labels = labels.map((label) => {
      const holder = document.createElement("div");
      holder.innerHTML = label.html;
      const el = holder.firstElementChild;
      if (label.sub !== undefined) {
        el.querySelector("b").textContent = label.text;
        el.querySelector("span").textContent = label.sub;
      } else el.textContent = label.text;
      this.#layer.append(el);
      return { el, point: label.point };
    });
    const callout = document.createElement("div");
    callout.className = "tag callout";
    callout.hidden = true;
    this.#layer.append(callout);
    this.#callout = callout;
    this.#chips = machines
      .filter((item) => item.row.state === "attention")
      .map((item) => {
        const el = document.createElement("div");
        el.className = "tag chip";
        el.textContent = item.row.status;
        this.#layer.insertBefore(el, callout);
        return { el, item };
      });
  }

  #shared = null;

  #buildMachine(row, cx, cz) {
    const p = this.#palette;
    const s = this.#shared;
    const group = new Group();
    group.position.set(cx, 0.06, cz);
    group.userData.machine = row.index;
    const body = new MeshStandardMaterial({ color: p.body, roughness: 0.45, metalness: 0.05 });
    const lampMat = new MeshStandardMaterial({ color: p.muted, emissive: p.muted, emissiveIntensity: 0.4 });
    const parts = { spinners: [], probe: null, beam: null, needle: null };
    const add = (geometry, material, x, y, z, cast = true) => {
      const mesh = new Mesh(geometry, material);
      mesh.position.set(x, y, z);
      mesh.castShadow = cast;
      mesh.receiveShadow = true;
      group.add(mesh);
      return mesh;
    };
    const shape = shapeOf(row.kind);
    let lampAt;
    if (shape === "mill") {
      add(new RoundedBoxGeometry(2.0, 1.7, 1.5, 3, 0.08), body, 0, 0.85, 0);
      add(new BoxGeometry(2.02, 0.07, 1.52), s.brand, 0, 1.52, 0);
      add(new BoxGeometry(2.02, 0.22, 1.52), s.trim, 0, 0.11, 0);
      add(new BoxGeometry(1.1, 0.78, 0.03), s.glass, -0.15, 1.0, 0.76, false);
      add(new BoxGeometry(0.05, 0.86, 0.04), s.trim, 0.43, 1.0, 0.76);
      const spindle = add(new CylinderGeometry(0.09, 0.09, 0.42, 16), s.metal, -0.15, 1.15, 0.35);
      parts.spinners.push({ mesh: spindle, axis: "y", speed: 9 });
      add(new BoxGeometry(0.34, 0.5, 0.1), s.trim, 0.75, 1.05, 0.8);
      add(new BoxGeometry(0.26, 0.18, 0.02), s.screen, 0.75, 1.18, 0.86, false);
      lampAt = [0.82, 1.7, -0.58];
    } else if (shape === "lathe") {
      add(new RoundedBoxGeometry(2.4, 1.3, 1.2, 3, 0.08), body, 0, 0.65, 0);
      add(new BoxGeometry(2.42, 0.06, 1.22), s.brand, 0, 1.18, 0);
      add(new BoxGeometry(2.42, 0.2, 1.22), s.trim, 0, 0.1, 0);
      add(new BoxGeometry(1.4, 0.56, 0.03), s.glass, -0.25, 0.78, 0.61, false);
      const chuck = add(new CylinderGeometry(0.22, 0.22, 0.14, 20), s.metal, -0.7, 0.78, 0.3);
      chuck.rotation.z = Math.PI / 2;
      parts.spinners.push({ mesh: chuck, axis: "y", speed: 12 });
      add(new BoxGeometry(0.22, 0.2, 0.2), s.metal, 0.2, 0.74, 0.3);
      add(new BoxGeometry(0.32, 0.46, 0.1), s.trim, 0.85, 0.8, 0.65);
      add(new BoxGeometry(0.24, 0.16, 0.02), s.screen, 0.85, 0.92, 0.71, false);
      lampAt = [1.05, 1.3, -0.45];
    } else if (shape === "cmm") {
      add(new RoundedBoxGeometry(1.8, 0.72, 1.4, 3, 0.05), s.granite, 0, 0.36, 0);
      add(new BoxGeometry(0.12, 0.95, 0.14), body, -0.8, 1.2, 0);
      add(new BoxGeometry(0.12, 0.95, 0.14), body, 0.8, 1.2, 0);
      add(new BoxGeometry(1.76, 0.16, 0.22), body, 0, 1.72, 0);
      add(new BoxGeometry(1.76, 0.04, 0.23), s.brand, 0, 1.79, 0);
      const probe = new Group();
      probe.position.set(0, 1.4, 0);
      const column = new Mesh(new BoxGeometry(0.12, 0.62, 0.12), s.trim);
      column.castShadow = true;
      probe.add(column);
      const tip = new Mesh(new CylinderGeometry(0.02, 0.02, 0.18, 8), s.metal);
      tip.position.y = -0.4;
      probe.add(tip);
      group.add(probe);
      parts.probe = probe;
      add(new BoxGeometry(0.5, 0.18, 0.4), s.metal, 0.3, 0.81, 0.2);
      lampAt = [0.8, 1.86, 0.45];
    } else if (shape === "tester") {
      add(new RoundedBoxGeometry(1.8, 0.9, 1.0, 3, 0.06), body, 0, 0.45, 0);
      add(new BoxGeometry(1.82, 0.05, 1.02), s.brand, 0, 0.86, 0);
      add(new CylinderGeometry(0.28, 0.28, 0.9, 24), s.metal, -0.45, 1.36, -0.05);
      add(new CylinderGeometry(0.3, 0.3, 0.06, 24), s.trim, -0.45, 1.83, -0.05);
      add(new RoundedBoxGeometry(0.62, 0.7, 0.5, 2, 0.04), body, 0.45, 1.25, 0);
      add(new CylinderGeometry(0.15, 0.15, 0.03, 24), s.trim, 0.45, 1.32, 0.26).rotation.x = Math.PI / 2;
      const needle = add(new BoxGeometry(0.02, 0.12, 0.01), s.beam, 0.45, 1.36, 0.285, false);
      needle.geometry.translate(0, 0.05, 0);
      parts.needle = needle;
      lampAt = [0.7, 1.7, -0.2];
    } else if (shape === "laser") {
      add(new RoundedBoxGeometry(1.0, 1.0, 0.9, 3, 0.06), body, 0, 0.5, 0);
      add(new BoxGeometry(1.02, 0.05, 0.92), s.brand, 0, 0.98, 0);
      add(new BoxGeometry(0.82, 0.7, 0.72), s.glass, 0, 1.36, 0, false);
      add(new BoxGeometry(0.86, 0.06, 0.76), s.trim, 0, 1.73, 0);
      add(new CylinderGeometry(0.08, 0.08, 0.28, 16), s.metal, 0, 1.56, 0);
      const beam = add(new CylinderGeometry(0.012, 0.012, 0.42, 6), s.beam, 0, 1.22, 0, false);
      parts.beam = beam;
      lampAt = [0.4, 1.95, -0.3];
    } else {
      add(new RoundedBoxGeometry(1.6, 1.2, 1.2, 3, 0.08), body, 0, 0.6, 0);
      add(new BoxGeometry(1.62, 0.06, 1.22), s.brand, 0, 1.12, 0);
      lampAt = [0.6, 1.4, -0.4];
    }
    // 三色灯：杆 + 灯。
    add(new CylinderGeometry(0.025, 0.025, 0.3, 8), s.metal, lampAt[0], lampAt[1] - 0.05, lampAt[2]);
    const lamp = add(new CylinderGeometry(0.07, 0.07, 0.16, 16), lampMat, lampAt[0], lampAt[1] + 0.16, lampAt[2], false);

    // 排队工序：托盘上的料箱，最多画 12 个。
    const [w, d] = FOOTPRINT[shape];
    const wip = new Group();
    wip.position.set(w / 2 + 0.5, 0, d / 2 - 0.15);
    if (row.queued > 0) {
      const pallet = new Mesh(new BoxGeometry(0.62, 0.08, 0.62), s.pallet);
      pallet.position.y = 0.04;
      pallet.receiveShadow = true;
      wip.add(pallet);
      const count = Math.min(row.queued, 12);
      for (let i = 0; i < count; i++) {
        const cube = new Mesh(new RoundedBoxGeometry(0.24, 0.2, 0.24, 2, 0.03), s.wip);
        const layer = Math.floor(i / 4);
        const slot = i % 4;
        cube.position.set((slot % 2) * 0.28 - 0.14, 0.18 + layer * 0.22, Math.floor(slot / 2) * 0.28 - 0.14);
        cube.castShadow = true;
        wip.add(cube);
      }
    }
    group.add(wip);

    // 地面上的环：需关注（脉动）与选中。
    const reach = Math.max(w, d) / 2 + 0.45;
    const ring = new Mesh(
      new RingGeometry(reach, reach + 0.16, 64),
      new MeshBasicMaterial({ color: p.warning, transparent: true, opacity: 0, depthWrite: false }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.012;
    group.add(ring);
    const focus = new Mesh(
      new RingGeometry(reach + 0.14, reach + 0.3, 64),
      new MeshBasicMaterial({ color: p.primary, transparent: true, opacity: 0, depthWrite: false }),
    );
    focus.rotation.x = -Math.PI / 2;
    focus.position.y = 0.014;
    group.add(focus);

    this.#world.add(group);
    return { row, group, body, lamp, lampMat, ring, focus, ...parts, anchor: new Vector3(0, lampAt[1] + 0.45, 0) };
  }

  #disposeWorld() {
    if (!this.#world) return;
    this.#world.traverse((object) => {
      object.geometry?.dispose?.();
      const material = object.material;
      if (Array.isArray(material)) material.forEach((item) => item.dispose());
      else material?.dispose?.();
    });
    this.#scene?.remove(this.#world);
    this.#world = null;
    this.#machines = [];
    this.#labels = [];
    this.#chips = [];
  }

  // 状态、悬停与选中的着色。
  #paintStates() {
    const p = this.#palette;
    if (!p) return;
    for (const item of this.#machines) {
      const color = item.row.state === "running" ? p.success : item.row.state === "attention" ? p.warning : p.muted;
      item.lampMat.color.copy(color);
      item.lampMat.emissive.copy(color);
      item.lampMat.emissiveIntensity = item.row.state === "idle" ? 0.15 : 0.9;
      const selected = item.row.key === this.#selectedKey;
      const hovered = this.#hovered === item;
      item.focus.material.opacity = selected ? 0.95 : hovered ? 0.35 : 0;
      item.body.emissive.copy(p.primary);
      item.body.emissiveIntensity = hovered || selected ? 0.08 : 0;
      if (item.beam) item.beam.visible = item.row.state === "running";
    }
    this.#updateCallout();
    this.#dirty = true;
    this.#loop();
  }

  #updateCallout() {
    const callout = this.#callout;
    if (!callout) return;
    const item = this.#hovered ?? this.#machines.find((entry) => entry.row.key === this.#selectedKey);
    if (!item) {
      callout.hidden = true;
      callout.dataset.key = "";
      return;
    }
    const p = this.#palette;
    const text = this.#text;
    const row = item.row;
    const color = row.state === "running" ? p.success : row.state === "attention" ? p.warning : p.muted;
    const stateText = row.state === "attention" ? row.status : row.state === "running" ? text.runningN(row.running) : text.idle;
    if (callout.dataset.key !== `${row.key}|${row.state}`) {
      callout.dataset.key = `${row.key}|${row.state}`;
      callout.innerHTML = `<div class="name"></div><div class="meta"><i class="dot"></i><span class="state"></span></div>`;
      callout.querySelector(".name").textContent = row.name;
      callout.querySelector(".dot").style.background = `#${color.getHexString()}`;
      const parts = [stateText, row.queued ? text.queuedN(row.queued) : "", row.kind];
      callout.querySelector(".state").textContent = parts.filter(Boolean).join(" · ");
    }
    callout.hidden = false;
    callout._anchor = item;
  }

  // ---- 相机 ----

  #sizeTo(width, height) {
    if (!this.#renderer || !width || !height) return;
    this.#renderer.setSize(width, height, false);
    this.#camera.aspect = width / height;
    this.#camera.updateProjectionMatrix();
    if (this.#built && !this.#userMoved) this.#fit(false);
    this.#dirty = true;
    this.#loop();
  }

  #userMoved = false;

  #fit(animate, intro = false) {
    if (!this.#camera) return;
    const { width = 20, depth = 12, center } = this.#bounds;
    const target = center.clone();
    const pitch = MathUtils.degToRad(50);
    const yaw = MathUtils.degToRad(-12);
    const dir = new Vector3(Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), Math.cos(yaw) * Math.cos(pitch));
    // 找最近的距离，使地面、每台设备与标签都落在画面里；再按投影的偏移把画面居中。
    const probe = this.#camera.clone();
    const points = this.#fitPoints.length
      ? this.#fitPoints
      : [new Vector3(-width / 2, 0, -depth / 2), new Vector3(width / 2, 2, depth / 2)];
    const v = new Vector3();
    const extent = (distance) => {
      probe.position.copy(dir).multiplyScalar(distance).add(target);
      probe.lookAt(target);
      probe.updateMatrixWorld();
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (const point of points) {
        v.copy(point).project(probe);
        minX = Math.min(minX, v.x);
        maxX = Math.max(maxX, v.x);
        minY = Math.min(minY, v.y);
        maxY = Math.max(maxY, v.y);
      }
      return { minX, maxX, minY, maxY };
    };
    const fits = (distance) => {
      const e = extent(distance);
      return e.minX >= -0.94 && e.maxX <= 0.94 && e.minY >= -0.78 && e.maxY <= 0.8;
    };
    let distance = 20;
    for (let round = 0; round < 3; round++) {
      let lo = 1;
      let hi = 400;
      for (let i = 0; i < 28; i++) {
        const mid = (lo + hi) / 2;
        if (fits(mid)) hi = mid;
        else lo = mid;
      }
      distance = hi;
      const e = extent(distance);
      const offX = (e.minX + e.maxX) / 2;
      const offY = (e.minY + e.maxY) / 2 + 0.02;
      if (Math.abs(offX) < 0.01 && Math.abs(offY) < 0.01) break;
      const halfH = Math.tan(MathUtils.degToRad(probe.fov) / 2) * distance;
      const right = new Vector3().setFromMatrixColumn(probe.matrixWorld, 0);
      const forward = new Vector3(-dir.x, 0, -dir.z).normalize();
      target.addScaledVector(right, offX * halfH * probe.aspect);
      // 竖直方向的偏移沿地面前后移动目标，保持俯角不变。
      target.addScaledVector(forward, (offY * halfH) / Math.sin(pitch));
    }
    const end = dir.clone().multiplyScalar(distance).add(target);
    this.#controls.minDistance = distance * 0.3;
    this.#controls.maxDistance = distance * 2;
    this.#userMoved = false;
    if ((animate || intro) && !this.#reduced) {
      const start = intro
        ? new Vector3(Math.sin(yaw - 0.6) * Math.cos(pitch + 0.2), Math.sin(pitch + 0.2), Math.cos(yaw - 0.6) * Math.cos(pitch + 0.2))
            .multiplyScalar(distance * 1.25)
            .add(target)
        : this.#camera.position.clone();
      this.#intro = { start, end, from: this.#controls.target.clone(), to: target, t: 0, duration: intro ? 1.6 : 0.7 };
    } else if (this.#intro) {
      // 开场动画还在走：只改它的终点。
      this.#intro.end = end;
      this.#intro.to = target;
    } else {
      this.#camera.position.copy(end);
      this.#controls.target.copy(target);
      this.#controls.update();
    }
    this.#dirty = true;
    this.#loop();
  }

  // ---- 交互 ----

  #pick(event) {
    if (!this.#camera || !this.#machines.length) return null;
    const rect = this.#canvas.getBoundingClientRect();
    const pointer = new Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    const ray = new Raycaster();
    ray.setFromCamera(pointer, this.#camera);
    const hits = ray.intersectObjects(
      this.#machines.map((item) => item.group),
      true,
    );
    for (const hit of hits) {
      let node = hit.object;
      while (node && node.userData.machine === undefined) node = node.parent;
      if (node) return this.#machines.find((item) => item.row.index === node.userData.machine) ?? null;
    }
    return null;
  }

  #onHover(event) {
    if (event.buttons) return;
    this.#setHovered(this.#pick(event));
  }

  #setHovered(item) {
    if (item === this.#hovered) return;
    this.#hovered = item;
    this.#canvas.style.cursor = item && this.#mode === "run" ? "pointer" : "";
    this.#paintStates();
  }

  #onPointerUp(event) {
    const down = this.#down;
    this.#down = null;
    if (!down || Math.hypot(event.clientX - down.x, event.clientY - down.y) > 5) {
      if (down) this.#userMoved = true;
      return;
    }
    const item = this.#pick(event);
    if (event.pointerType !== "mouse") this.#setHovered(null);
    if (!item) return;
    this.#choose(item);
  }

  #choose(item) {
    if (this.#mode !== "run" || !item.row.object) return;
    // 点一台选中（打开详情），再点同一台取消。
    const again = this.#selectedKey === item.row.key;
    this.dispatchEvent(
      new CustomEvent("workshop:select", {
        bubbles: true,
        composed: true,
        detail: { objectType: item.row.object.type, ids: again ? [] : [item.row.object.id] },
      }),
    );
  }

  #onKey(event) {
    // 键盘：左右键在设备间移动，回车选中，Esc 回到全景。
    if (!this.#machines.length) return;
    if (event.key === "Escape") {
      this.#fit(true);
      return;
    }
    if (event.key === "Enter" && this.#hovered) {
      this.#choose(this.#hovered);
      return;
    }
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
    event.preventDefault();
    const index = this.#hovered ? this.#machines.indexOf(this.#hovered) : -1;
    const step = event.key === "ArrowRight" ? 1 : -1;
    const next = this.#machines[(index + step + this.#machines.length) % this.#machines.length];
    this.#setHovered(next);
  }

  // ---- 渲染循环 ----

  #loop() {
    if (this.#frame || !this.#renderer || !this.#visible) return;
    this.#frame = requestAnimationFrame((time) => this.#tick(time));
  }

  #tick(time) {
    this.#frame = 0;
    if (!this.#renderer || !this.#built) return;
    const dt = Math.min(0.05, this.#clock ? (time - this.#clock) / 1000 : 0.016);
    this.#clock = time;
    let animating = false;

    if (this.#intro) {
      const intro = this.#intro;
      intro.t = Math.min(1, intro.t + dt / intro.duration);
      const k = 1 - Math.pow(1 - intro.t, 3);
      this.#camera.position.lerpVectors(intro.start, intro.end, k);
      this.#controls.target.lerpVectors(intro.from, intro.to, k);
      if (intro.t >= 1) this.#intro = null;
      animating = true;
    }
    if (this.#controls.update()) animating = true;

    if (!this.#reduced) {
      const seconds = time / 1000;
      for (const item of this.#machines) {
        const state = item.row.state;
        if (state === "running") {
          for (const spinner of item.spinners) spinner.mesh.rotation[spinner.axis] += spinner.speed * dt;
          if (item.probe) item.probe.position.x = Math.sin(seconds * 1.2) * 0.55;
          if (item.needle) item.needle.rotation.z = Math.sin(seconds * 2) * 0.9;
          if (item.beam) item.beam.material.opacity = 0.5 + 0.4 * Math.abs(Math.sin(seconds * 9));
          animating = true;
        }
        if (state === "attention") {
          const pulse = 0.5 + 0.5 * Math.sin(seconds * 3.2);
          item.ring.material.opacity = 0.25 + 0.6 * pulse;
          item.lampMat.emissiveIntensity = 0.3 + 0.9 * pulse;
          animating = true;
        }
      }
    } else {
      for (const item of this.#machines) if (item.row.state === "attention") item.ring.material.opacity = 0.7;
    }

    this.#renderer.render(this.#scene, this.#camera);
    this.#placeLabels();
    this.#dirty = false;
    if (animating) this.#loop();
  }

  #placeLabels() {
    const canvas = this.#canvas;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const v = new Vector3();
    const place = (el, point) => {
      v.copy(point).project(this.#camera);
      const visible = v.z < 1 && v.x > -1.2 && v.x < 1.2 && v.y > -1.2 && v.y < 1.2;
      el.style.visibility = visible ? "visible" : "hidden";
      if (visible) {
        const x = ((v.x + 1) / 2) * width;
        const y = ((1 - v.y) / 2) * height;
        const base = el.classList.contains("bay") || el.classList.contains("site") ? "translate(0, -100%)" : "translate(-50%, -100%)";
        el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) ${base}`;
      }
    };
    for (const label of this.#labels) place(label.el, label.point);
    const shown = this.#callout && !this.#callout.hidden ? this.#callout._anchor : null;
    for (const chip of this.#chips) {
      if (chip.item === shown) chip.el.style.visibility = "hidden";
      else place(chip.el, chip.item.group.localToWorld(chip.item.anchor.clone()));
    }
    const callout = this.#callout;
    if (callout && !callout.hidden && callout._anchor) {
      const anchor = callout._anchor;
      place(callout, anchor.group.localToWorld(anchor.anchor.clone()));
    }
  }

  // ---- 给页面 Agent ----

  #describe() {
    if (!this.#workshop) return;
    const { rows } = this.#rows();
    if (!rows) return;
    const sites = new Set(rows.map((row) => row.site));
    const groups = new Set(rows.map((row) => `${row.site}|${row.group}`));
    const busiest = rows.reduce((best, row) => (row.queued > (best?.queued ?? 0) ? row : best), null);
    const selected = rows.find((row) => row.key === this.#selectedKey)?.name;
    const summary = this.#text
      .summary({
        sites: sites.size,
        groups: groups.size,
        machines: rows.length,
        running: rows.filter((row) => row.state === "running").map((row) => row.name).slice(0, 8),
        attention: rows.filter((row) => row.state === "attention").map((row) => `${row.name}：${row.status}`).slice(0, 8),
        busiest,
        selected,
      })
      .slice(0, 500);
    const details = {
      machines: rows.slice(0, 60).map((row) => ({
        id: row.key,
        name: row.name,
        workCenter: row.group,
        site: row.site,
        status: row.status,
        running: row.running,
        queued: row.queued,
      })),
      selected: this.#selectedKey,
    };
    try {
      this.#workshop.describe({ summary, details });
    } catch {
      // 页面不收这类说明时不影响显示。
    }
  }
}

function selectedKeyOf(value) {
  if (value == null) return null;
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (Array.isArray(value)) return value.length === 1 ? String(value[0]) : null;
  if (typeof value === "object" && Array.isArray(value.ids)) return value.ids.length === 1 ? String(value.ids[0]) : null;
  return null;
}

customElements.define("ai-line-twin", LineTwinElement);
