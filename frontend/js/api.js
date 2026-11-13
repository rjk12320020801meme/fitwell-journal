/* api.js — 后端 API 封装
 * 与 FastAPI 契约一一对应；全部走相对路径 /api/...，fetch JSON。
 * 失败时抛出 Error（message 为人话），由界面层展示提示条。
 */
(function (global) {
  'use strict';

  /** 通用请求：自动带 JSON 头、解析响应、统一错误 */
  async function request(path, options) {
    options = options || {};
    const init = {
      headers: { 'Content-Type': 'application/json' },
      method: options.method || 'GET',
      body: options.body ? JSON.stringify(options.body) : undefined
    };
    let res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      throw new Error('网络请求失败，请确认后端已启动');
    }
    if (res.status === 204) return null; // DELETE 成功
    let data = null;
    try { data = await res.json(); } catch (e) { /* 空响应体 */ }
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || ('请求失败（HTTP ' + res.status + '）');
      throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
    return data;
  }

  /** 把对象序列化为查询串（跳过 null/undefined/空串） */
  function qs(params) {
    const parts = [];
    Object.keys(params || {}).forEach(function (k) {
      const v = params[k];
      if (v !== null && v !== undefined && v !== '') {
        parts.push(encodeURIComponent(k) + '=' + encodeURIComponent(v));
      }
    });
    return parts.length ? '?' + parts.join('&') : '';
  }

  const API = {
    // ---- 记录类（POST 均返回 201 + 创建的记录对象） ----
    createMeal: function (body) {
      return request('/api/records/meal', { method: 'POST', body: body });
    },
    createSleep: function (body) {
      return request('/api/records/sleep', { method: 'POST', body: body });
    },
    createSubjective: function (body) {
      return request('/api/records/subjective', { method: 'POST', body: body });
    },
    createBody: function (body) {
      return request('/api/records/body', { method: 'POST', body: body });
    },
    createTraining: function (body) {
      return request('/api/records/training', { method: 'POST', body: body });
    },
    createLab: function (body) {
      return request('/api/records/lab', { method: 'POST', body: body });
    },

    /** GET /api/records?from=&to= → {meals,sleep,subjective,body,training,lab} */
    listRecords: function (from, to) {
      return request('/api/records' + qs({ from: from, to: to }));
    },

    /** DELETE /api/records/{type}/{id} → 204 */
    deleteRecord: function (type, id) {
      return request('/api/records/' + type + '/' + id, { method: 'DELETE' });
    },

    // ---- 周报 ----
    /** GET /api/report/weekly?end_date= → 周报对象 */
    weeklyReport: function (endDate) {
      return request('/api/report/weekly' + qs({ end_date: endDate }));
    },

    // ---- 食谱 ----
    /** GET /api/recipes?goal=&slot=&q= → 食谱摘要数组 */
    recipes: function (params) {
      return request('/api/recipes' + qs(params || {}));
    },
    /** GET /api/recipes/{id} → 完整食谱（含 ingredients/steps） */
    recipe: function (id) {
      return request('/api/recipes/' + encodeURIComponent(id));
    },

    // ---- 健康检查 ----
    /** GET /api/health → {status:"ok", version} */
    health: function () {
      return request('/api/health');
    }
  };

  global.API = API;
})(window);
