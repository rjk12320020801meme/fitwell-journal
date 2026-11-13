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
  const TYPE_LABEL = { meal: '饮食', sleep: '睡眠', subjective: '状态', body: '身体', training: '训练', lab: '体检' };

  /* ==================== 通用小组件 ==================== */

  /** 1–5 五档评分按钮 */
  function Scale(props) {
    return html`<div class="scale">
      ${[1, 2, 3, 4, 5].map(function (v) {
        return html`<button key=${v} type="button"
          className=${props.value === v ? 'active' : ''}
          onClick=${function () { props.onChange(v); }}>${v}</button>`;
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
      <div>${props.text || '暂无数据'}</div>
    </div>`;
  }

  /* ==================== Tab 1：今日记录 ==================== */

  function TodayTab(props) {
    const notify = props.notify;
    const [records, setRecords] = useState(null); // null=加载中

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

    // ---- 今日状态（核心：精力 + 压力；其余折叠）----
    const [energy, setEnergy] = useState(3);
    const [stress, setStress] = useState(3);
    const [mood, setMood] = useState(3);
    const [hunger, setHunger] = useState(3);
    const [cravings, setCravings] = useState(3);

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

    function saveSubjective() {
      API.createSubjective({
        date: todayStr(),
        energy: energy, stress: stress, mood: mood,
        hunger: hunger, cravings: cravings
      }).then(function () {
        notify('已记录今日状态 ✓', 'success');
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
      if (!Object.keys(body).length) { notify('请至少填写一项身体数据', 'error'); return; }
      body.date = todayStr();
      API.createBody(body).then(function () {
        notify('已记录身体数据 ✓', 'success');
        refresh();
      }).catch(function (e) { notify(e.message, 'error'); });
    }

    function saveTraining() {
      if (!trainType) { notify('请填写训练类型', 'error'); return; }
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

    // 把六类记录展平为列表行
    function flatten(data) {
      const rows = [];
      (data.meals || []).forEach(function (m) {
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
          sub: '质量 ' + s.quality + '/5 · 醒来 ' + s.awakenings + ' 次 · 午睡 ' + s.nap_min + ' 分钟'
        });
      });
      (data.subjective || []).forEach(function (s) {
        rows.push({
          type: 'subjective', id: s.id, date: s.date,
          text: '精力 ' + s.energy + ' · 压力 ' + s.stress + ' · 心情 ' + s.mood,
          sub: '饥饿 ' + s.hunger + ' · 渴望 ' + s.cravings
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
      <div class="card">
        <div class="card-title">⚡ 30 秒快速记录</div>
        <p class="card-hint">只填核心三样：一餐、睡眠、今日状态。其余在下方折叠里按需补充。</p>

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
              <${Scale} value=${sleepQuality} onChange=${setSleepQuality} />
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

        <div class="field">
          <label>今日状态</label>
          <div class="field">
            <label>精力</label>
            <${Scale} value=${energy} onChange=${setEnergy} />
          </div>
          <div class="field">
            <label>压力</label>
            <${Scale} value=${stress} onChange=${setStress} />
          </div>
          <details class="fold">
            <summary>心情 / 饥饿 / 渴望（可选）</summary>
            <div class="field"><label>心情</label><${Scale} value=${mood} onChange=${setMood} /></div>
            <div class="field"><label>饥饿感</label><${Scale} value=${hunger} onChange=${setHunger} /></div>
            <div class="field"><label>对食物的渴望</label><${Scale} value=${cravings} onChange=${setCravings} /></div>
          </details>
          <button class="btn btn-primary btn-block" type="button" onClick=${saveSubjective}>记录今日状态</button>
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
        <div class="card-title">📋 今日已记录</div>
        ${rows.length === 0
          ? html`<${Empty} text="还没有记录，从上面 30 秒开始" icon="🕐" />`
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

  /** 单个分数卡：分数 + 等级徽章 + 一句话结论 + 因子明细折叠 */
  function ScoreCard(props) {
    const factors = props.factors || [];
    let worst = null;
    factors.forEach(function (f) { if (!worst || f.score < worst.score) worst = f; });
    let summary;
    if (props.score >= 80) summary = '整体规律良好，继续保持';
    else if (props.score >= 60) summary = (worst ? '建议关注' + worst.name : '总体尚可');
    else summary = (worst ? worst.name + '偏弱，建议优先改善' : '建议优先改善');
    return html`<div class="score-card">
      <div class="score-label">${props.title}</div>
      <div class="score-value">${props.score}</div>
      <span className=${'grade-badge grade-' + props.grade}>${props.grade}</span>
      <div class="score-summary">${summary}</div>
      ${factors.length ? html`<details class="fold">
        <summary>评分明细</summary>
        ${factors.map(function (f, i) {
          return html`<div class="factor-row" key=${i}>
            <div class="factor-head">
              <span>${f.name}</span>
              <span>${f.score}</span>
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
      ${!loading && !report ? html`<${Empty} text="本周还没有足够数据，先记录几天再来看趋势" icon="📭" />` : null}

      ${report ? html`<div>
        <div class="score-grid">
          <${ScoreCard} title="代谢规律分" score=${report.metabolic.score}
            grade=${report.metabolic.grade} factors=${report.metabolic.factors} />
          <${ScoreCard} title="睡眠规律分" score=${report.sleep.score}
            grade=${report.sleep.grade} factors=${report.sleep.factors} />
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
      meals: {
        api: 'createMeal',
        fields: ['date', 'time', 'meal_type', 'description', 'portion', 'notes']
      },
      sleep: {
        api: 'createSleep',
        fields: ['date', 'bed_time', 'wake_time', 'quality', 'awakenings', 'nap_min']
      },
      subjective: {
        api: 'createSubjective',
        fields: ['date', 'energy', 'stress', 'mood', 'hunger', 'cravings']
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
        notify('导入完成：成功 ' + ok + ' 条，失败 ' + fail + ' 条', fail ? 'error' : 'success');
      } catch (e) {
        notify('导入失败：文件格式不正确', 'error');
      }
    }

    return html`<div>
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
        <div class="setting-sub">FitWell Journal 健身健康日志 · v0.1.0</div>
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
})(window);
