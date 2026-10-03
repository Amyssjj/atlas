// Journey playback: on tours that draw their path, each new leg is traced from the last stop to the next while the
// camera flies, with a marker travelling along it. An example of an atlas plugin (docs/plugins.md).

const DURATION = 2600; // the tour's own camera flight

export default function setup(atlas) {
  const empty = { type: "FeatureCollection", features: [] };
  const leg = atlas.addLayer({ id: "journey-leg", chip: false, data: empty, type: "line", color: "#e0a526", width: 5 });
  const head = atlas.addLayer({ id: "journey-head", chip: false, data: empty, type: "circle", color: "#e0a526", radius: 8 });
  let frame = 0, enabled = true;

  const clear = () => { cancelAnimationFrame(frame); leg.setData(empty); head.setData(empty); };
  atlas.addToggle({ id: "journey", name: "Journey playback", name_zh: "行程回放" }, (on) => { enabled = on; if (!on) clear(); });

  atlas.on("tour-step", ({ index, steps, path }) => {
    clear();
    if (!enabled || !path || index === 0) return;
    const a = steps[index - 1].at, b = steps[index].at, t0 = performance.now();
    const tick = (now) => {
      const k = Math.min(1, (now - t0) / DURATION), e = k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
      const p = [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e];
      leg.setData({ type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: [a, p] } }] });
      head.setData({ type: "FeatureCollection", features: k < 1 ? [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: p } }] : [] });
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
  });
  atlas.on("tour-end", clear);
}
