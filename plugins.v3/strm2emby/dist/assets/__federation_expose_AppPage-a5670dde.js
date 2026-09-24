import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const DirectorySync_vue_vue_type_style_index_0_scoped_fb205e6d_lang = '';

const {resolveComponent:_resolveComponent$3,createVNode:_createVNode$3,createTextVNode:_createTextVNode$3,createElementVNode:_createElementVNode$3,toDisplayString:_toDisplayString$3,withCtx:_withCtx$3,openBlock:_openBlock$3,createElementBlock:_createElementBlock$3,createCommentVNode:_createCommentVNode$3,createBlock:_createBlock$3} = await importShared('vue');


const _hoisted_1$3 = { class: "ds-card" };
const _hoisted_2$3 = { class: "ds-card__header" };
const _hoisted_3$3 = { class: "ds-card__title" };
const _hoisted_4$3 = { class: "ds-grid" };
const _hoisted_5$3 = { class: "ds-item" };
const _hoisted_6$3 = { class: "ds-item" };
const _hoisted_7$2 = { class: "ds-item" };
const _hoisted_8$2 = { class: "ds-item" };
const _hoisted_9$2 = { class: "ds-item" };
const _hoisted_10$2 = { class: "ds-item" };
const _hoisted_11$2 = { class: "ds-item" };
const _hoisted_12$2 = { class: "ds-item" };
const _hoisted_13$2 = { class: "ds-item" };
const _hoisted_14$2 = { class: "ds-item" };
const _hoisted_15$2 = { class: "ds-actions" };
const _hoisted_16$2 = {
  key: 0,
  class: "ds-hint"
};

const {reactive: reactive$1,ref: ref$3,watch: watch$1} = await importShared('vue');



const _sfc_main$3 = {
  __name: 'DirectorySync',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  loggedIn: { type: Boolean, default: false },
  // 父组件传入的完整插件配置（含 sync_* 字段）
  config: { type: Object, default: () => ({}) },
},
  emits: ['update'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const conflictOptions = [
  { title: '跳过（保留云端）', value: 'skip' },
  { title: '覆盖（删除云端后上传）', value: 'overwrite' },
  { title: '保留两者（自动重命名）', value: 'rename' },
];

const form = reactive$1({
  sync_enabled: false,
  sync_watch: false,
  sync_watch_polling: false,
  sync_poll_interval: 2,
  sync_source_dir: '',
  sync_remote_dir: '/',
  sync_cron: '',
  sync_conflict: 'skip',
  sync_delete_source: false,
  sync_extensions: '',
});
const saving = ref$3(false);
const syncing = ref$3(false);
const feedback = ref$3({ type: '', text: '' });

function currentPluginId() {
  return props.pluginId || props.sourcePluginId || 'Strm2Emby'
}

async function request(path, options = {}) {
  const apiPath = `plugin/${currentPluginId()}${path}`;
  if (options.method === 'POST' && props.api?.post) {
    return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  if (options.method !== 'POST' && props.api?.get) {
    return props.api.get(apiPath, { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(`/api/v1/${apiPath}`, { headers, ...options });
  return response.json()
}

function applyConfig(config = {}) {
  form.sync_enabled = Boolean(config.sync_enabled);
  form.sync_watch = Boolean(config.sync_watch);
  form.sync_watch_polling = Boolean(config.sync_watch_polling);
  form.sync_poll_interval = Number(config.sync_poll_interval || 2);
  form.sync_source_dir = config.sync_source_dir || '';
  form.sync_remote_dir = config.sync_remote_dir || '/';
  form.sync_cron = config.sync_cron || '';
  form.sync_conflict = config.sync_conflict || (config.sync_overwrite ? 'overwrite' : 'skip');
  form.sync_delete_source = Boolean(config.sync_delete_source);
  form.sync_extensions = config.sync_extensions || '';
}

watch$1(() => props.config, (value) => applyConfig(value), { immediate: true, deep: true });

async function save() {
  saving.value = true;
  feedback.value = { type: '', text: '' };
  try {
    const result = await request('/config', {
      method: 'POST',
      body: JSON.stringify({
        sync_enabled: form.sync_enabled,
        sync_watch: form.sync_watch,
        sync_watch_polling: form.sync_watch_polling,
        sync_poll_interval: Number(form.sync_poll_interval || 2),
        sync_source_dir: form.sync_source_dir,
        sync_remote_dir: form.sync_remote_dir,
        sync_cron: form.sync_cron,
        sync_conflict: form.sync_conflict,
        sync_delete_source: form.sync_delete_source,
        sync_extensions: form.sync_extensions,
      }),
    });
    if (!result.success) {
      feedback.value = { type: 'error', text: result.message || '保存失败' };
      return
    }
    if (result.data) {
      applyConfig(result.data);
      emit('update', result.data);
    }
    feedback.value = { type: 'success', text: result.message || '同步设置已保存' };
  } catch (error) {
    feedback.value = { type: 'error', text: `保存失败：${error.message || error}` };
  } finally {
    saving.value = false;
  }
}

async function runNow() {
  syncing.value = true;
  feedback.value = { type: 'info', text: '正在同步，请稍候...' };
  try {
    const result = await request('/sync');
    if (!result.success) {
      feedback.value = { type: 'error', text: result.message || '同步失败' };
    } else {
      feedback.value = { type: 'success', text: result.message || '同步任务已执行，请查看插件日志' };
    }
  } catch (error) {
    feedback.value = { type: 'error', text: `同步失败：${error.message || error}` };
  } finally {
    syncing.value = false;
  }
}

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$3("v-icon");
  const _component_v_chip = _resolveComponent$3("v-chip");
  const _component_v_switch = _resolveComponent$3("v-switch");
  const _component_v_text_field = _resolveComponent$3("v-text-field");
  const _component_v_select = _resolveComponent$3("v-select");
  const _component_v_btn = _resolveComponent$3("v-btn");
  const _component_v_alert = _resolveComponent$3("v-alert");

  return (_openBlock$3(), _createElementBlock$3("div", _hoisted_1$3, [
    _createElementVNode$3("div", _hoisted_2$3, [
      _createElementVNode$3("span", _hoisted_3$3, [
        _createVNode$3(_component_v_icon, {
          icon: "mdi-folder-sync-outline",
          size: "18",
          color: "#10b981",
          class: "mr-1"
        }),
        _cache[10] || (_cache[10] = _createTextVNode$3(" 目录同步 ", -1))
      ]),
      _createVNode$3(_component_v_chip, {
        color: form.sync_enabled ? 'success' : 'grey',
        size: "x-small",
        variant: "tonal"
      }, {
        default: _withCtx$3(() => [
          _createTextVNode$3(_toDisplayString$3(form.sync_enabled ? '已启用' : '未启用'), 1)
        ]),
        _: 1
      }, 8, ["color"])
    ]),
    _createElementVNode$3("div", _hoisted_4$3, [
      _createElementVNode$3("div", _hoisted_5$3, [
        _createVNode$3(_component_v_switch, {
          modelValue: form.sync_enabled,
          "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form.sync_enabled) = $event)),
          label: "启用目录同步",
          density: "compact",
          "hide-details": "",
          color: "primary"
        }, null, 8, ["modelValue"]),
        _cache[11] || (_cache[11] = _createElementVNode$3("div", { class: "ds-hint" }, "把本地目录上传到光鸭云盘（独立于整理链）", -1))
      ]),
      _createElementVNode$3("div", _hoisted_6$3, [
        _createVNode$3(_component_v_switch, {
          modelValue: form.sync_watch,
          "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.sync_watch) = $event)),
          label: "目录监控（实时）",
          density: "compact",
          "hide-details": "",
          color: "primary"
        }, null, 8, ["modelValue"]),
        _cache[12] || (_cache[12] = _createElementVNode$3("div", { class: "ds-hint" }, "基于 watchfiles 实时上传，可不填 Cron；inotify 不可用时自动回退轮询", -1))
      ]),
      _createElementVNode$3("div", _hoisted_7$2, [
        _createVNode$3(_component_v_switch, {
          modelValue: form.sync_watch_polling,
          "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.sync_watch_polling) = $event)),
          label: "强制轮询模式",
          density: "compact",
          "hide-details": "",
          color: "primary",
          disabled: !form.sync_watch
        }, null, 8, ["modelValue", "disabled"]),
        _cache[13] || (_cache[13] = _createElementVNode$3("div", { class: "ds-hint" }, "网络盘/带高级 ACL 的目录不支持 inotify 时勾选（否则会自动回退）", -1))
      ]),
      _createElementVNode$3("div", _hoisted_8$2, [
        _createVNode$3(_component_v_text_field, {
          modelValue: form.sync_poll_interval,
          "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((form.sync_poll_interval) = $event)),
          modelModifiers: { number: true },
          label: "轮询扫描间隔（秒）",
          type: "number",
          min: "1",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input",
          disabled: !form.sync_watch
        }, null, 8, ["modelValue", "disabled"]),
        _cache[14] || (_cache[14] = _createElementVNode$3("div", { class: "ds-hint" }, "仅轮询模式下生效，默认 2 秒", -1))
      ]),
      _createElementVNode$3("div", _hoisted_9$2, [
        _createVNode$3(_component_v_text_field, {
          modelValue: form.sync_source_dir,
          "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((form.sync_source_dir) = $event)),
          label: "本地源目录",
          placeholder: "/vol2/1000/Vol2/Media",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"])
      ]),
      _createElementVNode$3("div", _hoisted_10$2, [
        _createVNode$3(_component_v_text_field, {
          modelValue: form.sync_remote_dir,
          "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((form.sync_remote_dir) = $event)),
          label: "光鸭目标目录",
          placeholder: "/Media",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"])
      ]),
      _createElementVNode$3("div", _hoisted_11$2, [
        _createVNode$3(_component_v_text_field, {
          modelValue: form.sync_cron,
          "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((form.sync_cron) = $event)),
          label: "同步周期（Cron）",
          placeholder: "0 3 * * *",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"])
      ]),
      _createElementVNode$3("div", _hoisted_12$2, [
        _createVNode$3(_component_v_select, {
          modelValue: form.sync_conflict,
          "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((form.sync_conflict) = $event)),
          items: conflictOptions,
          "item-title": "title",
          "item-value": "value",
          label: "同名文件处理",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"])
      ]),
      _createElementVNode$3("div", _hoisted_13$2, [
        _createVNode$3(_component_v_text_field, {
          modelValue: form.sync_extensions,
          "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((form.sync_extensions) = $event)),
          label: "仅同步扩展名（可选）",
          placeholder: ".mkv,.mp4,.srt",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"])
      ]),
      _createElementVNode$3("div", _hoisted_14$2, [
        _createVNode$3(_component_v_switch, {
          modelValue: form.sync_delete_source,
          "onUpdate:modelValue": _cache[9] || (_cache[9] = $event => ((form.sync_delete_source) = $event)),
          label: "上传成功后删除本地",
          density: "compact",
          "hide-details": "",
          color: "error"
        }, null, 8, ["modelValue"]),
        _cache[15] || (_cache[15] = _createElementVNode$3("div", { class: "ds-hint" }, "谨慎开启，删除不可恢复", -1))
      ])
    ]),
    _createElementVNode$3("div", _hoisted_15$2, [
      _createVNode$3(_component_v_btn, {
        color: "primary",
        loading: saving.value,
        onClick: save
      }, {
        default: _withCtx$3(() => [...(_cache[16] || (_cache[16] = [
          _createTextVNode$3("保存同步设置", -1)
        ]))]),
        _: 1
      }, 8, ["loading"]),
      _createVNode$3(_component_v_btn, {
        variant: "tonal",
        "prepend-icon": "mdi-sync",
        loading: syncing.value,
        disabled: !__props.loggedIn,
        onClick: runNow
      }, {
        default: _withCtx$3(() => [...(_cache[17] || (_cache[17] = [
          _createTextVNode$3("立即同步", -1)
        ]))]),
        _: 1
      }, 8, ["loading", "disabled"]),
      (!__props.loggedIn)
        ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_16$2, "未登录光鸭云盘，无法同步"))
        : _createCommentVNode$3("", true)
    ]),
    (feedback.value.text)
      ? (_openBlock$3(), _createBlock$3(_component_v_alert, {
          key: 0,
          type: feedback.value.type || 'info',
          variant: "tonal",
          density: "compact"
        }, {
          default: _withCtx$3(() => [
            _createTextVNode$3(_toDisplayString$3(feedback.value.text), 1)
          ]),
          _: 1
        }, 8, ["type"]))
      : _createCommentVNode$3("", true)
  ]))
}
}

};
const DirectorySync = /*#__PURE__*/_export_sfc(_sfc_main$3, [['__scopeId',"data-v-fb205e6d"]]);

const ManualUpload_vue_vue_type_style_index_0_scoped_de561c85_lang = '';

const {resolveComponent:_resolveComponent$2,createVNode:_createVNode$2,createTextVNode:_createTextVNode$2,createElementVNode:_createElementVNode$2,toDisplayString:_toDisplayString$2,withCtx:_withCtx$2,withKeys:_withKeys,openBlock:_openBlock$2,createElementBlock:_createElementBlock$2,createCommentVNode:_createCommentVNode$2,renderList:_renderList$1,Fragment:_Fragment$1,withModifiers:_withModifiers,createBlock:_createBlock$2,normalizeClass:_normalizeClass} = await importShared('vue');


const _hoisted_1$2 = { class: "mu-card" };
const _hoisted_2$2 = { class: "mu-card__header" };
const _hoisted_3$2 = { class: "mu-card__title" };
const _hoisted_4$2 = { class: "mu-grid" };
const _hoisted_5$2 = { class: "mu-browser" };
const _hoisted_6$2 = { class: "mu-toolbar" };
const _hoisted_7$1 = { class: "mu-list" };
const _hoisted_8$1 = {
  key: 0,
  class: "mu-empty"
};
const _hoisted_9$1 = {
  key: 1,
  class: "mu-empty"
};
const _hoisted_10$1 = ["onClick"];
const _hoisted_11$1 = { class: "mu-item__name" };
const _hoisted_12$1 = {
  key: 0,
  class: "mu-item__meta"
};
const _hoisted_13$1 = { class: "mu-side" };
const _hoisted_14$1 = { class: "mu-selected" };
const _hoisted_15$1 = {
  key: 0,
  class: "mu-selected__empty"
};
const _hoisted_16$1 = { class: "mu-actions" };

const {computed: computed$2,onMounted: onMounted$2,ref: ref$2,watch} = await importShared('vue');



const _sfc_main$2 = {
  __name: 'ManualUpload',
  props: {
  // 宿主注入的实例作用域 API 客户端
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  // 是否已登录光鸭云盘（由父组件传入，用于禁用上传按钮）
  loggedIn: { type: Boolean, default: false },
  // 初始浏览目录与默认目标目录（可由父组件异步传入）
  defaultSourceDir: { type: String, default: '' },
  defaultRemoteDir: { type: String, default: '/' },
},
  setup(__props) {

const props = __props;

const currentPluginId = computed$2(() => props.pluginId || props.sourcePluginId || 'Strm2Emby');
const localPath = ref$2('');
const fsItems = ref$2([]);
const fsParent = ref$2('');
const fsLoading = ref$2(false);
const selected = ref$2([]);
const uploading = ref$2(false);
const uploadRemoteDir = ref$2(props.defaultRemoteDir || '/');
const remoteDirTouched = ref$2(false);
const feedback = ref$2({ type: '', text: '' });

function pluginPath(path) {
  return `plugin/${currentPluginId.value}${path}`
}

async function request(path, options = {}) {
  if (options.method === 'POST' && props.api?.post) {
    return props.api.post(pluginPath(path), options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  if (options.method !== 'POST' && props.api?.get) {
    return props.api.get(pluginPath(path), { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(`/api/v1/${pluginPath(path)}`, { headers, ...options });
  return response.json()
}

function setFeedback(type, text) {
  feedback.value = { type, text };
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function markRemoteDirTouched() {
  remoteDirTouched.value = true;
}

async function browseLocal(path) {
  fsLoading.value = true;
  try {
    const query = path ? `?path=${encodeURIComponent(path)}` : '';
    const result = await request(`/fs/list${query}`);
    if (!result.success) {
      setFeedback('error', result.message || '打开目录失败');
      return
    }
    const data = result.data || {};
    localPath.value = data.path || path || '/';
    fsParent.value = data.parent || '';
    fsItems.value = Array.isArray(data.items) ? data.items : [];
  } catch (error) {
    setFeedback('error', `打开目录失败：${error.message || error}`);
  } finally {
    fsLoading.value = false;
  }
}

function isSelected(path) {
  return selected.value.some(item => item.path === path)
}

function addSelected(entry) {
  if (isSelected(entry.path)) {
    return
  }
  selected.value.push({ name: entry.name, path: entry.path, type: entry.type });
}

function toggleSelected(entry) {
  if (isSelected(entry.path)) {
    removeSelected(entry.path);
  } else {
    addSelected(entry);
  }
}

function onEntryClick(entry) {
  if (entry.type === 'dir') {
    browseLocal(entry.path);
  } else {
    toggleSelected(entry);
  }
}

function removeSelected(path) {
  selected.value = selected.value.filter(item => item.path !== path);
}

function clearSelected() {
  selected.value = [];
}

async function startUpload() {
  if (!selected.value.length) {
    return
  }
  uploading.value = true;
  setFeedback('info', '正在上传，请稍候...');
  try {
    const result = await request('/upload', {
      method: 'POST',
      body: JSON.stringify({
        paths: selected.value.map(item => item.path),
        remote_dir: uploadRemoteDir.value || props.defaultRemoteDir || '/',
      }),
    });
    if (!result.success) {
      setFeedback('error', result.message || '上传失败');
    } else {
      setFeedback('success', result.message || '上传完成');
      clearSelected();
    }
  } catch (error) {
    setFeedback('error', `上传失败：${error.message || error}`);
  } finally {
    uploading.value = false;
  }
}

watch(() => props.defaultRemoteDir, (value) => {
  if (!remoteDirTouched.value && value) {
    uploadRemoteDir.value = value;
  }
});

watch(() => props.defaultSourceDir, (value) => {
  if (!localPath.value && value) {
    browseLocal(value);
  }
});

onMounted$2(() => {
  browseLocal(props.defaultSourceDir || '/');
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$2("v-icon");
  const _component_v_chip = _resolveComponent$2("v-chip");
  const _component_v_text_field = _resolveComponent$2("v-text-field");
  const _component_v_btn = _resolveComponent$2("v-btn");
  const _component_v_alert = _resolveComponent$2("v-alert");

  return (_openBlock$2(), _createElementBlock$2("div", _hoisted_1$2, [
    _createElementVNode$2("div", _hoisted_2$2, [
      _createElementVNode$2("span", _hoisted_3$2, [
        _createVNode$2(_component_v_icon, {
          icon: "mdi-cloud-upload-outline",
          size: "18",
          color: "#f59e0b",
          class: "mr-1"
        }),
        _cache[5] || (_cache[5] = _createTextVNode$2(" 手动上传 ", -1))
      ]),
      _createVNode$2(_component_v_chip, {
        size: "x-small",
        variant: "tonal",
        color: "primary"
      }, {
        default: _withCtx$2(() => [
          _createTextVNode$2("已选 " + _toDisplayString$2(selected.value.length) + " 项", 1)
        ]),
        _: 1
      })
    ]),
    _createElementVNode$2("div", _hoisted_4$2, [
      _createElementVNode$2("div", _hoisted_5$2, [
        _createElementVNode$2("div", _hoisted_6$2, [
          _createVNode$2(_component_v_text_field, {
            modelValue: localPath.value,
            "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((localPath).value = $event)),
            label: "服务器目录",
            density: "compact",
            variant: "outlined",
            "hide-details": "",
            class: "mu-input",
            placeholder: "/vol2/1000/Media",
            onKeyup: _cache[1] || (_cache[1] = _withKeys($event => (browseLocal(localPath.value)), ["enter"]))
          }, null, 8, ["modelValue"]),
          _createVNode$2(_component_v_btn, {
            color: "primary",
            variant: "tonal",
            density: "comfortable",
            loading: fsLoading.value,
            icon: "mdi-folder-search-outline",
            onClick: _cache[2] || (_cache[2] = $event => (browseLocal(localPath.value)))
          }, null, 8, ["loading"]),
          _createVNode$2(_component_v_btn, {
            variant: "tonal",
            density: "comfortable",
            disabled: !fsParent.value,
            icon: "mdi-arrow-up",
            onClick: _cache[3] || (_cache[3] = $event => (browseLocal(fsParent.value)))
          }, null, 8, ["disabled"])
        ]),
        _createElementVNode$2("div", _hoisted_7$1, [
          (fsLoading.value)
            ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_8$1, "正在加载..."))
            : (!fsItems.value.length)
              ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_9$1, "该目录为空"))
              : _createCommentVNode$2("", true),
          (_openBlock$2(true), _createElementBlock$2(_Fragment$1, null, _renderList$1(fsItems.value, (entry) => {
            return (_openBlock$2(), _createElementBlock$2("div", {
              key: entry.path,
              class: _normalizeClass(["mu-item", { 'mu-item--selected': isSelected(entry.path) }])
            }, [
              _createElementVNode$2("div", {
                class: "mu-item__main",
                onClick: $event => (onEntryClick(entry))
              }, [
                _createVNode$2(_component_v_icon, {
                  icon: entry.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline',
                  size: "18",
                  color: entry.type === 'dir' ? '#f59e0b' : undefined
                }, null, 8, ["icon", "color"]),
                _createElementVNode$2("span", _hoisted_11$1, _toDisplayString$2(entry.name), 1),
                (entry.type === 'file')
                  ? (_openBlock$2(), _createElementBlock$2("span", _hoisted_12$1, _toDisplayString$2(formatSize(entry.size)), 1))
                  : _createCommentVNode$2("", true)
              ], 8, _hoisted_10$1),
              (entry.type === 'dir')
                ? (_openBlock$2(), _createBlock$2(_component_v_btn, {
                    key: 0,
                    variant: "text",
                    density: "comfortable",
                    size: "x-small",
                    icon: "mdi-plus",
                    disabled: isSelected(entry.path),
                    onClick: _withModifiers($event => (addSelected(entry)), ["stop"])
                  }, null, 8, ["disabled", "onClick"]))
                : (isSelected(entry.path))
                  ? (_openBlock$2(), _createBlock$2(_component_v_icon, {
                      key: 1,
                      icon: "mdi-check-circle",
                      size: "18",
                      color: "success",
                      class: "mr-1"
                    }))
                  : _createCommentVNode$2("", true)
            ], 2))
          }), 128))
        ])
      ]),
      _createElementVNode$2("div", _hoisted_13$1, [
        _createVNode$2(_component_v_text_field, {
          modelValue: uploadRemoteDir.value,
          "onUpdate:modelValue": [
            _cache[4] || (_cache[4] = $event => ((uploadRemoteDir).value = $event)),
            markRemoteDirTouched
          ],
          label: "光鸭目标目录",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "mu-input",
          placeholder: "/Media"
        }, null, 8, ["modelValue"]),
        _createElementVNode$2("div", _hoisted_14$1, [
          (_openBlock$2(true), _createElementBlock$2(_Fragment$1, null, _renderList$1(selected.value, (item) => {
            return (_openBlock$2(), _createBlock$2(_component_v_chip, {
              key: item.path,
              size: "small",
              variant: "tonal",
              closable: "",
              "onClick:close": $event => (removeSelected(item.path))
            }, {
              default: _withCtx$2(() => [
                _createVNode$2(_component_v_icon, {
                  icon: item.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline',
                  size: "14",
                  start: ""
                }, null, 8, ["icon"]),
                _createTextVNode$2(" " + _toDisplayString$2(item.name), 1)
              ]),
              _: 2
            }, 1032, ["onClick:close"]))
          }), 128)),
          (!selected.value.length)
            ? (_openBlock$2(), _createElementBlock$2("span", _hoisted_15$1, "尚未选择文件或文件夹"))
            : _createCommentVNode$2("", true)
        ]),
        _createElementVNode$2("div", _hoisted_16$1, [
          _createVNode$2(_component_v_btn, {
            color: "primary",
            loading: uploading.value,
            disabled: !selected.value.length || !__props.loggedIn,
            "prepend-icon": "mdi-cloud-upload-outline",
            onClick: startUpload
          }, {
            default: _withCtx$2(() => [...(_cache[6] || (_cache[6] = [
              _createTextVNode$2(" 开始上传 ", -1)
            ]))]),
            _: 1
          }, 8, ["loading", "disabled"]),
          (selected.value.length)
            ? (_openBlock$2(), _createBlock$2(_component_v_btn, {
                key: 0,
                variant: "text",
                onClick: clearSelected
              }, {
                default: _withCtx$2(() => [...(_cache[7] || (_cache[7] = [
                  _createTextVNode$2("清空", -1)
                ]))]),
                _: 1
              }))
            : _createCommentVNode$2("", true)
        ]),
        (feedback.value.text)
          ? (_openBlock$2(), _createBlock$2(_component_v_alert, {
              key: 0,
              type: feedback.value.type || 'info',
              variant: "tonal",
              density: "compact"
            }, {
              default: _withCtx$2(() => [
                _createTextVNode$2(_toDisplayString$2(feedback.value.text), 1)
              ]),
              _: 1
            }, 8, ["type"]))
          : _createCommentVNode$2("", true),
        _cache[8] || (_cache[8] = _createElementVNode$2("div", { class: "mu-hint" }, "同名文件按「目录同步」的同名策略处理；手动上传不会删除本地源文件。", -1))
      ])
    ])
  ]))
}
}

};
const ManualUpload = /*#__PURE__*/_export_sfc(_sfc_main$2, [['__scopeId',"data-v-de561c85"]]);

const UploadHistory_vue_vue_type_style_index_0_scoped_5982c7be_lang = '';

const {resolveComponent:_resolveComponent$1,createVNode:_createVNode$1,createTextVNode:_createTextVNode$1,createElementVNode:_createElementVNode$1,toDisplayString:_toDisplayString$1,withCtx:_withCtx$1,renderList:_renderList,Fragment:_Fragment,openBlock:_openBlock$1,createElementBlock:_createElementBlock$1,createCommentVNode:_createCommentVNode$1,createBlock:_createBlock$1} = await importShared('vue');


const _hoisted_1$1 = { class: "uh-card" };
const _hoisted_2$1 = { class: "uh-card__header" };
const _hoisted_3$1 = { class: "uh-card__title" };
const _hoisted_4$1 = { class: "uh-header-actions" };
const _hoisted_5$1 = {
  key: 0,
  class: "uh-progress"
};
const _hoisted_6$1 = { class: "uh-progress__top" };
const _hoisted_7 = { class: "uh-progress__current" };
const _hoisted_8 = { class: "uh-progress__percent" };
const _hoisted_9 = { class: "uh-progress__stats" };
const _hoisted_10 = {
  key: 0,
  class: "uh-progress__items"
};
const _hoisted_11 = ["title"];
const _hoisted_12 = {
  key: 0,
  class: "uh-pitem__phase"
};
const _hoisted_13 = {
  key: 1,
  class: "uh-pitem__percent"
};
const _hoisted_14 = {
  key: 0,
  class: "uh-pitem__flash"
};
const _hoisted_15 = {
  key: 1,
  class: "uh-progress__more"
};
const _hoisted_16 = { class: "uh-filters" };
const _hoisted_17 = { class: "uh-list" };
const _hoisted_18 = {
  key: 0,
  class: "uh-empty"
};
const _hoisted_19 = { class: "uh-item__body" };
const _hoisted_20 = { class: "uh-item__name" };
const _hoisted_21 = { class: "uh-item__meta" };
const _hoisted_22 = {
  key: 0,
  class: "uh-sep"
};
const _hoisted_23 = { key: 1 };
const _hoisted_24 = ["title"];
const _hoisted_25 = {
  key: 0,
  class: "uh-item__error"
};

const {computed: computed$1,onBeforeUnmount,onMounted: onMounted$1,ref: ref$1} = await importShared('vue');



const _sfc_main$1 = {
  __name: 'UploadHistory',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
},
  setup(__props) {

const props = __props;

const history = ref$1([]);
const loading = ref$1(false);
const filter = ref$1('all');
const progress = ref$1(emptyProgress());
const progressVisible = ref$1(false);
let pollTimer = null;
let hideTimer = null;
let wasActive = false;

const filterOptions = [
  { title: '全部', value: 'all' },
  { title: '手动上传', value: 'manual' },
  { title: '目录同步', value: 'sync' },
  { title: '目录监控', value: 'watch' },
];

const filtered = computed$1(() => {
  if (filter.value === 'all') {
    return history.value
  }
  return history.value.filter(item => item.trigger === filter.value)
});

// 最新的文件排在最上面
const progressItems = computed$1(() => [...(progress.value.items || [])].reverse());

function itemStatusLabel(status) {
  return { running: '进行中', uploaded: '成功', skipped: '跳过', failed: '失败' }[status] || status
}

// 后端为每个进度行新增 phase 字段：hashing / uploading / confirming
function itemPhaseLabel(phase) {
  return { hashing: '计算哈希中…', uploading: '传输中…', confirming: '确认中…' }[phase] || ''
}

function itemColor(status) {
  return { running: 'info', uploaded: 'success', skipped: 'warning', failed: 'error' }[status] || 'default'
}

function itemIcon(status) {
  return {
    running: 'mdi-progress-upload',
    uploaded: 'mdi-check-circle-outline',
    skipped: 'mdi-debug-step-over',
    failed: 'mdi-alert-circle-outline',
  }[status] || 'mdi-file-outline'
}

const showProgress = computed$1(() => progressVisible.value);

function emptyProgress() {
  return {
    active: false,
    trigger: '',
    total: 0,
    done: 0,
    uploaded: 0,
    skipped: 0,
    failed: 0,
    current: '',
    percent: 0,
    message: '',
    items: [],
  }
}

function currentPluginId() {
  return props.pluginId || props.sourcePluginId || 'Strm2Emby'
}

async function request(path, options = {}) {
  const apiPath = `plugin/${currentPluginId()}${path}`;
  if (options.method === 'POST' && props.api?.post) {
    return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  if (options.method !== 'POST' && props.api?.get) {
    return props.api.get(apiPath, { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(`/api/v1/${apiPath}`, { headers, ...options });
  return response.json()
}

function triggerLabel(trigger) {
  return { manual: '手动上传', sync: '目录同步', watch: '目录监控' }[trigger] || '上传'
}

function actionLabel(action) {
  return { uploaded: '成功', skipped: '跳过', failed: '失败' }[action] || action
}

function actionColor(action) {
  return { uploaded: 'success', skipped: 'warning', failed: 'error' }[action] || 'default'
}

function actionIcon(action) {
  return {
    uploaded: 'mdi-check-circle-outline',
    skipped: 'mdi-debug-step-over',
    failed: 'mdi-alert-circle-outline',
  }[action] || 'mdi-information-outline'
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatTime(timestamp) {
  const value = Number(timestamp || 0);
  if (!value) return '-'
  const date = new Date(value * 1000);
  const pad = num => String(num).padStart(2, '0');
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

async function loadHistory() {
  loading.value = true;
  try {
    const result = await request('/history?limit=200');
    const data = result.data || {};
    history.value = Array.isArray(data.items) ? data.items : [];
  } catch (error) {
    console.error('获取上传记录失败', error);
  } finally {
    loading.value = false;
  }
}

function scheduleHideProgress(delay = 6000) {
  if (hideTimer) {
    clearTimeout(hideTimer);
  }
  hideTimer = setTimeout(() => {
    progressVisible.value = false;
    hideTimer = null;
  }, delay);
}

async function loadProgress() {
  try {
    const result = await request('/progress');
    const data = result.data || {};
    progress.value = { ...emptyProgress(), ...data };
    if (progress.value.active) {
      // 运行中：持续显示
      if (hideTimer) {
        clearTimeout(hideTimer);
        hideTimer = null;
      }
      progressVisible.value = true;
    } else if (wasActive) {
      // 刚从运行转为完成：保留最终结果几秒后自动隐藏
      progressVisible.value = true;
      scheduleHideProgress(6000);
      loadHistory();
    }
    wasActive = progress.value.active;
  } catch (error) {
    progress.value = emptyProgress();
  }
}

function scheduleNext() {
  pollTimer = setTimeout(async () => {
    await loadProgress();
    scheduleNext();
  }, progress.value.active ? 1500 : 5000);
}

async function clearHistory() {
  try {
    const result = await request('/history/clear', { method: 'POST' });
    if (result.success) {
      history.value = [];
    }
  } catch (error) {
    console.error('清空上传记录失败', error);
  }
}

onMounted$1(async () => {
  await Promise.all([loadHistory(), loadProgress()]);
  scheduleNext();
});

onBeforeUnmount(() => {
  if (pollTimer) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  if (hideTimer) {
    clearTimeout(hideTimer);
    hideTimer = null;
  }
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$1("v-icon");
  const _component_v_chip = _resolveComponent$1("v-chip");
  const _component_v_btn = _resolveComponent$1("v-btn");
  const _component_v_progress_linear = _resolveComponent$1("v-progress-linear");

  return (_openBlock$1(), _createElementBlock$1("div", _hoisted_1$1, [
    _createElementVNode$1("div", _hoisted_2$1, [
      _createElementVNode$1("span", _hoisted_3$1, [
        _createVNode$1(_component_v_icon, {
          icon: "mdi-history",
          size: "18",
          color: "#6366f1",
          class: "mr-1"
        }),
        _cache[0] || (_cache[0] = _createTextVNode$1(" 上传记录 ", -1))
      ]),
      _createElementVNode$1("div", _hoisted_4$1, [
        _createVNode$1(_component_v_chip, {
          size: "x-small",
          variant: "tonal",
          color: "primary"
        }, {
          default: _withCtx$1(() => [
            _createTextVNode$1("共 " + _toDisplayString$1(history.value.length) + " 条", 1)
          ]),
          _: 1
        }),
        _createVNode$1(_component_v_btn, {
          size: "x-small",
          variant: "text",
          icon: "mdi-refresh",
          loading: loading.value,
          onClick: loadHistory
        }, null, 8, ["loading"]),
        _createVNode$1(_component_v_btn, {
          size: "x-small",
          variant: "text",
          color: "error",
          icon: "mdi-delete-outline",
          disabled: !history.value.length,
          onClick: clearHistory
        }, null, 8, ["disabled"])
      ])
    ]),
    (showProgress.value)
      ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_5$1, [
          _createElementVNode$1("div", _hoisted_6$1, [
            _createVNode$1(_component_v_chip, {
              size: "x-small",
              variant: "tonal",
              color: progress.value.active ? 'info' : 'success'
            }, {
              default: _withCtx$1(() => [
                _createTextVNode$1(_toDisplayString$1(triggerLabel(progress.value.trigger)), 1)
              ]),
              _: 1
            }, 8, ["color"]),
            _createElementVNode$1("span", _hoisted_7, _toDisplayString$1(progress.value.current || progress.value.message || '-'), 1),
            _createElementVNode$1("span", _hoisted_8, _toDisplayString$1(progress.value.percent) + "%", 1)
          ]),
          _createVNode$1(_component_v_progress_linear, {
            "model-value": progress.value.percent,
            color: progress.value.active ? 'primary' : 'success',
            height: "8",
            rounded: ""
          }, null, 8, ["model-value", "color"]),
          _createElementVNode$1("div", _hoisted_9, " 成功 " + _toDisplayString$1(progress.value.uploaded) + " · 跳过 " + _toDisplayString$1(progress.value.skipped) + " · 失败 " + _toDisplayString$1(progress.value.failed) + " · 共 " + _toDisplayString$1(progress.value.total), 1),
          (progressItems.value.length)
            ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_10, [
                (_openBlock$1(true), _createElementBlock$1(_Fragment, null, _renderList(progressItems.value, (it, idx) => {
                  return (_openBlock$1(), _createElementBlock$1("div", {
                    key: `${it.name}-${idx}`,
                    class: "uh-pitem"
                  }, [
                    _createVNode$1(_component_v_icon, {
                      icon: itemIcon(it.status),
                      color: itemColor(it.status),
                      size: "15"
                    }, null, 8, ["icon", "color"]),
                    _createElementVNode$1("span", {
                      class: "uh-pitem__name",
                      title: it.remote || it.local
                    }, _toDisplayString$1(it.name), 9, _hoisted_11),
                    (it.status === 'running')
                      ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_12, _toDisplayString$1(itemPhaseLabel(it.phase)), 1))
                      : _createCommentVNode$1("", true),
                    (it.status === 'running')
                      ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_13, _toDisplayString$1(it.percent) + "%", 1))
                      : (_openBlock$1(), _createElementBlock$1(_Fragment, { key: 2 }, [
                          (it.flash)
                            ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_14, "秒传"))
                            : _createCommentVNode$1("", true),
                          _createVNode$1(_component_v_chip, {
                            size: "x-small",
                            variant: "tonal",
                            color: itemColor(it.status)
                          }, {
                            default: _withCtx$1(() => [
                              _createTextVNode$1(_toDisplayString$1(itemStatusLabel(it.status)), 1)
                            ]),
                            _: 2
                          }, 1032, ["color"])
                        ], 64))
                  ]))
                }), 128))
              ]))
            : _createCommentVNode$1("", true),
          (progress.value.total > progressItems.value.length)
            ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_15, " 仅显示最近 " + _toDisplayString$1(progressItems.value.length) + " / 共 " + _toDisplayString$1(progress.value.total) + " 个文件，完整结果见下方记录 ", 1))
            : _createCommentVNode$1("", true)
        ]))
      : _createCommentVNode$1("", true),
    _cache[3] || (_cache[3] = _createElementVNode$1("div", { class: "uh-legend" }, " 「秒传」表示云端已存在相同内容（按文件 MD5 命中），实际上传字节为 0，仅新增云端文件引用。 ", -1)),
    _createElementVNode$1("div", _hoisted_16, [
      (_openBlock$1(), _createElementBlock$1(_Fragment, null, _renderList(filterOptions, (opt) => {
        return _createVNode$1(_component_v_chip, {
          key: opt.value,
          size: "x-small",
          variant: "tonal",
          color: filter.value === opt.value ? 'primary' : 'default',
          onClick: $event => (filter.value = opt.value)
        }, {
          default: _withCtx$1(() => [
            _createTextVNode$1(_toDisplayString$1(opt.title), 1)
          ]),
          _: 2
        }, 1032, ["color", "onClick"])
      }), 64))
    ]),
    _createElementVNode$1("div", _hoisted_17, [
      (!filtered.value.length)
        ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_18, "暂无上传记录"))
        : _createCommentVNode$1("", true),
      (_openBlock$1(true), _createElementBlock$1(_Fragment, null, _renderList(filtered.value, (item, idx) => {
        return (_openBlock$1(), _createElementBlock$1("div", {
          key: `${item.time}-${idx}`,
          class: "uh-item"
        }, [
          _createVNode$1(_component_v_icon, {
            icon: actionIcon(item.action),
            color: actionColor(item.action),
            size: "16"
          }, null, 8, ["icon", "color"]),
          _createElementVNode$1("div", _hoisted_19, [
            _createElementVNode$1("div", _hoisted_20, _toDisplayString$1(item.name), 1),
            _createElementVNode$1("div", _hoisted_21, [
              _createElementVNode$1("span", null, _toDisplayString$1(formatTime(item.time)), 1),
              _cache[1] || (_cache[1] = _createElementVNode$1("span", { class: "uh-sep" }, "·", -1)),
              _createElementVNode$1("span", null, _toDisplayString$1(triggerLabel(item.trigger)), 1),
              (item.size)
                ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_22, "·"))
                : _createCommentVNode$1("", true),
              (item.size)
                ? (_openBlock$1(), _createElementBlock$1("span", _hoisted_23, _toDisplayString$1(formatSize(item.size)), 1))
                : _createCommentVNode$1("", true),
              _createElementVNode$1("span", {
                class: "uh-item__remote",
                title: item.remote || item.local
              }, _toDisplayString$1(item.remote || item.local), 9, _hoisted_24)
            ]),
            (item.error)
              ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_25, _toDisplayString$1(item.error), 1))
              : _createCommentVNode$1("", true)
          ]),
          (item.flash && item.action === 'uploaded')
            ? (_openBlock$1(), _createBlock$1(_component_v_chip, {
                key: 0,
                size: "x-small",
                variant: "tonal",
                color: "info",
                class: "uh-item__flash"
              }, {
                default: _withCtx$1(() => [...(_cache[2] || (_cache[2] = [
                  _createTextVNode$1(" 秒传 ", -1)
                ]))]),
                _: 1
              }))
            : _createCommentVNode$1("", true),
          _createVNode$1(_component_v_chip, {
            size: "x-small",
            variant: "tonal",
            color: actionColor(item.action)
          }, {
            default: _withCtx$1(() => [
              _createTextVNode$1(_toDisplayString$1(actionLabel(item.action)), 1)
            ]),
            _: 2
          }, 1032, ["color"])
        ]))
      }), 128))
    ])
  ]))
}
}

};
const UploadHistory = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-5982c7be"]]);

const AppPage_vue_vue_type_style_index_0_scoped_505e18e1_lang = '';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,withCtx:_withCtx,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "ap-page" };
const _hoisted_2 = { class: "ap-header" };
const _hoisted_3 = { class: "ap-header__left" };
const _hoisted_4 = { class: "ap-header__icon" };
const _hoisted_5 = { class: "ap-header__right" };
const _hoisted_6 = {
  key: 2,
  class: "ap-empty"
};

const {computed,onMounted,reactive,ref} = await importShared('vue');


const _sfc_main = {
  __name: 'AppPage',
  props: {
  // 宿主注入的实例作用域 API 客户端
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
  // 侧栏全页宿主会注入，保留以免未声明属性告警
  nativeSubscribe: { type: Function, default: null },
},
  setup(__props) {

const props = __props;

const loading = ref(false);
const fullConfig = ref({});
const status = reactive({
  logged_in: false,
  total_space: 0,
  used_space: 0,
  sync_source_dir: '',
  sync_remote_dir: '/',
});

const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'Strm2Emby');

async function loadStatus() {
  loading.value = true;
  try {
    let data;
    if (props.api?.get) {
      data = await props.api.get(`plugin/${currentPluginId.value}/config`, { feedback: 'silent' });
    } else {
      const response = await fetch(`/api/v1/plugin/${currentPluginId.value}/config`);
      data = await response.json();
    }
    fullConfig.value = data?.data || {};
    status.logged_in = Boolean(data?.data?.logged_in);
    status.total_space = Number(data?.data?.total_space || 0);
    status.used_space = Number(data?.data?.used_space || 0);
    status.sync_source_dir = data?.data?.sync_source_dir || '';
    status.sync_remote_dir = data?.data?.sync_remote_dir || '/';
  } catch (error) {
    console.error('获取光鸭云盘状态失败', error);
  } finally {
    loading.value = false;
  }
}

function onConfigUpdate(data) {
  if (!data) {
    return
  }
  fullConfig.value = data;
  status.sync_source_dir = data.sync_source_dir || '';
  status.sync_remote_dir = data.sync_remote_dir || '/';
}

function openPluginPage() {
  window.location.hash = '#/plugins';
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(loadStatus);

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent("v-icon");
  const _component_v_chip = _resolveComponent("v-chip");
  const _component_v_btn = _resolveComponent("v-btn");
  const _component_v_alert = _resolveComponent("v-alert");

  return (_openBlock(), _createElementBlock("div", _hoisted_1, [
    _createElementVNode("div", _hoisted_2, [
      _createElementVNode("div", _hoisted_3, [
        _createElementVNode("div", _hoisted_4, [
          _createVNode(_component_v_icon, {
            icon: "mdi-duck",
            size: "26"
          })
        ]),
        _cache[0] || (_cache[0] = _createElementVNode("div", { class: "ap-header__meta" }, [
          _createElementVNode("div", { class: "ap-header__title" }, "Strm2Emby"),
          _createElementVNode("div", { class: "ap-header__sub" }, "浏览 MoviePilot 主机文件并上传到光鸭云盘")
        ], -1))
      ]),
      _createElementVNode("div", _hoisted_5, [
        _createVNode(_component_v_chip, {
          color: status.logged_in ? 'success' : 'warning',
          variant: "tonal",
          size: "small"
        }, {
          default: _withCtx(() => [
            _createTextVNode(_toDisplayString(status.logged_in ? '已登录' : '未登录'), 1)
          ]),
          _: 1
        }, 8, ["color"]),
        (status.logged_in && status.total_space)
          ? (_openBlock(), _createBlock(_component_v_chip, {
              key: 0,
              variant: "tonal",
              size: "small",
              color: "primary"
            }, {
              default: _withCtx(() => [
                _createTextVNode(" 已用 " + _toDisplayString(formatSize(status.used_space)) + " / " + _toDisplayString(formatSize(status.total_space)), 1)
              ]),
              _: 1
            }))
          : _createCommentVNode("", true),
        _createVNode(_component_v_btn, {
          color: "primary",
          variant: "tonal",
          size: "small",
          "prepend-icon": "mdi-refresh",
          loading: loading.value,
          onClick: loadStatus
        }, {
          default: _withCtx(() => [...(_cache[1] || (_cache[1] = [
            _createTextVNode("刷新", -1)
          ]))]),
          _: 1
        }, 8, ["loading"]),
        _createVNode(_component_v_btn, {
          variant: "tonal",
          size: "small",
          "prepend-icon": "mdi-cog",
          onClick: openPluginPage
        }, {
          default: _withCtx(() => [...(_cache[2] || (_cache[2] = [
            _createTextVNode("插件页", -1)
          ]))]),
          _: 1
        })
      ])
    ]),
    (!status.logged_in)
      ? (_openBlock(), _createBlock(_component_v_alert, {
          key: 0,
          type: "warning",
          variant: "tonal",
          class: "ap-alert"
        }, {
          default: _withCtx(() => [...(_cache[3] || (_cache[3] = [
            _createTextVNode(" 未登录光鸭云盘。请先点击右上角「插件页」扫码登录，登录后即可在此上传与同步。 ", -1)
          ]))]),
          _: 1
        }))
      : _createCommentVNode("", true),
    _createVNode(DirectorySync, {
      api: __props.api,
      "plugin-id": __props.pluginId,
      "source-plugin-id": __props.sourcePluginId,
      "logged-in": status.logged_in,
      config: fullConfig.value,
      onUpdate: onConfigUpdate
    }, null, 8, ["api", "plugin-id", "source-plugin-id", "logged-in", "config"]),
    (status.logged_in)
      ? (_openBlock(), _createBlock(ManualUpload, {
          key: 1,
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId,
          "logged-in": status.logged_in,
          "default-source-dir": status.sync_source_dir,
          "default-remote-dir": status.sync_remote_dir
        }, null, 8, ["api", "plugin-id", "source-plugin-id", "logged-in", "default-source-dir", "default-remote-dir"]))
      : (_openBlock(), _createElementBlock("div", _hoisted_6, [
          _createVNode(_component_v_icon, {
            icon: "mdi-cloud-off-outline",
            size: "48",
            color: "grey"
          }),
          _cache[4] || (_cache[4] = _createElementVNode("div", { class: "ap-empty__text" }, "登录后即可在「整理」菜单里直接把服务器文件上传到光鸭云盘。", -1))
        ])),
    _createVNode(UploadHistory, {
      api: __props.api,
      "plugin-id": __props.pluginId,
      "source-plugin-id": __props.sourcePluginId
    }, null, 8, ["api", "plugin-id", "source-plugin-id"])
  ]))
}
}

};
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-505e18e1"]]);

export { AppPage as default };
