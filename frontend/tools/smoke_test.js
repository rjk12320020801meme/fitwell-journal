// 冒烟测试：在 Node 环境验证 htm 模板、charts、api、app 的模块级加载。
// 运行：bundled node frontend/tools/smoke_test.js
'use strict';
const path = require('path');

// 提供浏览器全局的最小桩
global.window = global;
global.React = require(path.join(__dirname, '..', 'vendor', 'react.production.min.js'));
global.htm = require(path.join(__dirname, '..', 'vendor', 'htm.umd.js'));
global.document = { getElementById: function () { return {}; } };
global.ReactDOM = { createRoot: function () { return { render: function () {} }; } };

// 加载应用模块
require(path.join(__dirname, '..', 'js', 'api.js'));
require(path.join(__dirname, '..', 'js', 'charts.js'));

// 1) API 封装导出完整
const apiFns = ['createMeal', 'createSleep', 'createBody',
  'createTraining', 'createLab', 'listRecords', 'deleteRecord',
  'weeklyReport', 'settings', 'saveSettings', 'rhythmToday',
  'recipes', 'recipe', 'health'];
apiFns.forEach(function (f) {
  if (typeof global.API[f] !== 'function') throw new Error('API 缺少 ' + f);
});

// 2) 折线图产出 svg React 元素，且 null 值不断裂报错
const el = global.Charts.lineChart({
  dates: ['11-08', '11-09', '11-10', '11-11'],
  series: [
    { name: '进食窗口', color: '#0F766E', values: [9.5, null, 8.2, 10] },
    { name: '睡眠时长', color: '#F59E0B', values: [7.1, 6.4, null, 7.8] }
  ]
});
if (!el || el.type !== 'svg') throw new Error('lineChart 未返回 svg 元素');
if (!Array.isArray(el.props.children)) throw new Error('svg 子节点异常');

// 3) app.js 模块级加载（挂载被桩拦截，App 不真正渲染）
require(path.join(__dirname, '..', 'js', 'app.js'));

console.log('smoke ok: api', apiFns.length, 'fns; chart svg children', el.props.children.length);
