/* charts.js — 轻量 SVG 折线图（手写，无第三方图表库）
 * Charts.lineChart({ dates, series, height }) 返回 React 元素。
 * series: [{ name, color, values: [num|null] }]，null 值跳过并在该处断线。
 */
(function (global) {
  'use strict';

  const html = htm.bind(React.createElement);

  /**
   * 折线图。
   * @param {Object} props
   * @param {string[]} props.dates       x 轴日期标签
   * @param {Array}    props.series      [{name, color, values}]
   * @param {number}  [props.height]     绘图区高度（默认 180）
   */
  function lineChart(props) {
    const dates = props.dates || [];
    const series = props.series || [];
    const H = props.height || 180;

    // 画布尺寸（viewBox 坐标系，随容器缩放）
    const W = 600;
    const padL = 36, padR = 12, padT = 14, padB = 28;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    // 收集全部有效值，计算 y 轴范围（留 10% 上下边距）
    let min = Infinity, max = -Infinity;
    series.forEach(function (s) {
      (s.values || []).forEach(function (v) {
        if (v === null || v === undefined || isNaN(v)) return;
        if (v < min) min = v;
        if (v > max) max = v;
      });
    });
    if (min === Infinity) { min = 0; max = 1; }
    if (min === max) { min -= 1; max += 1; }
    const span = max - min;
    min -= span * 0.1;
    max += span * 0.1;

    const n = dates.length;
    const xAt = function (i) {
      return n <= 1 ? padL + plotW / 2 : padL + (plotW * i) / (n - 1);
    };
    const yAt = function (v) {
      return padT + plotH - ((v - min) / (max - min)) * plotH;
    };

    // y 轴刻度（4 档）
    const ticks = [];
    for (let t = 0; t <= 3; t++) {
      ticks.push(min + ((max - min) * t) / 3);
    }

    // 将一条 series 的点按 null 拆成连续段
    function segments(values) {
      const segs = [];
      let cur = [];
      (values || []).forEach(function (v, i) {
        if (v === null || v === undefined || isNaN(v)) {
          if (cur.length) segs.push(cur);
          cur = [];
        } else {
          cur.push({ x: xAt(i), y: yAt(v) });
        }
      });
      if (cur.length) segs.push(cur);
      return segs;
    }

    return html`
      <svg class="chart-svg" viewBox=${'0 0 ' + W + ' ' + H}
           preserveAspectRatio="xMidYMid meet" role="img" aria-label="趋势折线图">
        ${/* y 轴刻度线与标签 */ null}
        ${ticks.map(function (t, i) {
          const y = yAt(t);
          return html`<g key=${'tick' + i}>
            <line x1=${padL} y1=${y} x2=${W - padR} y2=${y}
                  stroke="#E5E7EB" strokeWidth="1" />
            <text x=${padL - 6} y=${y + 4} textAnchor="end"
                  fontSize="10" fill="#9CA3AF">${t.toFixed(1)}</text>
          </g>`;
        })}
        ${/* x 轴日期标签（全部显示，字号小） */ null}
        ${dates.map(function (d, i) {
          return html`<text key=${'x' + i} x=${xAt(i)} y=${H - 8}
                            textAnchor="middle" fontSize="10" fill="#9CA3AF">${d}</text>`;
        })}
        ${/* 折线与数据点 */ null}
        ${series.map(function (s, si) {
          return html`<g key=${'s' + si}>
            ${segments(s.values).map(function (seg, gi) {
              if (seg.length === 1) {
                // 单点没有线段，只画圆点
                return html`<circle key=${'p' + gi} cx=${seg[0].x} cy=${seg[0].y}
                                    r="3.5" fill=${s.color} />`;
              }
              const d = seg.map(function (p, pi) {
                return (pi === 0 ? 'M' : 'L') + p.x.toFixed(1) + ' ' + p.y.toFixed(1);
              }).join(' ');
              return html`<path key=${'seg' + gi} d=${d} fill="none"
                                stroke=${s.color} strokeWidth="2.5"
                                strokeLinecap="round" strokeLinejoin="round" />`;
            })}
            ${s.values.map(function (v, i) {
              if (v === null || v === undefined || isNaN(v)) return null;
              return html`<circle key=${'pt' + i} cx=${xAt(i)} cy=${yAt(v)}
                                  r="3.5" fill="#fff" stroke=${s.color} strokeWidth="2" />`;
            })}
          </g>`;
        })}
      </svg>
    `;
  }

  global.Charts = { lineChart: lineChart };
})(window);
