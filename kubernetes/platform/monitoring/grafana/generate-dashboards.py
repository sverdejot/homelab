"""Generates the Grafana dashboards in ./dashboards. Usage: python3 generate-dashboards.py"""
import json, sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboards")
DS = {"type": "prometheus", "uid": "${datasource}"}

# ---- palette (dark steps, validated against Grafana's dark panel surface #181b1f)
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
NODE_COLORS = {"homelab-0": BLUE, "homelab-1": ORANGE, "homelab-2": AQUA, "homelab-3": YELLOW}
GROUP_COLORS = {"Apps": BLUE, "Plataforma": ORANGE, "Infraestructura": AQUA}
GOOD, WARN, SERIOUS, CRIT = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
MUTED = "#898781"
RAM_COLOR, CPU_COLOR = BLUE, ORANGE  # one sequential hue per measure

PLATFORM_NS = "argocd|authentik|cert-manager|grafana|prometheus|cnpg-system|postgres"
INFRA_NS = "longhorn-system|metallb-system|ingress-nginx|kube-system|pihole-system"


def with_group(expr):
    """Add a 'grupo' label derived from namespace: Apps (default) / Plataforma / Infraestructura."""
    e = f'label_replace({expr}, "grupo", "Apps", "namespace", ".*")'
    e = f'label_replace({e}, "grupo", "Plataforma", "namespace", "{PLATFORM_NS}")'
    return f'label_replace({e}, "grupo", "Infraestructura", "namespace", "{INFRA_NS}")'


# pod -> workload (Deployment/StatefulSet/DaemonSet/...) via kube-state-metrics owner refs
W = (
    'label_replace('
    'max by (namespace, pod, workload) (label_replace(kube_pod_owner{owner_kind!~"ReplicaSet|<none>"}, "workload", "$1", "owner_name", "(.+)"))'
    ' or max by (namespace, pod, workload) (label_replace(kube_pod_owner{owner_kind="<none>"}, "workload", "$1", "pod", "(.+)"))'
    ' or max by (namespace, pod, workload) (label_replace(kube_pod_owner{owner_kind="ReplicaSet"}, "replicaset", "$1", "owner_name", "(.+)")'
    ' * on (namespace, replicaset) group_left (workload) max by (namespace, replicaset, workload) (label_replace(kube_replicaset_owner, "workload", "$1", "owner_name", "(.+)")))'
    ', "workload", "instance-manager", "workload", "instance-manager-.+")'
)


def by_workload(pod_expr):
    return f'sum by (namespace, workload) (({pod_expr}) * on (namespace, pod) group_left (workload) ({W}))'


# ---------------------------------------------------------------- building blocks
class Dash:
    def __init__(self):
        self.panels, self.y, self.id, self.x, self.rowh = [], 0, 1, 0, 0
        self.cur_row = None

    def row(self, title, collapsed=False):
        self.end_row()
        r = {"type": "row", "title": title, "collapsed": collapsed, "id": self.id,
             "gridPos": {"h": 1, "w": 24, "x": 0, "y": self.y}, "panels": []}
        self.id += 1
        self.y += 1
        self.panels.append(r)
        self.cur_row = r if collapsed else None

    def add(self, p, w, h):
        if self.x + w > 24:
            self.end_row()
        p["id"] = self.id
        self.id += 1
        p["gridPos"] = {"h": h, "w": w, "x": self.x, "y": self.y}
        p.setdefault("datasource", DS)
        (self.cur_row["panels"] if self.cur_row else self.panels).append(p)
        self.x += w
        self.rowh = max(self.rowh, h)
        if self.x >= 24:
            self.end_row()

    def end_row(self):
        if self.x:
            self.y += self.rowh
            self.x, self.rowh = 0, 0


def tgt(expr, legend="", ref="A", instant=False, fmt="time_series"):
    t = {"datasource": DS, "expr": expr, "legendFormat": legend, "refId": ref}
    if instant:
        t.update({"instant": True, "range": False, "format": fmt})
    else:
        t.update({"range": True, "instant": False})
    return t


def thresholds(steps):
    return {"mode": "absolute", "steps": [{"color": c, "value": v} for v, c in steps]}


def fixed(color):
    return {"mode": "fixed", "fixedColor": color}


def color_overrides(mapping):
    return [{"matcher": {"id": "byName", "options": n},
             "properties": [{"id": "color", "value": fixed(c)}]} for n, c in mapping.items()]


def value_color_mappings(mapping):
    return [{"type": "value", "options": {k: {"color": c, "index": i} for i, (k, c) in enumerate(mapping.items())}}]


BLUE_RAMP = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
ORANGE_RAMP = ["#5c2208", "#86330e", "#b04516", "#d95926", "#e9784a", "#f3a07c", "#fbcdb6"]


def ramp(colors, breaks):
    """Sequential thresholds: dark (near zero, recedes into the dark surface) -> light (high)."""
    return [(None, colors[0])] + list(zip(breaks, colors[1:]))


def gauge(title, targets, unit, thr, desc="", minv=0, maxv=100, overrides=None, decimals=0):
    return {"type": "gauge", "title": title, "description": desc, "targets": targets,
            "fieldConfig": {"defaults": {"unit": unit, "min": minv, "max": maxv, "decimals": decimals,
                                         "color": {"mode": "thresholds"}, "thresholds": thresholds(thr)},
                            "overrides": overrides or []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "showThresholdMarkers": True, "showThresholdLabels": False, "orientation": "auto",
                        "sizing": "auto", "minVizHeight": 75, "minVizWidth": 75}}


def status_history(title, expr, legend, unit, thr, desc="", decimals=0):
    return {"type": "status-history", "title": title, "description": desc,
            "targets": [tgt(expr, legend)], "interval": "5m", "maxDataPoints": 120,
            "fieldConfig": {"defaults": {"unit": unit, "decimals": decimals, "color": {"mode": "thresholds"},
                                         "thresholds": thresholds(thr),
                                         "custom": {"fillOpacity": 85, "lineWidth": 0, "hideFrom": {"legend": False, "tooltip": False, "viz": False}}},
                            "overrides": []},
            "options": {"showValue": "never", "rowHeight": 0.85, "colWidth": 0.92,
                        "legend": {"showLegend": False, "displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "single", "sort": "none"}}}


def ts(title, targets, unit="short", desc="", stack=False, minv=None, maxv=None, overrides=None,
       thr=None, decimals=None, palette="classic-by-name"):
    custom = {"drawStyle": "line", "lineWidth": 2, "fillOpacity": 35 if stack else 15, "gradientMode": "opacity",
              "showPoints": "never", "spanNulls": True, "lineInterpolation": "smooth",
              "stacking": {"mode": "normal" if stack else "none", "group": "A"},
              "axisBorderShow": False, "axisPlacement": "auto",
              "thresholdsStyle": {"mode": "line" if thr else "off"}}
    defaults = {"unit": unit, "custom": custom, "color": {"mode": f"palette-{palette}" if palette else "fixed"}}
    if thr:
        defaults["thresholds"] = thresholds(thr)
    for k, v in (("min", minv), ("max", maxv), ("decimals", decimals)):
        if v is not None:
            defaults[k] = v
    return {"type": "timeseries", "title": title, "description": desc, "targets": targets,
            "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
            "options": {"legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
                        "tooltip": {"mode": "multi", "sort": "desc"}}}


def stat(title, expr, unit, color=BLUE, desc="", decimals=None, thr=None, spark=True):
    d = {"unit": unit, "color": fixed(color) if not thr else {"mode": "thresholds"}}
    if thr:
        d["thresholds"] = thresholds(thr)
    if decimals is not None:
        d["decimals"] = decimals
    return {"type": "stat", "title": title, "description": desc,
            "targets": [tgt(expr, title)],
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "textMode": "value", "colorMode": "value", "graphMode": "area" if spark else "none",
                        "justifyMode": "center", "orientation": "auto", "wideLayout": True}}


def bargauge(title, targets, unit, steps=None, desc="", maxv=None):
    d = {"unit": unit, "min": 0, "decimals": 0, "thresholds": thresholds(steps or [(None, BLUE)]),
         "color": {"mode": "thresholds"}}
    if maxv is not None:
        d["max"] = maxv
    return {"type": "bargauge", "title": title, "description": desc, "targets": targets,
            "fieldConfig": {"defaults": d, "overrides": []},
            "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "valueMode": "text", "namePlacement": "left", "sizing": "manual", "minVizHeight": 16,
                        "maxVizHeight": 26, "minVizWidth": 8}}


def ranking(title, expr, legend, unit, color, desc=""):
    return {"type": "bargauge", "title": title, "description": desc,
            "targets": [tgt(f"sort_desc({expr})", legend, instant=True)],
            "fieldConfig": {"defaults": {"unit": unit, "min": 0, "color": fixed(color), "decimals": 0},
                            "overrides": []},
            "options": {"orientation": "horizontal", "displayMode": "gradient", "showUnfilled": True,
                        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
                        "valueMode": "text", "namePlacement": "left", "sizing": "manual", "minVizHeight": 16,
                        "maxVizHeight": 22, "minVizWidth": 8}}


def table(title, queries, rename, sort_by, labels, field_props, desc=""):
    """queries: list of (refId, expr) merged into one row per label set.
    field_props: {display name: [override properties]}"""
    targets = [tgt(e, ref=r, instant=True, fmt="table") for r, e in queries]
    order = {l: i for i, l in enumerate(labels)}
    for i, (r, _) in enumerate(queries):
        order[f"Value #{r}"] = len(labels) + i
    overrides = [{"matcher": {"id": "byName", "options": n}, "properties": p} for n, p in field_props.items()]
    return {"type": "table", "title": title, "description": desc, "targets": targets,
            "transformations": [
                {"id": "merge", "options": {}},
                {"id": "organize", "options": {"excludeByName": {"Time": True}, "indexByName": order,
                                               "renameByName": rename, "includeByName": {}}},
                {"id": "filterFieldsByName", "options": {"include": {"names": [rename.get(l, l) for l in labels] + [v for k, v in rename.items() if k.startswith("Value")]}}},
            ],
            "fieldConfig": {"defaults": {"custom": {"align": "auto", "filterable": False,
                                                    "cellOptions": {"type": "auto"}}},
                            "overrides": overrides},
            "options": {"showHeader": True, "cellHeight": "md", "sortBy": [{"displayName": sort_by, "desc": True}],
                        "footer": {"show": False}}}


# table cell styles
def unit(u, decimals=None):
    p = [{"id": "unit", "value": u}]
    if decimals is not None:
        p.append({"id": "decimals", "value": decimals})
    return p


def bar_cell(u, color, maxv=None, decimals=0):
    p = unit(u, decimals) + [{"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "gradient", "valueDisplayMode": "text"}},
                             {"id": "color", "value": fixed(color)}, {"id": "min", "value": 0}]
    if maxv is not None:
        p.append({"id": "max", "value": maxv})
    return p


def status_bar_cell(u, thr, maxv=100, decimals=0):
    return unit(u, decimals) + [{"id": "custom.cellOptions", "value": {"type": "gauge", "mode": "gradient", "valueDisplayMode": "text"}},
                                {"id": "color", "value": {"mode": "thresholds"}}, {"id": "thresholds", "value": thresholds(thr)},
                                {"id": "min", "value": 0}, {"id": "max", "value": maxv}]


def status_text_cell(u, thr, decimals=None):
    return unit(u, decimals) + [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
                                {"id": "color", "value": {"mode": "thresholds"}}, {"id": "thresholds", "value": thr}]


def muted_cell(u, decimals=0):
    return unit(u, decimals) + [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
                                {"id": "color", "value": fixed(MUTED)}]


def entity_cell(colors, width=None):
    p = [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
         {"id": "mappings", "value": value_color_mappings(colors)}, {"id": "color", "value": fixed("text")}]
    if width:
        p.append({"id": "custom.width", "value": width})
    return p


def dashboard(uid, title, desc, variables, panels, links):
    tmpl = [{"name": "datasource", "label": "Datasource", "type": "datasource", "query": "prometheus",
             "current": {}, "hide": 2, "refresh": 1, "options": [], "includeAll": False, "multi": False}] + variables
    return {"uid": uid, "title": title, "description": desc, "tags": ["homelab"], "timezone": "browser",
            "editable": True, "graphTooltip": 1, "refresh": "1m", "schemaVersion": 39, "version": 1,
            "time": {"from": "now-6h", "to": "now"}, "panels": panels, "templating": {"list": tmpl},
            "annotations": {"list": []},
            "links": [{"title": t, "type": "link", "url": u, "icon": "dashboard", "keepTime": True,
                       "includeVars": False, "targetBlank": False, "tooltip": "", "asDropdown": False, "tags": []}
                      for t, u in links]}


def query_var(name, label, query):
    return {"name": name, "label": label, "type": "query", "datasource": DS,
            "query": {"query": query, "refId": "PrometheusVariableQueryEditor-VariableQuery"},
            "definition": query, "refresh": 2, "sort": 1, "multi": True, "includeAll": True,
            "allValue": ".*", "current": {"selected": True, "text": ["All"], "value": ["$__all"]}, "hide": 0,
            "options": []}


STATUS_PCT = [(None, GOOD), (70, WARN), (85, SERIOUS), (95, CRIT)]
STATUS_TEMP = [(None, GOOD), (70, WARN), (78, SERIOUS), (82, CRIT)]

# ================================================================ Nodos
N = 'node=~"$node"'
CPU_PCT = f'100 * (1 - avg by (node) (rate(node_cpu_seconds_total{{mode="idle",{N}}}[__W__])))'
RAM_PCT = f'100 * (1 - node_memory_MemAvailable_bytes{{{N}}} / node_memory_MemTotal_bytes{{{N}}})'
TEMP = f'max by (node) (node_thermal_zone_temp{{type="cpu-thermal",{N}}})'
DISK_PCT = f'100 * (1 - node_filesystem_avail_bytes{{mountpoint="/",{N}}} / node_filesystem_size_bytes{{mountpoint="/",{N}}})'
SYSDISK = 'device=~"mmcblk[0-9]+|nvme[0-9]+n[0-9]+"'
node_overrides = color_overrides(NODE_COLORS)

d = Dash()
def radial(p):
    """Grafana 12.3 alpha 'New Gauge' panel (needs [panels] enable_alpha = true)."""
    p["type"] = "radialbar"
    p["options"].update({"shape": "gauge", "barWidthFactor": 0.55, "gradient": "auto", "sparkline": True,
                         "segmentCount": 1, "segmentSpacing": 0.3,
                         "effects": {"rounded": True, "barGlow": True, "spotlight": False, "centerGlow": False}})
    return p


def per_node(p):
    p.update({"repeat": "node", "repeatDirection": "h", "maxPerRow": 4})
    return p


d.row("Estado del clúster")
THERMO_JS = """
const ORDER = __ORDER__;
const STATUS = __STATUS__; // [[threshold, color], ...] ascending
const MIN = 40, MAX = 90, LIMIT = 80;

const vals = {};
context.panel.data.series.forEach((s) => {
  const f = s.fields.find((x) => x.type === "number");
  if (!f || !f.values.length) { return; }
  const name = (f.config && f.config.displayNameFromDS) || (f.labels && f.labels.node) || s.name;
  vals[name] = f.values[f.values.length - 1];
});
const nodes = ORDER.filter((n) => vals[n] !== undefined && vals[n] !== null);
const statusColor = (v) => { let c = STATUS[0][1]; STATUS.forEach((t) => { if (v >= t[0]) { c = t[1]; } }); return c; };
const band = (from, to, color, alpha) => [{ yAxis: from, itemStyle: { color: color, opacity: alpha } }, { yAxis: to }];

return {
  backgroundColor: "transparent",
  grid: { left: 44, right: 12, top: 26, bottom: 26 },
  tooltip: { trigger: "item", formatter: (p) => p.name + ": " + p.value.toFixed(1) + " °C" },
  xAxis: { type: "category", data: nodes, axisTick: { show: false },
           axisLine: { lineStyle: { color: "#383835" } }, axisLabel: { color: "#c3c2b7", fontSize: 11 } },
  yAxis: { type: "value", min: MIN, max: MAX, interval: 10,
           axisLabel: { color: "#898781", formatter: "{value}°" },
           splitLine: { lineStyle: { color: "#2c2c2a" } } },
  series: [{
    type: "bar", barWidth: "30%", barMaxWidth: 56,
    data: nodes.map((n) => ({ value: vals[n], itemStyle: { color: statusColor(vals[n]), borderRadius: [8, 8, 0, 0] } })),
    label: { show: true, position: "top", color: "#f0efec", fontSize: 13, fontWeight: 600,
             formatter: (p) => p.value.toFixed(0) + " °C" },
    markArea: { silent: true, data: [
      band(STATUS[1][0], STATUS[2][0], STATUS[1][1], 0.07),
      band(STATUS[2][0], STATUS[3][0], STATUS[2][1], 0.09),
      band(STATUS[3][0], MAX, STATUS[3][1], 0.11),
    ] },
    markLine: { silent: true, symbol: "none",
                lineStyle: { color: STATUS[3][1], width: 1.5, type: "solid" },
                label: { formatter: "80° baja frecuencia", color: STATUS[3][1], fontSize: 10, position: "insideEndTop" },
                data: [{ yAxis: LIMIT }] },
  }],
};
"""


def thermometer(title, targets, status, desc=""):
    js = (THERMO_JS.replace("__ORDER__", json.dumps(list(NODE_COLORS)))
          .replace("__STATUS__", json.dumps([[v if v is not None else -1e9, c] for v, c in status])))
    for t in targets:
        t.update({"instant": True, "range": False, "format": "time_series"})
    return {"type": "volkovlabs-echarts-panel", "title": title, "description": desc, "targets": targets,
            "options": {"renderer": "svg", "editorMode": "code", "editor": {"format": "auto"},
                        "getOption": js.strip(), "map": "none",
                        "themeEditor": {"name": "default", "config": "{}"}}}


PODS_JS = """
const ORDER = __ORDER__;
const COLORS = __COLORS__;
const SERIOUS = "__SERIOUS__", MUTED = "#898781";
const pods = {}, rst = {};
context.panel.data.series.forEach((s) => {
  const f = s.fields.find((x) => x.type === "number");
  if (!f || !f.values.length) { return; }
  const key = (f.config && f.config.displayNameFromDS) || s.name || "";
  const parts = key.split("|");
  const v = f.values[f.values.length - 1];
  if (parts[0] === "pods") { pods[parts[1]] = v; } else if (parts[0] === "rst") { rst[parts[1]] = v; }
});
const nodes = ORDER.filter((n) => pods[n] !== undefined);
const axisY = (i) => ({ type: "category", gridIndex: i, data: nodes, inverse: true, axisTick: { show: false },
                        axisLine: { show: false }, axisLabel: { color: "#c3c2b7", fontSize: 12 } });
const axisX = (i) => ({ type: "value", gridIndex: i, min: 0, show: false });
const titleStyle = { color: "#c3c2b7", fontSize: 13, fontWeight: 500 };

return {
  backgroundColor: "transparent",
  title: [{ text: "Pods en ejecución", left: 8, top: 4, textStyle: titleStyle },
          { text: "Reinicios de contenedores (24 h)", left: 8, top: "52%", textStyle: titleStyle }],
  tooltip: { trigger: "item", formatter: (p) => p.name + ": " + p.value },
  grid: [{ left: 82, right: 44, top: 34, height: "36%" }, { left: 82, right: 44, top: "60%", height: "34%" }],
  xAxis: [axisX(0), axisX(1)],
  yAxis: [axisY(0), axisY(1)],
  series: [
    { type: "bar", xAxisIndex: 0, yAxisIndex: 0, barWidth: "56%",
      showBackground: true, backgroundStyle: { color: "rgba(255,255,255,0.05)", borderRadius: 6 },
      data: nodes.map((n) => ({ value: pods[n], itemStyle: { color: COLORS[n], borderRadius: 6 } })),
      label: { show: true, position: "right", color: "#f0efec", fontSize: 13, fontWeight: 600 } },
    { type: "bar", xAxisIndex: 1, yAxisIndex: 1, barWidth: "56%", barMinHeight: 0,
      showBackground: true, backgroundStyle: { color: "rgba(255,255,255,0.05)", borderRadius: 6 },
      data: nodes.map((n) => ({ value: Math.round(rst[n] || 0), itemStyle: { color: SERIOUS, borderRadius: 6 } })),
      label: { show: true, position: "right", fontSize: 13, fontWeight: 600,
               formatter: (p) => "{" + (p.value > 0 ? "bad" : "ok") + "|" + p.value + "}",
               rich: { bad: { color: SERIOUS, fontSize: 13, fontWeight: 600 }, ok: { color: MUTED, fontSize: 13 } } } },
  ],
};
"""


def pods_restarts(title, targets, desc=""):
    js = (PODS_JS.replace("__ORDER__", json.dumps(list(NODE_COLORS)))
          .replace("__COLORS__", json.dumps(NODE_COLORS)).replace("__SERIOUS__", SERIOUS))
    for t in targets:
        t.update({"instant": True, "range": False, "format": "time_series"})
    return {"type": "volkovlabs-echarts-panel", "title": title, "description": desc, "targets": targets,
            "options": {"renderer": "svg", "editorMode": "code", "editor": {"format": "auto"},
                        "getOption": js.strip(), "map": "none",
                        "themeEditor": {"name": "default", "config": "{}"}}}


def per_node_targets(expr, legend="{{node}}", ref_offset=0):
    """One query per node so panels always list homelab-0..3 in order (still honours $node)."""
    return [tgt(f"max by (node) ({expr.replace('node=~\"$node\"', f'node=~\"$node\",node=\"{n}\"')})", legend, chr(65 + ref_offset + i))
            for i, n in enumerate(NODE_COLORS)]


RINGS_JS = """
const ORDER = __ORDER__;
const COLORS = __COLORS__;
const MIN = __MIN__, MAX = __MAX__, UNIT = "__UNIT__", DEC = __DEC__;
const STATUS = __STATUS__; // [[threshold, color], ...] ascending

const vals = {};
context.panel.data.series.forEach((s) => {
  const f = s.fields.find((x) => x.type === "number");
  if (!f || !f.values.length) { return; }
  const name = (f.config && f.config.displayNameFromDS) || (f.labels && f.labels.node) || s.name;
  vals[name] = f.values[f.values.length - 1];
});
const nodes = ORDER.filter((n) => vals[n] !== undefined && vals[n] !== null);
const fmt = (v) => (v === undefined || v === null ? "–" : v.toFixed(DEC) + UNIT);
const level = (v) => { let k = 0; STATUS.forEach((t, i) => { if (v >= t[0]) { k = i; } }); return "s" + k; };
const rich = { n: { fill: "#c3c2b7", fontSize: 12, width: 74 } };
STATUS.forEach((t, i) => { rich["s" + i] = { fill: t[1], fontSize: 14, fontWeight: 600 }; });

nodes.forEach((n, i) => { rich["d" + i] = { fill: COLORS[n], fontSize: 14, width: 16 }; });

return {
  backgroundColor: "transparent",
  tooltip: { trigger: "item", formatter: (p) => p.name + ": " + fmt(vals[p.name]) },
  polar: { radius: ["20%", "74%"], center: ["50%", "40%"] },
  angleAxis: { min: MIN, max: MAX, startAngle: 90, clockwise: true, show: false },
  radiusAxis: { type: "category", data: nodes, show: false, inverse: true },
  series: [{
    type: "bar", coordinateSystem: "polar", roundCap: true, barWidth: "62%",
    showBackground: true, backgroundStyle: { color: "rgba(255,255,255,0.06)" },
    data: nodes.map((n) => ({ name: n, value: Math.min(MAX, Math.max(MIN, vals[n])), itemStyle: { color: COLORS[n] } })),
  }],
  graphic: nodes.map((n, i) => ({
    type: "text", left: (i % 2 === 0 ? 6 : 52) + "%", top: (i < 2 ? 80 : 90) + "%",
    style: { text: "{d" + i + "|●}{n|" + n + "}{" + level(vals[n]) + "|" + fmt(vals[n]) + "}", rich: rich, fill: "#c3c2b7" },
  })),
};
"""


def rings(title, targets, unit_suffix, minv, maxv, status, decimals=0, desc=""):
    js = (RINGS_JS.replace("__ORDER__", json.dumps(list(NODE_COLORS)))
          .replace("__COLORS__", json.dumps(NODE_COLORS))
          .replace("__MIN__", str(minv)).replace("__MAX__", str(maxv))
          .replace("__UNIT__", unit_suffix).replace("__DEC__", str(decimals))
          .replace("__STATUS__", json.dumps([[v if v is not None else -1e9, c] for v, c in status])))
    for t in targets:
        t.update({"instant": True, "range": False, "format": "time_series"})
    return {"type": "volkovlabs-echarts-panel", "title": title, "description": desc, "targets": targets,
            "options": {"renderer": "svg", "editorMode": "code", "editor": {"format": "auto"},
                        "getOption": js.strip(), "map": "none",
                        "themeEditor": {"name": "default", "config": "{}"}}}


# one panel per measure, one dial per node
RUNNING_PODS = f'count by (node) (kube_pod_info{{{N}}} * on (namespace, pod) group_left () (kube_pod_status_phase{{phase="Running"}} == 1))'
for title, expr, u, thr, extra in (
    ("CPU", CPU_PCT.replace("__W__", "5m"), "percent", STATUS_PCT, {}),
    ("RAM", RAM_PCT, "percent", STATUS_PCT, {}),
    ("Disco", DISK_PCT, "percent", STATUS_PCT, {}),
):
    d.add(rings(title, per_node_targets(expr), " °C" if u == "celsius" else "%",
                extra.get("minv", 0), extra.get("maxv", 100), thr,
                desc="Un anillo por nodo. El valor de la leyenda se colorea por estado: verde = normal · ámbar = vigilar · naranja = atención · rojo = actuar."
                     + (" Escala 30–90 °C." if title == "Temperatura" else "")), 6, 8)
RESTARTS_24H = (f'sum by (node) (increase(kube_pod_container_status_restarts_total[24h])'
                f' * on (namespace, pod) group_left (node) max by (namespace, pod, node) (kube_pod_info{{{N}}}))')
top = d.y  # rings were placed at x=0,6,12 on this line
d.x, d.rowh = 0, 0
d.panels.append(dict(pods_restarts("Pods y reinicios",
                                   per_node_targets(RUNNING_PODS, "pods|{{node}}", 0)
                                   + per_node_targets(RESTARTS_24H, "rst|{{node}}", 4),
                                   desc="Reinicios = reinicios de contenedores en las últimas 24 h, sumados por nodo."),
                     id=d.id, datasource=DS, gridPos={"h": 16, "w": 6, "x": 18, "y": top}))
d.id += 1
d.panels.append(dict(thermometer("Temperatura", per_node_targets(TEMP), STATUS_TEMP,
                                 desc="Franjas: ámbar ≥ 70 °C · naranja ≥ 78 °C · rojo ≥ 82 °C. A 80 °C la Pi 5 baja la frecuencia."),
                     id=d.id, datasource=DS, gridPos={"h": 8, "w": 18, "x": 0, "y": top + 8}))
d.id += 1
d.y = top + 16

d.row("Historial de estado")
d.add(status_history("CPU", CPU_PCT.replace("__W__", "$__interval"), "{{node}}", "percent", STATUS_PCT), 8, 6)
d.add(status_history("RAM", RAM_PCT, "{{node}}", "percent", STATUS_PCT), 8, 6)
d.add(status_history("Temperatura", TEMP, "{{node}}", "celsius", STATUS_TEMP, decimals=1,
                     desc="Cada celda es un intervalo de 5 minutos coloreado por su estado."), 8, 6)

d.row("Comparativa")
d.add(ts("CPU", [tgt(CPU_PCT.replace("__W__", "$__rate_interval"), "{{node}}")], "percent", minv=0, maxv=100,
         overrides=node_overrides, decimals=0), 12, 9)
d.add(ts("RAM", [tgt(RAM_PCT, "{{node}}")], "percent", minv=0, maxv=100, overrides=node_overrides, decimals=0,
         desc="Memoria en uso (sin contar caché liberable) sobre los 8 GB de cada nodo."), 12, 9)
d.add(ts("Temperatura", [tgt(TEMP, "{{node}}")], "celsius", overrides=node_overrides, decimals=1,
         thr=[(None, "transparent"), (80, CRIT)], desc="La línea roja marca 80 °C, donde la Pi empieza a bajar frecuencia."), 12, 9)
d.add(ts("Escritura en disco", [tgt(f'sum by (node) (rate(node_disk_written_bytes_total{{{SYSDISK},{N}}}[$__rate_interval]))', "{{node}}")],
         "Bps", minv=0, overrides=node_overrides,
         desc="Disco del sistema: SD en los agentes, NVMe en homelab-0. Las escrituras son lo que desgasta la SD."), 12, 9)

d.row("Más detalle", collapsed=True)
d.add(ts("Lectura de disco", [tgt(f'sum by (node) (rate(node_disk_read_bytes_total{{{SYSDISK},{N}}}[$__rate_interval]))', "{{node}}")],
         "Bps", minv=0, overrides=node_overrides), 12, 8)
d.add(ts("Disco ocupado", [tgt(f'100 * max by (node) (rate(node_disk_io_time_seconds_total{{{SYSDISK},{N}}}[$__rate_interval]))', "{{node}}")],
         "percent", minv=0, maxv=100, overrides=node_overrides, decimals=0,
         desc="% del tiempo con operaciones en curso. Cerca de 100% = disco saturado."), 12, 8)
d.add(ts("Red: entrada", [tgt(f'rate(node_network_receive_bytes_total{{device="end0",{N}}}[$__rate_interval])', "{{node}}")],
         "Bps", minv=0, overrides=node_overrides), 12, 8)
d.add(ts("Red: salida", [tgt(f'rate(node_network_transmit_bytes_total{{device="end0",{N}}}[$__rate_interval])', "{{node}}")],
         "Bps", minv=0, overrides=node_overrides), 12, 8)
d.add(ts("Carga por núcleo", [tgt(f'node_load1{{{N}}} / on (node) count by (node) (node_cpu_seconds_total{{mode="idle",{N}}})', "{{node}}")],
         "short", minv=0, overrides=node_overrides, decimals=2,
         desc="load1 / núcleos. Por encima de 1 hay procesos esperando CPU o disco."), 12, 8)
d.add(ts("Espacio libre en /", [tgt(f'node_filesystem_avail_bytes{{mountpoint="/",{N}}}', "{{node}}")],
         "bytes", minv=0, overrides=node_overrides), 12, 8)

nodes = dashboard("homelab-nodes", "Nodos", "Estado de los nodos del clúster",
                  [query_var("node", "Nodo", "label_values(node_uname_info, node)")], d.panels,
                  [("Aplicaciones", "/d/homelab-apps/aplicaciones")])

# ================================================================ Aplicaciones
NS = 'namespace=~"$namespace"'
MEM = f'container_memory_working_set_bytes{{container!="",{NS}}}'
CPU = f'rate(container_cpu_usage_seconds_total{{container!="",{NS}}}[5m])'
CPUR = f'rate(container_cpu_usage_seconds_total{{container!="",{NS}}}[$__rate_interval])'
REQ = lambda r: f'kube_pod_container_resource_requests{{resource="{r}",{NS}}}'
LIM = lambda r: f'kube_pod_container_resource_limits{{resource="{r}",{NS}}}'
RST = f'kube_pod_container_status_restarts_total{{{NS}}}'
RUNNING = f'kube_pod_info{{{NS}}} * on (namespace, pod) group_left () (kube_pod_status_phase{{phase="Running"}} == 1)'
CPU_UNIT = "suffix:m"
RESTART_THR = thresholds([(None, MUTED), (1, SERIOUS)])

d = Dash()
d.row("Resumen")
d.add(stat("RAM de los pods", f'sum({MEM})', "bytes", RAM_COLOR, decimals=1), 6, 5)
d.add(stat("CPU de los pods", f'1000 * sum({CPUR})', CPU_UNIT, CPU_COLOR, decimals=0,
           desc="Milicores: 1000m = 1 núcleo. El clúster tiene 16 núcleos."), 6, 5)
d.add(gauge("RAM del clúster", [tgt(f'100 * sum({MEM}) / sum(node_memory_MemTotal_bytes)', "RAM")],
            "percent", STATUS_PCT, desc="Working set de los pods sobre la RAM total de los 4 nodos (32 GB)."), 6, 5)
d.add(stat("Pods en ejecución", f'count({RUNNING})', "short", "text", decimals=0, spark=False), 6, 5)

d.add(ranking("RAM por namespace", f'sum by (namespace) ({MEM})', "{{namespace}}", "bytes", RAM_COLOR), 12, 11)
d.add(ranking("CPU por namespace", f'1000 * sum by (namespace) ({CPU})', "{{namespace}}", CPU_UNIT, CPU_COLOR,
              desc="Media de los últimos 5 minutos, en milicores."), 12, 11)

MiB = 2 ** 20
d.row("Mapa de calor por namespace")
d.add(status_history("RAM", f'sum by (namespace) ({MEM})', "{{namespace}}", "bytes",
                     ramp(BLUE_RAMP, [32 * MiB, 64 * MiB, 128 * MiB, 256 * MiB, 512 * MiB, 1024 * MiB]),
                     desc="Más claro = más RAM. Escala: 32, 64, 128, 256, 512 MiB, 1 GiB."), 12, 11)
d.add(status_history("CPU", f'1000 * sum by (namespace) (rate(container_cpu_usage_seconds_total{{container!="",{NS}}}[$__interval]))',
                     "{{namespace}}", CPU_UNIT, ramp(ORANGE_RAMP, [5, 10, 25, 50, 100, 200]),
                     desc="Más claro = más CPU. Escala: 5, 10, 25, 50, 100, 200 milicores."), 12, 11)

grp_overrides = color_overrides(GROUP_COLORS)
d.row("Evolución por grupo")
d.add(ts("RAM", [tgt(f'sum by (grupo) ({with_group(f"sum by (namespace) ({MEM})")})', "{{grupo}}")], "bytes",
         stack=True, minv=0, overrides=grp_overrides, palette=None,
         desc=f"Apps: el resto. Plataforma: {PLATFORM_NS.replace('|', ', ')}. Infraestructura: {INFRA_NS.replace('|', ', ')}."), 12, 9)
d.add(ts("CPU", [tgt(f'1000 * sum by (grupo) ({with_group(f"sum by (namespace) ({CPUR})")})', "{{grupo}}")], CPU_UNIT,
         stack=True, minv=0, overrides=grp_overrides, palette=None, decimals=0), 12, 9)

d.row("Detalle por namespace")
d.add(table("Consumo por namespace", [
    ("A", with_group(f'sum by (namespace) ({MEM})')),
    ("B", with_group(f'1000 * sum by (namespace) ({CPU})')),
    ("C", with_group(f'sum by (namespace) ({REQ("memory")})')),
    ("D", with_group(f'sum by (namespace) ({LIM("memory")})')),
    ("E", with_group(f'1000 * sum by (namespace) ({REQ("cpu")})')),
    ("F", with_group(f'count by (namespace) ({RUNNING})')),
    ("G", with_group(f'sum by (namespace) (round(increase({RST}[$__range])))')),
], {"namespace": "Namespace", "grupo": "Grupo", "Value #A": "RAM", "Value #B": "CPU", "Value #C": "RAM pedida",
    "Value #D": "RAM límite", "Value #E": "CPU pedida", "Value #F": "Pods", "Value #G": "Reinicios"},
    "RAM", ["namespace", "grupo"], {
        "Grupo": entity_cell(GROUP_COLORS, 150),
        "RAM": bar_cell("bytes", RAM_COLOR, 1024 ** 3),
        "CPU": bar_cell(CPU_UNIT, CPU_COLOR, 250),
        "RAM pedida": muted_cell("bytes"),
        "RAM límite": muted_cell("bytes"),
        "CPU pedida": muted_cell(CPU_UNIT),
        "Pods": unit("short", 0) + [{"id": "custom.width", "value": 80}],
        "Reinicios": status_text_cell("short", RESTART_THR, 0) + [{"id": "custom.width", "value": 100}],
    }, desc="Pedida = requests (lo que el scheduler reserva). Barras: RAM hasta 1 GB, CPU hasta 250m."), 24, 13)

d.row("Workloads (filtra un namespace arriba)")
d.add(ranking("RAM por workload", by_workload(f'sum by (namespace, pod) ({MEM})'), "{{namespace}} / {{workload}}",
              "bytes", RAM_COLOR), 12, 10)
d.add(ranking("CPU por workload", by_workload(f'1000 * sum by (namespace, pod) ({CPU})'), "{{namespace}} / {{workload}}",
              CPU_UNIT, CPU_COLOR), 12, 10)
d.add(table("Uso frente a requests", [
    ("A", by_workload(f'sum by (namespace, pod) ({MEM})')),
    ("B", f'max_over_time(({by_workload(f"sum by (namespace, pod) ({MEM})")})[$__range:5m])'),
    ("C", by_workload(f'sum by (namespace, pod) ({REQ("memory")})')),
    ("D", by_workload(f'sum by (namespace, pod) ({LIM("memory")})')),
    ("E", by_workload(f'1000 * sum by (namespace, pod) ({CPU})')),
    ("F", f'max_over_time(({by_workload(f"1000 * sum by (namespace, pod) ({CPU})")})[$__range:5m])'),
    ("G", by_workload(f'1000 * sum by (namespace, pod) ({REQ("cpu")})')),
], {"namespace": "Namespace", "workload": "Workload", "Value #A": "RAM", "Value #B": "RAM pico",
    "Value #C": "RAM pedida", "Value #D": "RAM límite", "Value #E": "CPU", "Value #F": "CPU pico", "Value #G": "CPU pedida"},
    "RAM pico", ["namespace", "workload"], {
        "RAM": bar_cell("bytes", RAM_COLOR, 1024 ** 3),
        "RAM pico": unit("bytes", 0),
        "RAM pedida": muted_cell("bytes"),
        "RAM límite": muted_cell("bytes"),
        "CPU": bar_cell(CPU_UNIT, CPU_COLOR, 250),
        "CPU pico": unit(CPU_UNIT, 0),
        "CPU pedida": muted_cell(CPU_UNIT),
    }, desc="Pico = máximo en el rango de tiempo elegido. Referencia para fijar requests (≈ uso normal) y límites (> pico)."), 24, 12)
d.add(table("Pods", [
    ("A", f'sum by (namespace, pod) ({MEM}) * on (namespace, pod) group_left (node) max by (namespace, pod, node) (kube_pod_info)'),
    ("B", f'1000 * sum by (namespace, pod) ({CPU})'),
    ("C", f'sum by (namespace, pod) ({RST}) * on (namespace, pod) group_left () max by (namespace, pod) ({RUNNING})'),
], {"namespace": "Namespace", "pod": "Pod", "node": "Nodo", "Value #A": "RAM", "Value #B": "CPU", "Value #C": "Reinicios"},
    "RAM", ["namespace", "pod", "node"], {
        "Nodo": entity_cell(NODE_COLORS, 120),
        "RAM": bar_cell("bytes", RAM_COLOR, 1024 ** 3),
        "CPU": bar_cell(CPU_UNIT, CPU_COLOR, 250),
        "Reinicios": status_text_cell("short", RESTART_THR, 0) + [{"id": "custom.width", "value": 100}],
    }, desc="Reinicios totales desde que se creó el pod."), 24, 12)

d.row("Estabilidad", collapsed=True)
d.add(ts("Reinicios de contenedores", [tgt(f'sum by (namespace, pod) (round(increase({RST}[$__rate_interval]))) > 0', "{{namespace}} / {{pod}}")],
         "short", minv=0, decimals=0), 12, 8)
d.add(table("Último reinicio por falta de memoria (OOMKilled)", [
    ("A", f'max by (namespace, pod, container) (kube_pod_container_status_last_terminated_reason{{reason="OOMKilled",{NS}}}) == 1'),
], {"namespace": "Namespace", "pod": "Pod", "container": "Contenedor"}, "Pod",
    ["namespace", "pod", "container"], {}, desc="Contenedores cuyo último reinicio fue por superar su límite de memoria."), 12, 8)

apps = dashboard("homelab-apps", "Aplicaciones", "Consumo de RAM y CPU por aplicación",
                 [query_var("namespace", "Namespace", "label_values(kube_pod_info, namespace)")], d.panels,
                 [("Nodos", "/d/homelab-nodes/nodos")])

# ================================================================ Almacenamiento
GiB = 2 ** 30
ROBUST_MAP = [{"type": "value", "options": {
    "0": {"text": "Desconectado", "color": MUTED, "index": 0},
    "1": {"text": "Sano", "color": GOOD, "index": 1},
    "2": {"text": "Degradado", "color": SERIOUS, "index": 2},
    "3": {"text": "Fallido", "color": CRIT, "index": 3}}}]
PROBLEM_THR = [(None, GOOD), (1, SERIOUS)]


def lh(expr):
    """Longhorn series -> namespace / persistentvolumeclaim labels, like kubelet's."""
    return f'label_replace(label_replace({expr}, "namespace", "$1", "pvc_namespace", "(.+)"), "persistentvolumeclaim", "$1", "pvc", "(.+)")'


ROBUSTNESS = ('(max by (pvc_namespace, pvc) (longhorn_volume_robustness{state="healthy"})'
              ' + 2 * max by (pvc_namespace, pvc) (longhorn_volume_robustness{state="degraded"})'
              ' + 3 * max by (pvc_namespace, pvc) (longhorn_volume_robustness{state="faulted"}))')
REPLICAS = 'count by (volume) (longhorn_replica_info)'
ACTUAL = 'max by (volume, pvc, pvc_namespace) (longhorn_volume_actual_size_bytes)'
SD = 'device="mmcblk0"'
ROOT_PCT = '100 * (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})'

d = Dash()
d.row("Resumen")
d.add(stat("Volúmenes", 'count(max by (volume) (longhorn_volume_capacity_bytes))', "short", "text", decimals=0, spark=False), 4, 4)
d.add(stat("Con problemas", '(count(max by (volume) (longhorn_volume_robustness{state=~"degraded|faulted"}) == 1) or vector(0))',
           "short", decimals=0, spark=False, thr=PROBLEM_THR, desc="Volúmenes degradados (les falta alguna réplica) o fallidos."), 4, 4)
d.add(stat("Ocupado en disco", f'sum({ACTUAL} * on (volume) group_left () {REPLICAS})', "bytes", BLUE, decimals=1,
           desc="Espacio real que ocupan los volúmenes en los discos de los nodos, contando todas sus réplicas."), 4, 4)
d.add(stat("PVC más llena", 'max(100 * kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes)', "percent",
           decimals=0, spark=False, thr=STATUS_PCT), 4, 4)
d.add(stat("Nodo más lleno", f'max({ROOT_PCT})', "percent", decimals=0, spark=False, thr=STATUS_PCT), 4, 4)
d.add(stat("SD escrito (24 h)", f'sum(increase(node_disk_written_bytes_total{{{SD}}}[24h]))', "bytes", ORANGE, decimals=1,
           desc="Suma de lo escrito en la tarjeta SD de todos los nodos en las últimas 24 horas. Es lo que desgasta las tarjetas."), 4, 4)

d.row("Volúmenes")
d.add(table("Volúmenes (PVC)", [
    ("A", '100 * max by (namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes / kubelet_volume_stats_capacity_bytes)'),
    ("B", 'max by (namespace, persistentvolumeclaim) (kubelet_volume_stats_used_bytes)'),
    ("C", 'max by (namespace, persistentvolumeclaim) (kube_persistentvolumeclaim_resource_requests_storage_bytes)'),
    ("D", lh(f'max by (pvc_namespace, pvc) ({ACTUAL})')),
    ("E", lh(f'max by (pvc_namespace, pvc) ({ACTUAL} * on (volume) group_left () {REPLICAS})')),
    ("F", lh(f'max by (pvc_namespace, pvc) (max by (volume, pvc, pvc_namespace) (longhorn_volume_actual_size_bytes) * 0 + on (volume) group_left () {REPLICAS})')),
    ("G", lh(ROBUSTNESS)),
], {"namespace": "Namespace", "persistentvolumeclaim": "PVC", "Value #A": "Ocupación", "Value #B": "Usado",
    "Value #C": "Tamaño", "Value #D": "Real por réplica", "Value #E": "Real total", "Value #F": "Réplicas", "Value #G": "Estado"},
    "Ocupación", ["namespace", "persistentvolumeclaim"], {
        "Ocupación": status_bar_cell("percent", STATUS_PCT),
        "Usado": unit("bytes", 1),
        "Tamaño": muted_cell("bytes"),
        "Real por réplica": unit("bytes", 1),
        "Real total": unit("bytes", 1),
        "Réplicas": unit("short", 0) + [{"id": "custom.width", "value": 90}],
        "Estado": [{"id": "mappings", "value": ROBUST_MAP}, {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                   {"id": "custom.width", "value": 120}],
    }, desc="Usado = datos dentro del volumen. Real = lo que ocupa en disco (incluye bloques ya borrados hasta que se hace trim). "
            "Si 'Real' es mucho mayor que 'Usado', el volumen necesita un trim."), 24, 10)
d.add(ts("Escritura por volumen", [tgt('max by (pvc_namespace, pvc) (longhorn_volume_write_throughput)', "{{pvc_namespace}} / {{pvc}}")],
         "Bps", minv=0, desc="Lo que cada aplicación escribe en su volumen. Longhorn lo multiplica por el número de réplicas en los discos."), 12, 9)
d.add(ts("Lectura por volumen", [tgt('max by (pvc_namespace, pvc) (longhorn_volume_read_throughput)', "{{pvc_namespace}} / {{pvc}}")],
         "Bps", minv=0), 12, 9)

d.row("Discos de los nodos")
d.add(bargauge("Disco del sistema ocupado", [tgt(f'max by (node) ({ROOT_PCT})', "{{node}}", instant=True)], "percent", STATUS_PCT, maxv=100), 8, 8)
d.add(bargauge("Longhorn: espacio usado del disco", [
    tgt('100 * max by (node) (longhorn_node_storage_usage_bytes) / max by (node) (longhorn_node_storage_capacity_bytes)', "{{node}}", instant=True)],
    "percent", STATUS_PCT, maxv=100, desc="Ocupación del disco donde Longhorn guarda las réplicas (en los agentes es la propia SD)."), 8, 8)
ranking_sd = ranking("Escrito en la SD (24 h)", f'max by (node) (increase(node_disk_written_bytes_total{{{SD}}}[24h]))', "{{node}}", "bytes", ORANGE)
ranking_sd["fieldConfig"]["overrides"] = color_overrides(NODE_COLORS)
d.add(ranking_sd, 8, 8)
d.add(ts("Escritura en la SD", [tgt(f'max by (node) (rate(node_disk_written_bytes_total{{{SD}}}[$__rate_interval]))', "{{node}}")],
         "Bps", minv=0, overrides=color_overrides(NODE_COLORS)), 12, 8)
d.add(ts("Espacio libre en /", [tgt('max by (node) (node_filesystem_avail_bytes{mountpoint="/"})', "{{node}}")],
         "bytes", minv=0, overrides=color_overrides(NODE_COLORS)), 12, 8)

storage = dashboard("homelab-storage", "Almacenamiento", "Volúmenes de Longhorn, PVCs y discos de los nodos", [], d.panels,
                    [("Salud del clúster", "/d/homelab-health/salud-del-cluster"), ("Nodos", "/d/homelab-nodes/nodos")])

# ================================================================ Salud del clúster
YESNO_OK = [{"type": "value", "options": {"0": {"text": "No", "color": GOOD, "index": 0}, "1": {"text": "Sí", "color": CRIT, "index": 1}}}]
READY_MAP = [{"type": "value", "options": {"1": {"text": "Sí", "color": GOOD, "index": 0}, "0": {"text": "No", "color": CRIT, "index": 1}}}]
CERT_DAYS = [(None, CRIT), (7, SERIOUS), (14, WARN), (30, GOOD)]
DEPLOY_BAD = 'label_replace(kube_deployment_status_replicas_unavailable > 0, "workload", "$1", "deployment", "(.+)")'
STS_BAD = ('label_replace(kube_statefulset_replicas - on (namespace, statefulset) kube_statefulset_status_replicas_ready > 0,'
           ' "workload", "$1", "statefulset", "(.+)")')
DS_BAD = 'label_replace(kube_daemonset_status_number_unavailable > 0, "workload", "$1", "daemonset", "(.+)")'
BAD_PODS = ('max by (namespace, pod, reason) (kube_pod_container_status_waiting_reason == 1)'
            ' or max by (namespace, pod, reason) (label_replace(kube_pod_status_phase{phase=~"Pending|Failed|Unknown"} == 1, "reason", "$1", "phase", "(.+)"))')
CERT_DAYS_EXPR = 'min by (namespace, name) ((certmanager_certificate_expiration_timestamp_seconds - time()) / 86400)'

d = Dash()
d.row("Problemas detectados")
d.add(stat("Nodos", 'count(kube_node_info) - (sum(kube_node_status_condition{condition="Ready",status="true"}) or vector(0))'
           ' + (count(kube_node_status_condition{condition=~".+Pressure",status="true"} == 1) or vector(0))',
           "short", decimals=0, spark=False, thr=PROBLEM_THR, desc="Nodos no listos o con presión de memoria, disco o procesos."), 4, 4)
d.add(stat("Pods", f'count({BAD_PODS}) or vector(0)', "short", decimals=0, spark=False, thr=PROBLEM_THR,
           desc="Pods pendientes, fallidos o con contenedores esperando (CrashLoopBackOff, ImagePullBackOff…)."), 4, 4)
d.add(stat("Workloads", f'count(({DEPLOY_BAD}) or ({STS_BAD}) or ({DS_BAD})) or vector(0)', "short", decimals=0,
           spark=False, thr=PROBLEM_THR, desc="Deployments, StatefulSets o DaemonSets con réplicas no disponibles."), 4, 4)
d.add(stat("Volúmenes", '(count(max by (volume) (longhorn_volume_robustness{state=~"degraded|faulted"}) == 1) or vector(0))',
           "short", decimals=0, spark=False, thr=PROBLEM_THR, desc="Volúmenes de Longhorn degradados o fallidos."), 4, 4)
d.add(stat("Reinicios (24 h)", 'sum(round(increase(kube_pod_container_status_restarts_total[24h])))', "short", decimals=0,
           spark=False, thr=PROBLEM_THR), 4, 4)
d.add(stat("Próximo certificado", f'min({CERT_DAYS_EXPR})', "suffix: días", decimals=0, spark=False, thr=CERT_DAYS,
           desc="Días hasta la caducidad del certificado más cercano a caducar. cert-manager los renueva antes de que caduquen."), 4, 4)

d.row("Qué falla ahora")
bad_pods = table("Pods con problemas", [("A", BAD_PODS)], {"namespace": "Namespace", "pod": "Pod", "reason": "Motivo"},
                 "Pod", ["namespace", "pod", "reason"], {"Motivo": [{"id": "custom.cellOptions", "value": {"type": "color-text"}},
                                                                     {"id": "color", "value": fixed(SERIOUS)}]})
bad_pods["fieldConfig"]["defaults"]["noValue"] = "Ninguno"
d.add(bad_pods, 12, 5)
bad_wl = table("Workloads incompletos", [("A", f'max by (namespace, workload) (({DEPLOY_BAD}) or ({STS_BAD}) or ({DS_BAD}))')],
               {"namespace": "Namespace", "workload": "Workload", "Value #A": "Réplicas sin disponibilidad"},
               "Réplicas sin disponibilidad", ["namespace", "workload"],
               {"Réplicas sin disponibilidad": status_text_cell("short", thresholds(PROBLEM_THR), 0)})
bad_wl["fieldConfig"]["defaults"]["noValue"] = "Ninguno"
d.add(bad_wl, 12, 5)

d.row("Nodos y certificados")
d.add(table("Estado de los nodos", [
    ("A", 'max by (node) (kube_node_status_condition{condition="Ready",status="true"})'),
    ("B", 'max by (node) (kube_node_status_condition{condition="MemoryPressure",status="true"})'),
    ("C", 'max by (node) (kube_node_status_condition{condition="DiskPressure",status="true"})'),
    ("D", 'max by (node) (kube_node_status_condition{condition="PIDPressure",status="true"})'),
], {"node": "Nodo", "Value #A": "Listo", "Value #B": "Sin memoria", "Value #C": "Sin disco", "Value #D": "Sin procesos"},
    "Nodo", ["node"], {
        "Nodo": entity_cell(NODE_COLORS, 120),
        "Listo": [{"id": "mappings", "value": READY_MAP}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}, {"id": "custom.width", "value": 105}],
        "Sin memoria": [{"id": "mappings", "value": YESNO_OK}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}, {"id": "custom.width", "value": 105}],
        "Sin disco": [{"id": "mappings", "value": YESNO_OK}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}, {"id": "custom.width", "value": 105}],
        "Sin procesos": [{"id": "mappings", "value": YESNO_OK}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}],
    }, desc="Condiciones que Kubernetes marca cuando un nodo se queda sin memoria, disco o procesos (presión)."), 11, 10)
d.panels[-1]["options"]["sortBy"] = [{"displayName": "Nodo", "desc": False}]
d.add(table("Certificados", [
    ("A", CERT_DAYS_EXPR),
    ("B", 'max by (namespace, name) (certmanager_certificate_ready_status{condition="True"})'),
], {"namespace": "Namespace", "name": "Certificado", "Value #A": "Caduca en", "Value #B": "Válido"},
    "Caduca en", ["namespace", "name"], {
        "Caduca en": status_text_cell("suffix: días", thresholds(CERT_DAYS), 0),
        "Válido": [{"id": "mappings", "value": READY_MAP}, {"id": "custom.cellOptions", "value": {"type": "color-text"}}],
    }, desc="Rojo < 7 días · naranja < 14 · ámbar < 30."), 13, 10)
d.panels[-1]["options"]["sortBy"] = [{"displayName": "Caduca en", "desc": False}]

d.row("Estabilidad")
restarts = ts("Reinicios de contenedores", [tgt('sum by (namespace) (round(increase(kube_pod_container_status_restarts_total[$__rate_interval]))) > 0', "{{namespace}}")],
              "short", minv=0, decimals=0)
restarts["fieldConfig"]["defaults"]["custom"].update({"drawStyle": "bars", "fillOpacity": 80, "lineWidth": 0})
d.add(restarts, 8, 8)
d.add(ts("API de Kubernetes: errores", [
    tgt('sum(rate(apiserver_request_total{code=~"5.."}[$__rate_interval])) or vector(0)', "5xx (errores del servidor)", "A"),
    tgt('sum(rate(apiserver_request_total{code=~"4.."}[$__rate_interval])) or vector(0)', "4xx (peticiones rechazadas)", "B"),
], "reqps", minv=0, overrides=color_overrides({"5xx (errores del servidor)": CRIT, "4xx (peticiones rechazadas)": WARN}), palette=None,
    desc="Peticiones por segundo al API server que terminan en error. Lo normal es 5xx ≈ 0; algunos 4xx son habituales."), 8, 8)
d.add(ts("DNS del clúster (CoreDNS)", [tgt('sum by (rcode) (rate(coredns_dns_responses_total[$__rate_interval]))', "{{rcode}}")],
         "reqps", minv=0, overrides=color_overrides({"NOERROR": GOOD, "NXDOMAIN": MUTED, "SERVFAIL": CRIT, "REFUSED": SERIOUS}), palette=None,
         desc="Respuestas por segundo según resultado. SERVFAIL = fallo al resolver; NXDOMAIN = el nombre no existe (normal en pequeña cantidad)."), 8, 8)

health = dashboard("homelab-health", "Salud del clúster", "¿Hay algo roto? Nodos, pods, workloads, volúmenes y certificados", [], d.panels,
                   [("Almacenamiento", "/d/homelab-storage/almacenamiento"), ("Nodos", "/d/homelab-nodes/nodos"),
                    ("Aplicaciones", "/d/homelab-apps/aplicaciones")])

os.makedirs(OUT, exist_ok=True)
for name, dash in (("nodes.json", nodes), ("apps.json", apps), ("storage.json", storage), ("health.json", health)):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(dash, f, indent=2, ensure_ascii=False)
        f.write("\n")
