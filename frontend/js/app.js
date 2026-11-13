/* app.js — FitWell Journal 主应用
 * React 18 UMD + htm 模板语法（无 JSX、无构建工具）。
 * 单页 + 底部 tab：今日记录 / 周报 / 食谱 / 设置。
 * 措辞红线：全部洞察文案为"趋势/建议关注"，不出现诊断性语言。
 */
(function (global) {
  'use strict';

  const { useState, useEffect, useRef } = React;
  const html = htm.bind(React.createElement);

  /* ==================== 工具函数 ==================== */

  function pad2(n) { return (n < 10 ? '0' : '') + n; }

  /** Date → YYYY-MM-DD（本地时区） */
  function fmtDate(d) {
    return d.getFullYear() + '-' + pad2(d.getMonth() + 1) + '-' + pad2(d.getDate());
  }
  function todayStr() { return fmtDate(new Date()); }
  function daysAgoStr(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return fmtDate(d);
  }
  function nowHM() {
    const d = new Date();
    return pad2(d.getHours()) + ':' + pad2(d.getMinutes());
  }
  /** 日期字符串平移 n 天 */
  function shiftDate(dateStr, n) {
    const d = new Date(dateStr + 'T00:00:00');
    d.setDate(d.getDate() + n);
    return fmtDate(d);
  }

  /** 只保留有值的字段（数字化），用于身体/体检等可选数值表单 */
  function pickFields(obj, keys) {
    const out = {};
    keys.forEach(function (k) {
      const v = obj[k];
      if (v === '' || v === null || v === undefined || (typeof v === 'number' && isNaN(v))) return;
      out[k] = v;
    });
    return out;
  }

  const MEAL_LABEL = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐' };
  const TYPE_LABEL = { meal: '饮食', sleep: '睡眠', body: '身体', training: '训练', lab: '体检' };

  /* ==================== 通用小组件 ==================== */

  /** 睡眠质量选择：数据存 1–5，界面只显示文字（不给用户"打分"压力） */
  const QUALITY_LABEL = { 1: '很差', 2: '较差', 3: '一般', 4: '不错', 5: '很好' };
  function QualityPicker(props) {
    return html`<div class="scale">
      ${[1, 2, 3, 4, 5].map(function (v) {
        return html`<button key=${v} type="button"
          className=${props.value === v ? 'active' : ''}
          onClick=${function () { props.onChange(v); }}>${QUALITY_LABEL[v]}</button>`;
      })}
    </div>`;
  }

  /** chips 单选组：options: [{value, label}]，value 为 null 表示"全部" */
  function Chips(props) {
    return html`<div class="chips">
      ${props.options.map(function (opt) {
        return html`<button key=${String(opt.value)} type="button"
          className=${props.value === opt.value ? 'chip active' : 'chip'}
          onClick=${function () { props.onChange(opt.value); }}>${opt.label}</button>`;
      })}
    </div>`;
  }

  /** 空状态 */
  function Empty(props) {
    return html`<div class="empty-state">
      <div class="big">${props.icon || '🌱'}</div>
      <div>${props.text || '这里还什么都没有'}</div>
    </div>`;
  }

  /* ==================== 今日节奏卡（温和提示，不制造焦虑） ==================== */

  /** phase → 柔和背景色（morning 淡金 / eating 淡绿 / wind_down 淡青 / pre_bed 淡紫 / sleep 深蓝夜色） */
  function RhythmCard(props) {
    const rhythm = props.rhythm; // undefined=加载中，null=不可用
    if (rhythm === undefined) {
      return html`<div class="card rhythm-card rhythm-neutral">
        <div class="rhythm-title">正在看看今天的节奏…</div>
      </div>`;
    }
    if (rhythm === null) {
      return html`<div class="card rhythm-card rhythm-neutral">
        <div class="rhythm-title">⏰ 今日节奏</div>
        <div class="rhythm-message">节奏提示暂时不可用</div>
      </div>`;
    }
    return html`<div className=${'rhythm-card rhythm-' + rhythm.phase}>
      <div class="rhythm-now">${rhythm.now}</div>
      <div class="rhythm-title">${rhythm.title}</div>
      <div class="rhythm-message">${rhythm.message}</div>
      <div class="rhythm-next">下一步：${rhythm.next_label} · ${rhythm.next_time}</div>
    </div>`;
  }

  /* ==================== Tab 1：今日记录 ==================== */

  function TodayTab(props) {
    const notify = props.notify;
    const [records, setRecords] = useState(null); // null=加载中

    // ---- 今日节奏（打开页面取一次，不做轮询）----
    const [rhythm, setRhythm] = useState(undefined); // undefined=加载中，null=不可用

    // ---- 快速记录一餐 ----
    const [mealTime, setMealTime] = useState(nowHM());
    const [mealType, setMealType] = useState(
      (function () { // 按当前时刻猜测默认餐次
        const h = new Date().getHours();
        return h < 10 ? 'breakfast' : h < 15 ? 'lunch' : h < 21 ? 'dinner' : 'snack';
      })()
    );
    const [mealDesc, setMealDesc] = useState('');

    // ---- 快速记录睡眠（默认昨晚 23:00 / 今日 07:00）----
    const [bedTime, setBedTime] = useState('23:00');
    const [wakeTime, setWakeTime] = useState('07:00');
    const [sleepQuality, setSleepQuality] = useState(3);
    const [awakenings, setAwakenings] = useState('0');
    const [napMin, setNapMin] = useState('0');

    // ---- 展开层：身体数据 ----
    const [weight, setWeight] = useState('');
    const [waist, setWaist] = useState('');
    const [bodyFat, setBodyFat] = useState('');
    const [restHr, setRestHr] = useState('');
    const [hrv, setHrv] = useState('');

    // ---- 展开层：训练 ----
    const [trainTime, setTrainTime] = useState(nowHM());
    const [trainType, setTrainType] = useState('');
    const [trainDur, setTrainDur] = useState('');
    const [trainRpe, setTrainRpe] = useState('7');

    /** 加载今日记录（含昨天，保证"昨晚的睡眠"可见） */
    function refresh() {
      API.listRecords(daysAgoStr(1), todayStr()).then(function (data) {
        setRecords(data);
      }).catch(function (e) {
        setRecords({}); // 列表加载失败不阻塞录入
        notify(e.message, 'error');
      });
    }
    useEffect(refresh, []);
    useEffect(function () {
      API.rhythmToday().then(function (data) {
        setRhythm(data);
      }).catch(function () {
        setRhythm(null); // 节奏提示不可用不阻塞录入
      });
    }, []);

    function saveMeal() {
      API.createMeal({
        date: todayStr(), time: mealTime, meal_type: mealType,
        description: mealDesc, portion: '', notes: ''
      }).then(function () {
        setMealDesc('');
        notify('已记录一餐 ✓', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function saveSleep() {
      // date 为"上床那天"：默认昨晚（昨天 23:00 上床）
      API.createSleep({
        date: daysAgoStr(1), bed_time: bedTime, wake_time: wakeTime,
        quality: sleepQuality,
        awakenings: parseInt(awakenings, 10) || 0,
        nap_min: parseInt(napMin, 10) || 0
      }).then(function () {
        notify('已记录睡眠 ✓', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function saveBody() {
      const body = pickFields({
        weight_kg: weight ? parseFloat(weight) : '',
        waist_cm: waist ? parseFloat(waist) : '',
        body_fat_pct: bodyFat ? parseFloat(bodyFat) : '',
        resting_hr: restHr ? parseFloat(restHr) : '',
        hrv_ms: hrv ? parseFloat(hrv) : ''
      }, ['weight_kg', 'waist_cm', 'body_fat_pct', 'resting_hr', 'hrv_ms']);
      if (!Object.keys(body).length) { notify('填一项身体数据就可以保存啦', 'error'); return; }
      body.date = todayStr();
      API.createBody(body).then(function () {
        notify('已记录身体数据 ✓', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function saveTraining() {
      if (!trainType) { notify('填一下训练类型就能保存啦', 'error'); return; }
      API.createTraining({
        date: todayStr(), time: trainTime, type: trainType,
        duration_min: parseInt(trainDur, 10) || 0,
        rpe: parseInt(trainRpe, 10) || 7
      }).then(function () {
        setTrainType(''); setTrainDur('');
        notify('已记录训练 ✓', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function removeRecord(type, id) {
      API.deleteRecord(type, id).then(function () {
        notify('已删除', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    // 把记录展平为列表行
    function flatten(data) {
      const rows = [];
      (data.meal || []).forEach(function (m) {
        rows.push({
          type: 'meal', id: m.id, date: m.date,
          text: m.time + ' ' + (MEAL_LABEL[m.meal_type] || m.meal_type) + (m.description ? ' · ' + m.description : ''),
          sub: [m.portion, m.notes].filter(Boolean).join(' · ')
        });
      });
      (data.sleep || []).forEach(function (s) {
        rows.push({
          type: 'sleep', id: s.id, date: s.date,
          text: '上床 ' + s.bed_time + ' → 起床 ' + s.wake_time,
          sub: '质量 ' + (QUALITY_LABEL[s.quality] || s.quality) + ' · 醒来 ' + s.awakenings + ' 次 · 午睡 ' + s.nap_min + ' 分钟'
        });
      });
      (data.body || []).forEach(function (b) {
        const parts = [];
        if (b.weight_kg != null) parts.push('体重 ' + b.weight_kg + ' kg');
        if (b.waist_cm != null) parts.push('腰围 ' + b.waist_cm + ' cm');
        if (b.body_fat_pct != null) parts.push('体脂 ' + b.body_fat_pct + '%');
        if (b.resting_hr != null) parts.push('静息心率 ' + b.resting_hr);
        if (b.hrv_ms != null) parts.push('HRV ' + b.hrv_ms + ' ms');
        rows.push({ type: 'body', id: b.id, date: b.date, text: parts.join(' · ') || '身体数据', sub: '' });
      });
      (data.training || []).forEach(function (t) {
        rows.push({
          type: 'training', id: t.id, date: t.date,
          text: t.time + ' ' + t.type + ' · ' + t.duration_min + ' 分钟',
          sub: 'RPE ' + t.rpe
        });
      });
      (data.lab || []).forEach(function (l) {
        const parts = [];
        if (l.fasting_glucose != null) parts.push('空腹血糖 ' + l.fasting_glucose);
        if (l.fasting_insulin != null) parts.push('空腹胰岛素 ' + l.fasting_insulin);
        if (l.hba1c != null) parts.push('HbA1c ' + l.hba1c);
        rows.push({ type: 'lab', id: l.id, date: l.date, text: parts.join(' · ') || '体检数据', sub: '' });
      });
      // 按日期时间倒序（简单按 date 字符串 + 时间）
      rows.sort(function (a, b) { return (b.date || '').localeCompare(a.date || ''); });
      return rows;
    }

    const rows = records ? flatten(records) : [];

    return html`<div>
      <${RhythmCard} rhythm=${rhythm} />

      <div class="card">
        <div class="card-title">⚡ 30 秒快速记录</div>
        <p class="card-hint">只填客观事实：一餐、睡眠。体重和训练在下方折叠里按需补充。</p>

        <div class="field">
          <label>记录一餐</label>
          <${Chips} value=${mealType} onChange=${setMealType}
            options=${[
              { value: 'breakfast', label: '早' },
              { value: 'lunch', label: '午' },
              { value: 'dinner', label: '晚' },
              { value: 'snack', label: '加餐' }
            ]} />
          <div class="field-row">
            <div class="field">
              <label>时间</label>
              <input type="time" value=${mealTime}
                onChange=${function (e) { setMealTime(e.target.value); }} />
            </div>
            <div class="field">
              <label>吃了什么（可留空）</label>
              <input type="text" placeholder="例如：鸡胸肉沙拉" value=${mealDesc}
                onChange=${function (e) { setMealDesc(e.target.value); }} />
            </div>
          </div>
          <button class="btn btn-primary btn-block" type="button" onClick=${saveMeal}>记录一餐</button>
        </div>

        <div class="field">
          <label>记录睡眠（昨晚）</label>
          <div class="field-row">
            <div class="field">
              <label>上床</label>
              <input type="time" value=${bedTime}
                onChange=${function (e) { setBedTime(e.target.value); }} />
            </div>
            <div class="field">
              <label>起床</label>
              <input type="time" value=${wakeTime}
                onChange=${function (e) { setWakeTime(e.target.value); }} />
            </div>
          </div>
          <div class="field-row">
            <div class="field">
              <label>睡眠质量（1-5）</label>
              <${QualityPicker} value=${sleepQuality} onChange=${setSleepQuality} />
            </div>
          </div>
          <details class="fold">
            <summary>更多睡眠细节（可选）</summary>
            <div class="field-row">
              <div class="field">
                <label>夜间醒来次数</label>
                <input type="number" min="0" value=${awakenings}
                  onChange=${function (e) { setAwakenings(e.target.value); }} />
              </div>
              <div class="field">
                <label>午睡（分钟）</label>
                <input type="number" min="0" value=${napMin}
                  onChange=${function (e) { setNapMin(e.target.value); }} />
              </div>
            </div>
          </details>
          <button class="btn btn-primary btn-block" type="button" onClick=${saveSleep}>记录睡眠</button>
        </div>
      </div>

      <details class="fold">
        <summary>体重与身体数据（可选展开）</summary>
        <div class="field-row">
          <div class="field"><label>体重 (kg)</label>
            <input type="number" step="0.1" value=${weight}
              onChange=${function (e) { setWeight(e.target.value); }} /></div>
          <div class="field"><label>腰围 (cm)</label>
            <input type="number" step="0.1" value=${waist}
              onChange=${function (e) { setWaist(e.target.value); }} /></div>
        </div>
        <div class="field-row">
          <div class="field"><label>体脂率 (%)</label>
            <input type="number" step="0.1" value=${bodyFat}
              onChange=${function (e) { setBodyFat(e.target.value); }} /></div>
          <div class="field"><label>静息心率</label>
            <input type="number" value=${restHr}
              onChange=${function (e) { setRestHr(e.target.value); }} /></div>
          <div class="field"><label>HRV (ms)</label>
            <input type="number" value=${hrv}
              onChange=${function (e) { setHrv(e.target.value); }} /></div>
        </div>
        <button class="btn btn-ghost btn-block" type="button" onClick=${saveBody}>保存身体数据</button>
      </details>

      <details class="fold">
        <summary>训练记录（可选展开）</summary>
        <div class="field-row">
          <div class="field"><label>时间</label>
            <input type="time" value=${trainTime}
              onChange=${function (e) { setTrainTime(e.target.value); }} /></div>
          <div class="field"><label>类型</label>
            <input type="text" placeholder="例如：力量 / 有氧" value=${trainType}
              onChange=${function (e) { setTrainType(e.target.value); }} /></div>
        </div>
        <div class="field-row">
          <div class="field"><label>时长（分钟）</label>
            <input type="number" min="0" value=${trainDur}
              onChange=${function (e) { setTrainDur(e.target.value); }} /></div>
          <div class="field"><label>RPE（1-10）</label>
            <input type="number" min="1" max="10" value=${trainRpe}
              onChange=${function (e) { setTrainRpe(e.target.value); }} /></div>
        </div>
        <button class="btn btn-ghost btn-block" type="button" onClick=${saveTraining}>保存训练</button>
      </details>

      <div class="card">
        <div class="card-title">📋 最近记录</div>
        ${rows.length === 0
          ? html`<${Empty} text="还没有记录，想起来时点两下就好" icon="🕐" />`
          : html`<ul class="record-list">
              ${rows.map(function (r) {
                return html`<li class="record-item" key=${r.type + '-' + r.id}>
                  <div class="record-main">
                    <div class="record-text">
                      <span class="record-badge">${TYPE_LABEL[r.type]}</span>${r.text}
                    </div>
                    <div class="record-sub">
                      ${r.date !== todayStr() ? r.date + ' · ' : ''}${r.sub}
                    </div>
                  </div>
                  <button class="record-del" type="button"
                    onClick=${function () { removeRecord(r.type, r.id); }}>删除</button>
                </li>`;
              })}
            </ul>`}
      </div>
    </div>`;
  }

  /* ==================== Tab 2：周报 ==================== */

  /** 分数 → 文字档位（弱化数字，重点看趋势） */
  function tierOf(score) {
    if (score >= 85) return '很稳';
    if (score >= 70) return '不错';
    return '可调整';
  }
  /** 因子行的档位词 */
  function factorTierOf(score) {
    if (score >= 85) return '良好';
    if (score >= 70) return '不错';
    return '可调整';
  }
  const TIER_CLASS = { '很稳': 'tier-good', '良好': 'tier-good', '不错': 'tier-ok', '可调整': 'tier-adjust' };

  /** 单个档位卡：文字档位徽章 + 一句话结论 + 因子明细折叠 */
  function ScoreCard(props) {
    const factors = props.factors || [];
    if (props.score == null) {
      return html`<div class="score-card">
        <div class="score-label">${props.title}</div>
        <div class="empty-state"><div class="big">🌱</div><div>继续记录，趋势会慢慢显现</div></div>
      </div>`;
    }
    const tier = tierOf(props.score);
    let summary;
    if (tier === '很稳') summary = '节奏很稳，继续保持';
    else if (tier === '不错') summary = '整体不错，继续保持';
    else summary = '有可以调整的地方，想起来时优化一下就好';
    return html`<div class="score-card">
      <div class="score-label">${props.title}</div>
      <div class="score-tier-row">
        <span className=${'tier-badge ' + TIER_CLASS[tier]}>${tier}</span>
        <span class="score-ref">参考分 ${props.score}</span>
      </div>
      <div class="score-summary">${summary}</div>
      ${factors.length ? html`<details class="fold">
        <summary>看看是哪些方面</summary>
        ${factors.map(function (f, i) {
          const ft = factorTierOf(f.score);
          return html`<div class="factor-row" key=${i}>
            <div class="factor-head">
              <span>${f.name}</span>
              <span className=${'factor-tier ' + TIER_CLASS[ft]}>${ft}</span>
            </div>
            <div class="factor-bar"><span style=${{ width: Math.max(0, Math.min(100, f.score)) + '%' }}></span></div>
            <div class="factor-detail">${f.detail}</div>
          </div>`;
        })}
      </details>` : null}
    </div>`;
  }

  function ReportTab(props) {
    const notify = props.notify;
    const [endDate, setEndDate] = useState(todayStr());
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(function () {
      setLoading(true);
      API.weeklyReport(endDate).then(function (data) {
        setReport(data);
        setLoading(false);
      }).catch(function (e) {
        setReport(null);
        setLoading(false);
        notify(e.message, 'error');
      });
    }, [endDate]);

    const DIRECTION_ICON = { up: '↑', down: '↓', flat: '→' };

    return html`<div>
      <div class="week-nav">
        <button class="btn btn-ghost btn-sm" type="button"
          onClick=${function () { setEndDate(shiftDate(endDate, -7)); }}>‹ 上一周</button>
        <span class="range">
          ${report && report.period ? report.period.start + ' ~ ' + report.period.end : endDate + ' 结束'}
        </span>
        <span>
          <button class="btn btn-ghost btn-sm" type="button"
            onClick=${function () { setEndDate(todayStr()); }}>本周</button>
          <button class="btn btn-ghost btn-sm" type="button"
            onClick=${function () { setEndDate(shiftDate(endDate, 7)); }}>下一周 ›</button>
        </span>
      </div>

      ${loading ? html`<${Empty} text="正在生成周报…" icon="⏳" />` : null}
      ${!loading && !report ? html`<${Empty} text="继续记录，趋势会慢慢显现" icon="📭" />` : null}

      ${report ? html`<div>
        <div class="score-grid">
          <${ScoreCard} title="代谢规律" score=${report.metabolic.score}
            factors=${report.metabolic.factors} />
          <${ScoreCard} title="睡眠规律" score=${report.sleep.score}
            factors=${report.sleep.factors} />
        </div>

        <div class="chart-wrap">
          <div class="chart-legend">
            <span><span class="dot" style=${{ background: '#0F766E' }}></span>进食窗口(小时)</span>
            <span><span class="dot" style=${{ background: '#F59E0B' }}></span>睡眠时长(小时)</span>
          </div>
          ${Charts.lineChart({
            dates: report.series.dates,
            series: [
              { name: '进食窗口(小时)', color: '#0F766E', values: report.series.eating_window_h },
              { name: '睡眠时长(小时)', color: '#F59E0B', values: report.series.sleep_duration_h }
            ]
          })}
        </div>

        ${(report.cards || []).length === 0
          ? html`<${Empty} text="数据再攒几天，趋势卡片就会出现在这里" icon="📊" />`
          : html`<div>
            ${report.cards.map(function (c, i) {
              return html`<div class="feed-card" key=${i}>
                <div className=${'feed-icon ' + c.kind}>
                  ${DIRECTION_ICON[c.direction] || '→'}
                </div>
                <div class="feed-body">
                  <div class="feed-title">${c.title}</div>
                  <div class="feed-detail">${c.detail}</div>
                  <div class="feed-meta">
                    <span className="kind-tag">${c.kind === 'trend' ? '趋势' : '关联'}</span>
                    <span>基于 ${c.evidence_days} 天数据</span>
                  </div>
                </div>
              </div>`;
            })}
          </div>`}

        <div class="disclaimer">本工具输出为趋势洞察，不构成医疗诊断或医疗建议。</div>
      </div>` : null}
    </div>`;
  }

  /* ==================== Tab 3：食谱 ==================== */

  function RecipesTab(props) {
    const notify = props.notify;
    const [goal, setGoal] = useState(null);
    const [slot, setSlot] = useState(null);
    const [qInput, setQInput] = useState('');
    const [q, setQ] = useState('');
    const [list, setList] = useState(null);
    const [openId, setOpenId] = useState(null);   // 展开的食谱 id
    const [detail, setDetail] = useState(null);   // 完整食谱对象

    useEffect(function () {
      setList(null);
      API.recipes({ goal: goal || undefined, slot: slot || undefined, q: q || undefined })
        .then(function (data) { setList(data); })
        .catch(function (e) {
          setList([]);
          notify(e.message, 'error');
        });
    }, [goal, slot, q]);

    function toggleDetail(id) {
      if (openId === id) { setOpenId(null); setDetail(null); return; }
      setOpenId(id);
      setDetail(null);
      API.recipe(id).then(function (data) { setDetail(data); })
        .catch(function (e) { notify(e.message, 'error'); });
    }

    return html`<div>
      <div class="card">
        <div class="card-title">🍳 食谱推荐</div>
        <div class="field">
          <label>目标</label>
          <${Chips} value=${goal} onChange=${setGoal}
            options=${[
              { value: null, label: '全部' },
              { value: 'cut', label: '减脂' },
              { value: 'maintain', label: '维持' },
              { value: 'gain', label: '增肌' }
            ]} />
        </div>
        <div class="field">
          <label>餐次</label>
          <${Chips} value=${slot} onChange=${setSlot}
            options=${[
              { value: null, label: '全部' },
              { value: 'breakfast', label: '早餐' },
              { value: 'lunch', label: '午餐' },
              { value: 'dinner', label: '晚餐' },
              { value: 'snack', label: '加餐' }
            ]} />
        </div>
        <div class="field-row">
          <div class="field">
            <input type="search" placeholder="搜索食材或菜名，如：鸡胸肉"
              value=${qInput}
              onInput=${function (e) { setQInput(e.target.value); }}
              onKeyDown=${function (e) { if (e.key === 'Enter') setQ(qInput.trim()); }} />
          </div>
          <button class="btn btn-primary" type="button"
            onClick=${function () { setQ(qInput.trim()); }}>搜索</button>
        </div>
      </div>

      ${list === null ? html`<${Empty} text="正在加载食谱…" icon="⏳" />` : null}
      ${list !== null && list.length === 0
        ? html`<${Empty} text="没有匹配的食谱，换个关键词试试" icon="🍽" />` : null}

      ${list ? list.map(function (r) {
        return html`<div class="recipe-card" key=${r.id} onClick=${function () { toggleDetail(r.id); }}>
          <div class="recipe-name">${r.name}</div>
          <div class="recipe-macros">
            <span><b>${r.kcal}</b> kcal</span>
            <span>蛋白 <b>${r.protein_g}</b> g</span>
            <span>碳水 <b>${r.carb_g}</b> g</span>
            <span>脂肪 <b>${r.fat_g}</b> g</span>
            <span>⏱ ${r.prep_min} 分钟</span>
          </div>
          ${openId === r.id ? html`<div class="recipe-detail">
            ${detail === null
              ? html`<${Empty} text="正在加载做法…" icon="⏳" />`
              : html`<div>
                <h4>食材</h4>
                <table class="ingredient-table"><tbody>
                  ${(detail.ingredients || []).map(function (ing, i) {
                    return html`<tr key=${i}>
                      <td>${ing.item}</td><td>${ing.amount}</td>
                    </tr>`;
                  })}
                </tbody></table>
                <h4>做法</h4>
                <ol class="step-list">
                  ${(detail.steps || []).map(function (s, i) {
                    return html`<li key=${i}>${s}</li>`;
                  })}
                </ol>
                ${detail.timing_tip ? html`<div class="timing-tip">💡 ${detail.timing_tip}</div>` : null}
              </div>`}
          </div>` : null}
        </div>`;
      }) : null}
    </div>`;
  }

  /* ==================== Tab 4：设置 ==================== */

  function SettingsTab(props) {
    const notify = props.notify;
    const [health, setHealth] = useState({ status: 'unknown', version: '' });
    const fileRef = useRef(null);

    // ---- 节奏目标（小闹钟的提醒时刻）----
    const [rhythmCfg, setRhythmCfg] = useState({
      window_start: '10:00', window_end: '19:00',
      bed_target: '23:00', wake_target: '07:00'
    });

    function setCfg(key, val) {
      const next = {};
      Object.keys(rhythmCfg).forEach(function (k) { next[k] = rhythmCfg[k]; });
      next[key] = val;
      setRhythmCfg(next);
    }

    useEffect(function () {
      API.settings().then(function (data) {
        setRhythmCfg({
          window_start: data.window_start || '10:00',
          window_end: data.window_end || '19:00',
          bed_target: data.bed_target || '23:00',
          wake_target: data.wake_target || '07:00'
        });
      }).catch(function () { /* 回填不打扰，保留默认值 */ });
    }, []);

    function saveRhythm() {
      API.saveSettings(rhythmCfg).then(function () {
        notify('节奏目标已保存 ✓', 'success');
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function checkHealth() {
      setHealth({ status: 'unknown', version: health.version });
      API.health().then(function (data) {
        setHealth({ status: 'ok', version: data.version || '' });
      }).catch(function () {
        setHealth({ status: 'fail', version: '' });
      });
    }
    useEffect(checkHealth, []);

    /** 数据导出：全量记录下载为 JSON 文件 */
    function exportData() {
      API.listRecords('1970-01-01', '2099-12-31').then(function (data) {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'fitwell-records-' + todayStr() + '.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        notify('已导出全部记录', 'success');
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    /** 数据导入：按类型逐条 POST */
    const IMPORT_MAP = {
      meal: {
        api: 'createMeal',
        fields: ['date', 'time', 'meal_type', 'description', 'portion', 'notes']
      },
      sleep: {
        api: 'createSleep',
        fields: ['date', 'bed_time', 'wake_time', 'quality', 'awakenings', 'nap_min']
      },
      body: {
        api: 'createBody',
        fields: ['date', 'weight_kg', 'waist_cm', 'body_fat_pct', 'resting_hr', 'hrv_ms']
      },
      training: {
        api: 'createTraining',
        fields: ['date', 'time', 'type', 'duration_min', 'rpe']
      },
      lab: {
        api: 'createLab',
        fields: ['date', 'fasting_glucose', 'fasting_insulin', 'hba1c', 'total_chol', 'ldl', 'hdl', 'triglycerides']
      }
    };

    async function importData(file) {
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        let ok = 0, fail = 0;
        for (const key of Object.keys(IMPORT_MAP)) {
          const records = data[key] || [];
          const conf = IMPORT_MAP[key];
          for (const rec of records) {
            const body = pickFields(rec, conf.fields);
            if (!body.date) { fail++; continue; }
            try {
              await API[conf.api](body);
              ok++;
            } catch (e) { fail++; }
          }
        }
        notify(fail
          ? '导入完成：成功 ' + ok + ' 条，' + fail + ' 条没能导入，可以稍后再试'
          : '导入完成：成功 ' + ok + ' 条', fail ? 'error' : 'success');
      } catch (e) {
        notify('导入没能完成：文件格式不正确', 'error');
      }
    }

    return html`<div>
      <div class="card">
        <div class="card-title">⏰ 节奏目标</div>
        <p class="card-hint">设定你的节奏，小闹钟就按这个提醒你</p>
        <div class="field-row">
          <div class="field">
            <label>进食窗口开启</label>
            <input type="time" value=${rhythmCfg.window_start}
              onChange=${function (e) { setCfg('window_start', e.target.value); }} />
          </div>
          <div class="field">
            <label>进食窗口收尾</label>
            <input type="time" value=${rhythmCfg.window_end}
              onChange=${function (e) { setCfg('window_end', e.target.value); }} />
          </div>
        </div>
        <div class="field-row">
          <div class="field">
            <label>目标就寝</label>
            <input type="time" value=${rhythmCfg.bed_target}
              onChange=${function (e) { setCfg('bed_target', e.target.value); }} />
          </div>
          <div class="field">
            <label>目标起床</label>
            <input type="time" value=${rhythmCfg.wake_target}
              onChange=${function (e) { setCfg('wake_target', e.target.value); }} />
          </div>
        </div>
        <button class="btn btn-primary btn-block" type="button" onClick=${saveRhythm}>保存节奏目标</button>
      </div>

      <div class="card">
        <div class="card-title">⚙️ 设置</div>

        <div class="setting-row">
          <div>
            <div class="setting-label">后端连通状态</div>
            <div class="setting-sub">
              <span className=${'status-dot ' + health.status}></span>
              ${health.status === 'ok' ? '已连接' : health.status === 'fail' ? '未连接' : '检查中…'}
              ${health.version ? ' · v' + health.version : ''}
            </div>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" onClick=${checkHealth}>重新检查</button>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-label">数据导出</div>
            <div class="setting-sub">把全部记录下载为 JSON 文件（备份/迁移）</div>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" onClick=${exportData}>导出 JSON</button>
        </div>

        <div class="setting-row">
          <div>
            <div class="setting-label">数据导入</div>
            <div class="setting-sub">选择之前导出的 JSON 文件，按条恢复记录</div>
          </div>
          <button class="btn btn-ghost btn-sm" type="button"
            onClick=${function () { fileRef.current && fileRef.current.click(); }}>选择文件</button>
          <input type="file" accept="application/json" style=${{ display: 'none' }}
            ref=${fileRef}
            onChange=${function (e) {
              const f = e.target.files && e.target.files[0];
              if (f) importData(f);
              e.target.value = '';
            }} />
        </div>
      </div>

      <div class="card">
        <div class="card-title">ℹ️ 关于</div>
        <div class="setting-sub">FitWell Journal 健身健康日志 · v0.1.1</div>
        <div class="disclaimer">
          本工具输出为趋势洞察，不构成医疗诊断或医疗建议。
          如有健康问题请及时就医，任何数据解读都不能替代专业医疗意见。
        </div>
      </div>
    </div>`;
  }

  /* ==================== 应用根组件 ==================== */

  const TABS = [
    { key: 'today', label: '今日', icon: '📝', comp: TodayTab },
    { key: 'report', label: '周报', icon: '📊', comp: ReportTab },
    { key: 'recipes', label: '食谱', icon: '🍳', comp: RecipesTab },
    { key: 'settings', label: '设置', icon: '⚙️', comp: SettingsTab }
  ];

  function App() {
    const [tab, setTab] = useState('today');
    const [toast, setToast] = useState(null);
    const toastTimer = useRef(null);

    /** 轻量提示条（success / error） */
    function notify(msg, kind) {
      setToast({ msg: msg, kind: kind || 'success' });
      if (toastTimer.current) clearTimeout(toastTimer.current);
      toastTimer.current = setTimeout(function () { setToast(null); }, 2600);
    }

    const active = TABS.find(function (t) { return t.key === tab; }) || TABS[0];
    const ActiveComp = active.comp;

    return html`<div class="app">
      ${toast ? html`<div className=${'toast ' + toast.kind}>${toast.msg}</div>` : null}

      <header class="app-header">
        <h1 class="app-title">FitWell Journal</h1>
        <span class="app-date">${todayStr()}</span>
      </header>

      <${ActiveComp} notify=${notify} />

      <nav class="tabbar">
        ${TABS.map(function (t) {
          return html`<button key=${t.key} type="button"
            className=${t.key === tab ? 'active' : ''}
            onClick=${function () { setTab(t.key); }}>
            <span class="tab-icon">${t.icon}</span>
            <span>${t.label}</span>
          </button>`;
        })}
      </nav>
    </div>`;
  }

  // 挂载
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(html`<${App} />`);

  // 暴露组件供冒烟/渲染测试使用（不影响业务逻辑）
  global.FitWell = {
    App: App, TodayTab: TodayTab, ReportTab: ReportTab,
    RecipesTab: RecipesTab, SettingsTab: SettingsTab,
    ScoreCard: ScoreCard, RhythmCard: RhythmCard, QualityPicker: QualityPicker,
    tierOf: tierOf, factorTierOf: factorTierOf
  };
})(window);
