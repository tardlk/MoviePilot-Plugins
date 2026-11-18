import { importShared } from './__federation_fn_import-054b33c3.js';
import { _ as _export_sfc } from './_plugin-vue_export-helper-c4c0bc37.js';

const RemoteDirPicker_vue_vue_type_style_index_0_scoped_5699b5f8_lang = '';

const {resolveComponent:_resolveComponent$6,createVNode:_createVNode$6,withCtx:_withCtx$6,createElementVNode:_createElementVNode$6,withKeys:_withKeys$1,openBlock:_openBlock$6,createElementBlock:_createElementBlock$6,createCommentVNode:_createCommentVNode$6,toDisplayString:_toDisplayString$6,renderList:_renderList$4,Fragment:_Fragment$4,createTextVNode:_createTextVNode$6} = await importShared('vue');


const _hoisted_1$6 = { class: "rdp-field" };
const _hoisted_2$6 = { class: "rdp-card" };
const _hoisted_3$6 = { class: "rdp-head" };
const _hoisted_4$6 = { class: "rdp-toolbar" };
const _hoisted_5$6 = { class: "rdp-list" };
const _hoisted_6$6 = {
  key: 0,
  class: "rdp-empty"
};
const _hoisted_7$5 = {
  key: 1,
  class: "rdp-error"
};
const _hoisted_8$5 = {
  key: 2,
  class: "rdp-empty"
};
const _hoisted_9$3 = ["onClick"];
const _hoisted_10$3 = { class: "rdp-item__name" };
const _hoisted_11$2 = { class: "rdp-current" };
const _hoisted_12$2 = { class: "rdp-hint" };
const _hoisted_13$2 = { class: "rdp-actions" };

const {computed: computed$5,ref: ref$6} = await importShared('vue');



const _sfc_main$6 = {
  __name: 'RemoteDirPicker',
  props: {
  modelValue: { type: String, default: '/' },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  label: { type: String, default: '光鸭目标目录' },
  placeholder: { type: String, default: '/Media' },
  disabled: { type: Boolean, default: false },
  hint: { type: String, default: '也可以直接在输入框里手填新目录，上传时会自动创建。' },
},
  emits: ['update:modelValue'],
  setup(__props, { emit: __emit }) {

const props = __props;

const emit = __emit;

const value = computed$5({
  get: () => props.modelValue || '/',
  set: (next) => emit('update:modelValue', next),
});

const dialog = ref$6(false);
const currentPath = ref$6('/');
const parentPath = ref$6('');
const pathInput = ref$6('/');
const items = ref$6([]);
const loading = ref$6(false);
const error = ref$6('');

const currentPluginId = computed$5(() => props.pluginId || props.sourcePluginId || 'guangyasync');

async function request(path) {
  const apiPath = `plugin/${currentPluginId.value}${path}`;
  if (props.api?.get) {
    return props.api.get(apiPath, { feedback: 'silent' })
  }
  const response = await fetch(`/api/v1/${apiPath}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  return response.json()
}

function parentOf(path) {
  if (!path || path === '/') return ''
  const parts = path.split('/').filter(Boolean);
  parts.pop();
  return parts.length ? `/${parts.join('/')}` : '/'
}

async function browse(path) {
  const target = (path || '/').trim() || '/';
  loading.value = true;
  error.value = '';
  try {
    const result = await request(`/remote/list?path=${encodeURIComponent(target)}`);
    if (!result.success) {
      // 目标目录可能还不存在（用户打算新建）：自动回退到最近的已存在父目录
      const fallback = parentOf(target);
      if (fallback && fallback !== target) {
        loading.value = false;
        return browse(fallback)
      }
      error.value = result.message || '打开目录失败';
      return
    }
    const data = result.data || {};
    currentPath.value = data.path || target;
    parentPath.value = data.parent || '';
    pathInput.value = currentPath.value;
    items.value = Array.isArray(data.items) ? data.items : [];
  } catch (err) {
    error.value = `打开目录失败：${err.message || err}`;
  } finally {
    loading.value = false;
  }
}

function openPicker() {
  currentPath.value = props.modelValue || '/';
  pathInput.value = currentPath.value;
  items.value = [];
  error.value = '';
  dialog.value = true;
  browse(currentPath.value);
}

function goUp() {
  if (parentPath.value) {
    browse(parentPath.value);
  }
}

function choose() {
  emit('update:modelValue', currentPath.value || '/');
  dialog.value = false;
}

return (_ctx, _cache) => {
  const _component_v_btn = _resolveComponent$6("v-btn");
  const _component_v_text_field = _resolveComponent$6("v-text-field");
  const _component_v_icon = _resolveComponent$6("v-icon");
  const _component_v_dialog = _resolveComponent$6("v-dialog");

  return (_openBlock$6(), _createElementBlock$6("div", _hoisted_1$6, [
    _createVNode$6(_component_v_text_field, {
      modelValue: value.value,
      "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((value).value = $event)),
      label: __props.label,
      placeholder: __props.placeholder,
      disabled: __props.disabled,
      density: "compact",
      variant: "outlined",
      "hide-details": "",
      class: "rdp-input"
    }, {
      "append-inner": _withCtx$6(() => [
        _createVNode$6(_component_v_btn, {
          variant: "text",
          density: "comfortable",
          size: "small",
          disabled: __props.disabled,
          icon: "mdi-folder-search-outline",
          title: '浏览云盘目录',
          onClick: openPicker
        }, null, 8, ["disabled"])
      ]),
      _: 1
    }, 8, ["modelValue", "label", "placeholder", "disabled"]),
    _createVNode$6(_component_v_dialog, {
      modelValue: dialog.value,
      "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((dialog).value = $event)),
      "max-width": "520",
      scrollable: ""
    }, {
      default: _withCtx$6(() => [
        _createElementVNode$6("div", _hoisted_2$6, [
          _createElementVNode$6("div", _hoisted_3$6, [
            _cache[7] || (_cache[7] = _createElementVNode$6("span", { class: "rdp-title" }, "选择光鸭云盘目录", -1)),
            _createVNode$6(_component_v_btn, {
              variant: "text",
              density: "comfortable",
              size: "small",
              icon: "mdi-close",
              onClick: _cache[1] || (_cache[1] = $event => (dialog.value = false))
            })
          ]),
          _createElementVNode$6("div", _hoisted_4$6, [
            _createVNode$6(_component_v_btn, {
              variant: "tonal",
              density: "comfortable",
              size: "small",
              icon: "mdi-arrow-up",
              disabled: !parentPath.value || loading.value,
              title: "上一级",
              onClick: goUp
            }, null, 8, ["disabled"]),
            _createVNode$6(_component_v_text_field, {
              modelValue: pathInput.value,
              "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((pathInput).value = $event)),
              label: "当前路径",
              density: "compact",
              variant: "outlined",
              "hide-details": "",
              class: "rdp-input",
              onKeyup: _cache[3] || (_cache[3] = _withKeys$1($event => (browse(pathInput.value)), ["enter"]))
            }, null, 8, ["modelValue"]),
            _createVNode$6(_component_v_btn, {
              variant: "tonal",
              density: "comfortable",
              size: "small",
              icon: "mdi-refresh",
              loading: loading.value,
              title: "刷新",
              onClick: _cache[4] || (_cache[4] = $event => (browse(currentPath.value)))
            }, null, 8, ["loading"])
          ]),
          _createElementVNode$6("div", _hoisted_5$6, [
            (loading.value)
              ? (_openBlock$6(), _createElementBlock$6("div", _hoisted_6$6, "正在读取云盘目录..."))
              : (error.value)
                ? (_openBlock$6(), _createElementBlock$6("div", _hoisted_7$5, _toDisplayString$6(error.value), 1))
                : (!items.value.length)
                  ? (_openBlock$6(), _createElementBlock$6("div", _hoisted_8$5, "此目录下没有子文件夹"))
                  : (_openBlock$6(true), _createElementBlock$6(_Fragment$4, { key: 3 }, _renderList$4(items.value, (entry) => {
                      return (_openBlock$6(), _createElementBlock$6("div", {
                        key: entry.path,
                        class: "rdp-item",
                        onClick: $event => (browse(entry.path))
                      }, [
                        _createVNode$6(_component_v_icon, {
                          icon: "mdi-folder",
                          size: "18",
                          color: "#f59e0b"
                        }),
                        _createElementVNode$6("span", _hoisted_10$3, _toDisplayString$6(entry.name), 1),
                        _createVNode$6(_component_v_icon, {
                          icon: "mdi-chevron-right",
                          size: "16",
                          class: "rdp-item__arrow"
                        })
                      ], 8, _hoisted_9$3))
                    }), 128))
          ]),
          _createElementVNode$6("div", _hoisted_11$2, [
            _cache[8] || (_cache[8] = _createTextVNode$6(" 将选择：", -1)),
            _createElementVNode$6("strong", null, _toDisplayString$6(currentPath.value || '/'), 1)
          ]),
          _createElementVNode$6("div", _hoisted_12$2, _toDisplayString$6(__props.hint), 1),
          _createElementVNode$6("div", _hoisted_13$2, [
            _createVNode$6(_component_v_btn, {
              variant: "text",
              onClick: _cache[5] || (_cache[5] = $event => (dialog.value = false))
            }, {
              default: _withCtx$6(() => [...(_cache[9] || (_cache[9] = [
                _createTextVNode$6("取消", -1)
              ]))]),
              _: 1
            }),
            _createVNode$6(_component_v_btn, {
              color: "primary",
              disabled: loading.value || Boolean(error.value),
              onClick: choose
            }, {
              default: _withCtx$6(() => [...(_cache[10] || (_cache[10] = [
                _createTextVNode$6("选择此目录", -1)
              ]))]),
              _: 1
            }, 8, ["disabled"])
          ])
        ])
      ]),
      _: 1
    }, 8, ["modelValue"])
  ]))
}
}

};
const RemoteDirPicker = /*#__PURE__*/_export_sfc(_sfc_main$6, [['__scopeId',"data-v-5699b5f8"]]);

const DirectorySync_vue_vue_type_style_index_0_scoped_4c2d62b2_lang = '';

const {resolveComponent:_resolveComponent$5,createVNode:_createVNode$5,createTextVNode:_createTextVNode$5,createElementVNode:_createElementVNode$5,toDisplayString:_toDisplayString$5,withCtx:_withCtx$5,openBlock:_openBlock$5,createBlock:_createBlock$5,createCommentVNode:_createCommentVNode$5,createElementBlock:_createElementBlock$5} = await importShared('vue');


const _hoisted_1$5 = { class: "ds-card" };
const _hoisted_2$5 = { class: "ds-card__header" };
const _hoisted_3$5 = { class: "ds-card__title" };
const _hoisted_4$5 = { class: "ds-grid" };
const _hoisted_5$5 = { class: "ds-item" };
const _hoisted_6$5 = { class: "ds-item" };
const _hoisted_7$4 = { class: "ds-item" };
const _hoisted_8$4 = { class: "ds-actions" };

const {reactive: reactive$3,ref: ref$5,watch: watch$3} = await importShared('vue');


const _sfc_main$5 = {
  __name: 'DirectorySync',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  // 父组件传入的完整插件配置
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

const form = reactive$3({
  sync_on_transfer: false,
  sync_remote_dir: '/',
  sync_conflict: 'skip',
});
const saving = ref$5(false);
const feedback = ref$5({ type: '', text: '' });

function currentPluginId() {
  return props.pluginId || props.sourcePluginId || 'guangyasync'
}

async function request(path, options = {}) {
  const apiPath = `plugin/${currentPluginId()}${path}`;
  if (props.api?.post) {
    return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const response = await fetch(`/api/v1/${apiPath}`, { headers, ...options });
  return response.json()
}

function applyConfig(config = {}) {
  form.sync_on_transfer = Boolean(config.sync_on_transfer);
  form.sync_remote_dir = config.sync_remote_dir || '/';
  form.sync_conflict = config.sync_conflict || 'skip';
}

watch$3(() => props.config, (value) => applyConfig(value), { immediate: true, deep: true });

async function save() {
  saving.value = true;
  feedback.value = { type: '', text: '' };
  try {
    const result = await request('/config', {
      method: 'POST',
      body: JSON.stringify({
        sync_on_transfer: form.sync_on_transfer,
        sync_remote_dir: form.sync_remote_dir,
        sync_conflict: form.sync_conflict,
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
    feedback.value = { type: 'success', text: result.message || '设置已保存' };
  } catch (error) {
    feedback.value = { type: 'error', text: `保存失败：${error.message || error}` };
  } finally {
    saving.value = false;
  }
}

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$5("v-icon");
  const _component_v_chip = _resolveComponent$5("v-chip");
  const _component_v_switch = _resolveComponent$5("v-switch");
  const _component_v_select = _resolveComponent$5("v-select");
  const _component_v_btn = _resolveComponent$5("v-btn");
  const _component_v_alert = _resolveComponent$5("v-alert");

  return (_openBlock$5(), _createElementBlock$5("div", _hoisted_1$5, [
    _createElementVNode$5("div", _hoisted_2$5, [
      _createElementVNode$5("span", _hoisted_3$5, [
        _createVNode$5(_component_v_icon, {
          icon: "mdi-folder-move-outline",
          size: "18",
          color: "#10b981",
          class: "mr-1"
        }),
        _cache[3] || (_cache[3] = _createTextVNode$5(" 整理联动上传 ", -1))
      ]),
      _createVNode$5(_component_v_chip, {
        color: form.sync_on_transfer ? 'success' : 'grey',
        size: "x-small",
        variant: "tonal"
      }, {
        default: _withCtx$5(() => [
          _createTextVNode$5(_toDisplayString$5(form.sync_on_transfer ? '已启用' : '未启用'), 1)
        ]),
        _: 1
      }, 8, ["color"])
    ]),
    _createElementVNode$5("div", _hoisted_4$5, [
      _createElementVNode$5("div", _hoisted_5$5, [
        _createVNode$5(_component_v_switch, {
          modelValue: form.sync_on_transfer,
          "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form.sync_on_transfer) = $event)),
          label: "整理成功后自动上传",
          density: "compact",
          "hide-details": "",
          color: "primary"
        }, null, 8, ["modelValue"]),
        _cache[4] || (_cache[4] = _createElementVNode$5("div", { class: "ds-hint" }, "订阅 MoviePilot「整理完成」事件，自动读取整理后的成品文件与媒体目录并上传；无需填写本地路径，不扫描目录、不参与整理过程。", -1))
      ]),
      _createElementVNode$5("div", _hoisted_6$5, [
        _createVNode$5(RemoteDirPicker, {
          modelValue: form.sync_remote_dir,
          "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.sync_remote_dir) = $event)),
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId
        }, null, 8, ["modelValue", "api", "plugin-id", "source-plugin-id"])
      ]),
      _createElementVNode$5("div", _hoisted_7$4, [
        _createVNode$5(_component_v_select, {
          modelValue: form.sync_conflict,
          "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.sync_conflict) = $event)),
          items: conflictOptions,
          "item-title": "title",
          "item-value": "value",
          label: "同名文件处理",
          density: "compact",
          variant: "outlined",
          "hide-details": "",
          class: "ds-input"
        }, null, 8, ["modelValue"]),
        _cache[5] || (_cache[5] = _createElementVNode$5("div", { class: "ds-hint" }, "云端已有同名文件时的处理方式，默认跳过", -1))
      ])
    ]),
    _createElementVNode$5("div", _hoisted_8$4, [
      _createVNode$5(_component_v_btn, {
        color: "primary",
        loading: saving.value,
        onClick: save
      }, {
        default: _withCtx$5(() => [...(_cache[6] || (_cache[6] = [
          _createTextVNode$5("保存设置", -1)
        ]))]),
        _: 1
      }, 8, ["loading"]),
      _cache[7] || (_cache[7] = _createElementVNode$5("span", { class: "ds-hint" }, "上传记录与逐文件进度见下方「上传记录」", -1))
    ]),
    (feedback.value.text)
      ? (_openBlock$5(), _createBlock$5(_component_v_alert, {
          key: 0,
          type: feedback.value.type || 'info',
          variant: "tonal",
          density: "compact"
        }, {
          default: _withCtx$5(() => [
            _createTextVNode$5(_toDisplayString$5(feedback.value.text), 1)
          ]),
          _: 1
        }, 8, ["type"]))
      : _createCommentVNode$5("", true)
  ]))
}
}

};
const DirectorySync = /*#__PURE__*/_export_sfc(_sfc_main$5, [['__scopeId',"data-v-4c2d62b2"]]);

const ManualUpload_vue_vue_type_style_index_0_scoped_11c3a556_lang = '';

const {resolveComponent:_resolveComponent$4,createVNode:_createVNode$4,createTextVNode:_createTextVNode$4,createElementVNode:_createElementVNode$4,toDisplayString:_toDisplayString$4,withCtx:_withCtx$4,withKeys:_withKeys,openBlock:_openBlock$4,createElementBlock:_createElementBlock$4,createCommentVNode:_createCommentVNode$4,renderList:_renderList$3,Fragment:_Fragment$3,withModifiers:_withModifiers,createBlock:_createBlock$4,normalizeClass:_normalizeClass} = await importShared('vue');


const _hoisted_1$4 = { class: "mu-card" };
const _hoisted_2$4 = { class: "mu-card__header" };
const _hoisted_3$4 = { class: "mu-card__title" };
const _hoisted_4$4 = { class: "mu-grid" };
const _hoisted_5$4 = { class: "mu-browser" };
const _hoisted_6$4 = { class: "mu-toolbar" };
const _hoisted_7$3 = { class: "mu-list" };
const _hoisted_8$3 = {
  key: 0,
  class: "mu-empty"
};
const _hoisted_9$2 = {
  key: 1,
  class: "mu-empty"
};
const _hoisted_10$2 = ["onClick"];
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

const {computed: computed$4,onMounted: onMounted$3,ref: ref$4,watch: watch$2} = await importShared('vue');


const _sfc_main$4 = {
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

const currentPluginId = computed$4(() => props.pluginId || props.sourcePluginId || 'guangyasync');
const localPath = ref$4('');
const fsItems = ref$4([]);
const fsParent = ref$4('');
const fsLoading = ref$4(false);
const selected = ref$4([]);
const uploading = ref$4(false);
const uploadRemoteDir = ref$4(props.defaultRemoteDir || '/');
const remoteDirTouched = ref$4(false);
const feedback = ref$4({ type: '', text: '' });

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

function onRemoteDirChange(next) {
  uploadRemoteDir.value = next || '/';
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

watch$2(() => props.defaultRemoteDir, (value) => {
  if (!remoteDirTouched.value && value) {
    uploadRemoteDir.value = value;
  }
});

watch$2(() => props.defaultSourceDir, (value) => {
  if (!localPath.value && value) {
    browseLocal(value);
  }
});

onMounted$3(() => {
  browseLocal(props.defaultSourceDir || '/');
});

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$4("v-icon");
  const _component_v_chip = _resolveComponent$4("v-chip");
  const _component_v_text_field = _resolveComponent$4("v-text-field");
  const _component_v_btn = _resolveComponent$4("v-btn");
  const _component_v_alert = _resolveComponent$4("v-alert");

  return (_openBlock$4(), _createElementBlock$4("div", _hoisted_1$4, [
    _createElementVNode$4("div", _hoisted_2$4, [
      _createElementVNode$4("span", _hoisted_3$4, [
        _createVNode$4(_component_v_icon, {
          icon: "mdi-cloud-upload-outline",
          size: "18",
          color: "#f59e0b",
          class: "mr-1"
        }),
        _cache[4] || (_cache[4] = _createTextVNode$4(" 手动上传 ", -1))
      ]),
      _createVNode$4(_component_v_chip, {
        size: "x-small",
        variant: "tonal",
        color: "primary"
      }, {
        default: _withCtx$4(() => [
          _createTextVNode$4("已选 " + _toDisplayString$4(selected.value.length) + " 项", 1)
        ]),
        _: 1
      })
    ]),
    _createElementVNode$4("div", _hoisted_4$4, [
      _createElementVNode$4("div", _hoisted_5$4, [
        _createElementVNode$4("div", _hoisted_6$4, [
          _createVNode$4(_component_v_text_field, {
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
          _createVNode$4(_component_v_btn, {
            color: "primary",
            variant: "tonal",
            density: "comfortable",
            loading: fsLoading.value,
            icon: "mdi-folder-search-outline",
            onClick: _cache[2] || (_cache[2] = $event => (browseLocal(localPath.value)))
          }, null, 8, ["loading"]),
          _createVNode$4(_component_v_btn, {
            variant: "tonal",
            density: "comfortable",
            disabled: !fsParent.value,
            icon: "mdi-arrow-up",
            onClick: _cache[3] || (_cache[3] = $event => (browseLocal(fsParent.value)))
          }, null, 8, ["disabled"])
        ]),
        _createElementVNode$4("div", _hoisted_7$3, [
          (fsLoading.value)
            ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_8$3, "正在加载..."))
            : (!fsItems.value.length)
              ? (_openBlock$4(), _createElementBlock$4("div", _hoisted_9$2, "该目录为空"))
              : _createCommentVNode$4("", true),
          (_openBlock$4(true), _createElementBlock$4(_Fragment$3, null, _renderList$3(fsItems.value, (entry) => {
            return (_openBlock$4(), _createElementBlock$4("div", {
              key: entry.path,
              class: _normalizeClass(["mu-item", { 'mu-item--selected': isSelected(entry.path) }])
            }, [
              _createElementVNode$4("div", {
                class: "mu-item__main",
                onClick: $event => (onEntryClick(entry))
              }, [
                _createVNode$4(_component_v_icon, {
                  icon: entry.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline',
                  size: "18",
                  color: entry.type === 'dir' ? '#f59e0b' : undefined
                }, null, 8, ["icon", "color"]),
                _createElementVNode$4("span", _hoisted_11$1, _toDisplayString$4(entry.name), 1),
                (entry.type === 'file')
                  ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_12$1, _toDisplayString$4(formatSize(entry.size)), 1))
                  : _createCommentVNode$4("", true)
              ], 8, _hoisted_10$2),
              (entry.type === 'dir')
                ? (_openBlock$4(), _createBlock$4(_component_v_btn, {
                    key: 0,
                    variant: "text",
                    density: "comfortable",
                    size: "x-small",
                    icon: "mdi-plus",
                    disabled: isSelected(entry.path),
                    onClick: _withModifiers($event => (addSelected(entry)), ["stop"])
                  }, null, 8, ["disabled", "onClick"]))
                : (isSelected(entry.path))
                  ? (_openBlock$4(), _createBlock$4(_component_v_icon, {
                      key: 1,
                      icon: "mdi-check-circle",
                      size: "18",
                      color: "success",
                      class: "mr-1"
                    }))
                  : _createCommentVNode$4("", true)
            ], 2))
          }), 128))
        ])
      ]),
      _createElementVNode$4("div", _hoisted_13$1, [
        _createVNode$4(RemoteDirPicker, {
          "model-value": uploadRemoteDir.value,
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId,
          "onUpdate:modelValue": onRemoteDirChange
        }, null, 8, ["model-value", "api", "plugin-id", "source-plugin-id"]),
        _createElementVNode$4("div", _hoisted_14$1, [
          (_openBlock$4(true), _createElementBlock$4(_Fragment$3, null, _renderList$3(selected.value, (item) => {
            return (_openBlock$4(), _createBlock$4(_component_v_chip, {
              key: item.path,
              size: "small",
              variant: "tonal",
              closable: "",
              "onClick:close": $event => (removeSelected(item.path))
            }, {
              default: _withCtx$4(() => [
                _createVNode$4(_component_v_icon, {
                  icon: item.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline',
                  size: "14",
                  start: ""
                }, null, 8, ["icon"]),
                _createTextVNode$4(" " + _toDisplayString$4(item.name), 1)
              ]),
              _: 2
            }, 1032, ["onClick:close"]))
          }), 128)),
          (!selected.value.length)
            ? (_openBlock$4(), _createElementBlock$4("span", _hoisted_15$1, "尚未选择文件或文件夹"))
            : _createCommentVNode$4("", true)
        ]),
        _createElementVNode$4("div", _hoisted_16$1, [
          _createVNode$4(_component_v_btn, {
            color: "primary",
            loading: uploading.value,
            disabled: !selected.value.length || !__props.loggedIn,
            "prepend-icon": "mdi-cloud-upload-outline",
            onClick: startUpload
          }, {
            default: _withCtx$4(() => [...(_cache[5] || (_cache[5] = [
              _createTextVNode$4(" 开始上传 ", -1)
            ]))]),
            _: 1
          }, 8, ["loading", "disabled"]),
          (selected.value.length)
            ? (_openBlock$4(), _createBlock$4(_component_v_btn, {
                key: 0,
                variant: "text",
                onClick: clearSelected
              }, {
                default: _withCtx$4(() => [...(_cache[6] || (_cache[6] = [
                  _createTextVNode$4("清空", -1)
                ]))]),
                _: 1
              }))
            : _createCommentVNode$4("", true)
        ]),
        (feedback.value.text)
          ? (_openBlock$4(), _createBlock$4(_component_v_alert, {
              key: 0,
              type: feedback.value.type || 'info',
              variant: "tonal",
              density: "compact"
            }, {
              default: _withCtx$4(() => [
                _createTextVNode$4(_toDisplayString$4(feedback.value.text), 1)
              ]),
              _: 1
            }, 8, ["type"]))
          : _createCommentVNode$4("", true),
        _cache[7] || (_cache[7] = _createElementVNode$4("div", { class: "mu-hint" }, "同名文件按上方设置的同名策略处理；手动上传不会删除本地源文件。", -1))
      ])
    ])
  ]))
}
}

};
const ManualUpload = /*#__PURE__*/_export_sfc(_sfc_main$4, [['__scopeId',"data-v-11c3a556"]]);

const UploadHistory_vue_vue_type_style_index_0_scoped_4ceb7da0_lang = '';

const {resolveComponent:_resolveComponent$3,createVNode:_createVNode$3,createTextVNode:_createTextVNode$3,createElementVNode:_createElementVNode$3,toDisplayString:_toDisplayString$3,withCtx:_withCtx$3,renderList:_renderList$2,Fragment:_Fragment$2,openBlock:_openBlock$3,createElementBlock:_createElementBlock$3,createCommentVNode:_createCommentVNode$3,createBlock:_createBlock$3} = await importShared('vue');


const _hoisted_1$3 = { class: "uh-card" };
const _hoisted_2$3 = { class: "uh-card__header" };
const _hoisted_3$3 = { class: "uh-card__title" };
const _hoisted_4$3 = { class: "uh-header-actions" };
const _hoisted_5$3 = {
  key: 0,
  class: "uh-progress"
};
const _hoisted_6$3 = { class: "uh-progress__top" };
const _hoisted_7$2 = { class: "uh-progress__current" };
const _hoisted_8$2 = { class: "uh-progress__percent" };
const _hoisted_9$1 = { class: "uh-progress__stats" };
const _hoisted_10$1 = {
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

const {computed: computed$3,onBeforeUnmount,onMounted: onMounted$2,ref: ref$3} = await importShared('vue');



const _sfc_main$3 = {
  __name: 'UploadHistory',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
},
  setup(__props) {

const props = __props;

const history = ref$3([]);
const loading = ref$3(false);
const filter = ref$3('all');
const progress = ref$3(emptyProgress());
const progressVisible = ref$3(false);
let pollTimer = null;
let hideTimer = null;
let wasActive = false;

const filterOptions = [
  { title: '全部', value: 'all' },
  { title: '手动上传', value: 'manual' },
  { title: '整理联动', value: 'transfer' },
];

const filtered = computed$3(() => {
  if (filter.value === 'all') {
    return history.value
  }
  return history.value.filter(item => item.trigger === filter.value)
});

// 最新的文件排在最上面
const progressItems = computed$3(() => [...(progress.value.items || [])].reverse());

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

const showProgress = computed$3(() => progressVisible.value);

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
  return props.pluginId || props.sourcePluginId || 'guangyasync'
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
  return { manual: '手动上传', sync: '目录同步', watch: '目录监控', transfer: '整理联动' }[trigger] || '上传'
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

onMounted$2(async () => {
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
  const _component_v_icon = _resolveComponent$3("v-icon");
  const _component_v_chip = _resolveComponent$3("v-chip");
  const _component_v_btn = _resolveComponent$3("v-btn");
  const _component_v_progress_linear = _resolveComponent$3("v-progress-linear");

  return (_openBlock$3(), _createElementBlock$3("div", _hoisted_1$3, [
    _createElementVNode$3("div", _hoisted_2$3, [
      _createElementVNode$3("span", _hoisted_3$3, [
        _createVNode$3(_component_v_icon, {
          icon: "mdi-history",
          size: "18",
          color: "#6366f1",
          class: "mr-1"
        }),
        _cache[0] || (_cache[0] = _createTextVNode$3(" 上传记录 ", -1))
      ]),
      _createElementVNode$3("div", _hoisted_4$3, [
        _createVNode$3(_component_v_chip, {
          size: "x-small",
          variant: "tonal",
          color: "primary"
        }, {
          default: _withCtx$3(() => [
            _createTextVNode$3("共 " + _toDisplayString$3(history.value.length) + " 条", 1)
          ]),
          _: 1
        }),
        _createVNode$3(_component_v_btn, {
          size: "x-small",
          variant: "text",
          icon: "mdi-refresh",
          loading: loading.value,
          onClick: loadHistory
        }, null, 8, ["loading"]),
        _createVNode$3(_component_v_btn, {
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
      ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_5$3, [
          _createElementVNode$3("div", _hoisted_6$3, [
            _createVNode$3(_component_v_chip, {
              size: "x-small",
              variant: "tonal",
              color: progress.value.active ? 'info' : 'success'
            }, {
              default: _withCtx$3(() => [
                _createTextVNode$3(_toDisplayString$3(triggerLabel(progress.value.trigger)), 1)
              ]),
              _: 1
            }, 8, ["color"]),
            _createElementVNode$3("span", _hoisted_7$2, _toDisplayString$3(progress.value.current || progress.value.message || '-'), 1),
            _createElementVNode$3("span", _hoisted_8$2, _toDisplayString$3(progress.value.percent) + "%", 1)
          ]),
          _createVNode$3(_component_v_progress_linear, {
            "model-value": progress.value.percent,
            color: progress.value.active ? 'primary' : 'success',
            height: "8",
            rounded: ""
          }, null, 8, ["model-value", "color"]),
          _createElementVNode$3("div", _hoisted_9$1, " 成功 " + _toDisplayString$3(progress.value.uploaded) + " · 跳过 " + _toDisplayString$3(progress.value.skipped) + " · 失败 " + _toDisplayString$3(progress.value.failed) + " · 共 " + _toDisplayString$3(progress.value.total), 1),
          (progressItems.value.length)
            ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_10$1, [
                (_openBlock$3(true), _createElementBlock$3(_Fragment$2, null, _renderList$2(progressItems.value, (it, idx) => {
                  return (_openBlock$3(), _createElementBlock$3("div", {
                    key: `${it.name}-${idx}`,
                    class: "uh-pitem"
                  }, [
                    _createVNode$3(_component_v_icon, {
                      icon: itemIcon(it.status),
                      color: itemColor(it.status),
                      size: "15"
                    }, null, 8, ["icon", "color"]),
                    _createElementVNode$3("span", {
                      class: "uh-pitem__name",
                      title: it.remote || it.local
                    }, _toDisplayString$3(it.name), 9, _hoisted_11),
                    (it.status === 'running')
                      ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_12, _toDisplayString$3(itemPhaseLabel(it.phase)), 1))
                      : _createCommentVNode$3("", true),
                    (it.status === 'running')
                      ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_13, _toDisplayString$3(it.percent) + "%", 1))
                      : (_openBlock$3(), _createElementBlock$3(_Fragment$2, { key: 2 }, [
                          (it.flash)
                            ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_14, "秒传"))
                            : _createCommentVNode$3("", true),
                          _createVNode$3(_component_v_chip, {
                            size: "x-small",
                            variant: "tonal",
                            color: itemColor(it.status)
                          }, {
                            default: _withCtx$3(() => [
                              _createTextVNode$3(_toDisplayString$3(itemStatusLabel(it.status)), 1)
                            ]),
                            _: 2
                          }, 1032, ["color"])
                        ], 64))
                  ]))
                }), 128))
              ]))
            : _createCommentVNode$3("", true),
          (progress.value.total > progressItems.value.length)
            ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_15, " 仅显示最近 " + _toDisplayString$3(progressItems.value.length) + " / 共 " + _toDisplayString$3(progress.value.total) + " 个文件，完整结果见下方记录 ", 1))
            : _createCommentVNode$3("", true)
        ]))
      : _createCommentVNode$3("", true),
    _cache[3] || (_cache[3] = _createElementVNode$3("div", { class: "uh-legend" }, " 「秒传」表示云端已存在相同内容（按文件 MD5 命中），实际上传字节为 0，仅新增云端文件引用。 ", -1)),
    _createElementVNode$3("div", _hoisted_16, [
      (_openBlock$3(), _createElementBlock$3(_Fragment$2, null, _renderList$2(filterOptions, (opt) => {
        return _createVNode$3(_component_v_chip, {
          key: opt.value,
          size: "x-small",
          variant: "tonal",
          color: filter.value === opt.value ? 'primary' : 'default',
          onClick: $event => (filter.value = opt.value)
        }, {
          default: _withCtx$3(() => [
            _createTextVNode$3(_toDisplayString$3(opt.title), 1)
          ]),
          _: 2
        }, 1032, ["color", "onClick"])
      }), 64))
    ]),
    _createElementVNode$3("div", _hoisted_17, [
      (!filtered.value.length)
        ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_18, "暂无上传记录"))
        : _createCommentVNode$3("", true),
      (_openBlock$3(true), _createElementBlock$3(_Fragment$2, null, _renderList$2(filtered.value, (item, idx) => {
        return (_openBlock$3(), _createElementBlock$3("div", {
          key: `${item.time}-${idx}`,
          class: "uh-item"
        }, [
          _createVNode$3(_component_v_icon, {
            icon: actionIcon(item.action),
            color: actionColor(item.action),
            size: "16"
          }, null, 8, ["icon", "color"]),
          _createElementVNode$3("div", _hoisted_19, [
            _createElementVNode$3("div", _hoisted_20, _toDisplayString$3(item.name), 1),
            _createElementVNode$3("div", _hoisted_21, [
              _createElementVNode$3("span", null, _toDisplayString$3(formatTime(item.time)), 1),
              _cache[1] || (_cache[1] = _createElementVNode$3("span", { class: "uh-sep" }, "·", -1)),
              _createElementVNode$3("span", null, _toDisplayString$3(triggerLabel(item.trigger)), 1),
              (item.size)
                ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_22, "·"))
                : _createCommentVNode$3("", true),
              (item.size)
                ? (_openBlock$3(), _createElementBlock$3("span", _hoisted_23, _toDisplayString$3(formatSize(item.size)), 1))
                : _createCommentVNode$3("", true),
              _createElementVNode$3("span", {
                class: "uh-item__remote",
                title: item.remote || item.local
              }, _toDisplayString$3(item.remote || item.local), 9, _hoisted_24)
            ]),
            (item.error)
              ? (_openBlock$3(), _createElementBlock$3("div", _hoisted_25, _toDisplayString$3(item.error), 1))
              : _createCommentVNode$3("", true)
          ]),
          (item.flash && item.action === 'uploaded')
            ? (_openBlock$3(), _createBlock$3(_component_v_chip, {
                key: 0,
                size: "x-small",
                variant: "tonal",
                color: "info",
                class: "uh-item__flash"
              }, {
                default: _withCtx$3(() => [...(_cache[2] || (_cache[2] = [
                  _createTextVNode$3(" 秒传 ", -1)
                ]))]),
                _: 1
              }))
            : _createCommentVNode$3("", true),
          _createVNode$3(_component_v_chip, {
            size: "x-small",
            variant: "tonal",
            color: actionColor(item.action)
          }, {
            default: _withCtx$3(() => [
              _createTextVNode$3(_toDisplayString$3(actionLabel(item.action)), 1)
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
const UploadHistory = /*#__PURE__*/_export_sfc(_sfc_main$3, [['__scopeId',"data-v-4ceb7da0"]]);

const CloudOrganize_vue_vue_type_style_index_0_scoped_deae7b97_lang = '';

const {resolveComponent:_resolveComponent$2,createVNode:_createVNode$2,createTextVNode:_createTextVNode$2,createElementVNode:_createElementVNode$2,withCtx:_withCtx$2,toDisplayString:_toDisplayString$2,openBlock:_openBlock$2,createBlock:_createBlock$2,createCommentVNode:_createCommentVNode$2,renderList:_renderList$1,Fragment:_Fragment$1,createElementBlock:_createElementBlock$2} = await importShared('vue');


const _hoisted_1$2 = { class: "co-card" };
const _hoisted_2$2 = { class: "co-header" };
const _hoisted_3$2 = { class: "co-title" };
const _hoisted_4$2 = { class: "co-grid" };
const _hoisted_5$2 = { class: "co-options" };
const _hoisted_6$2 = { class: "co-actions" };
const _hoisted_7$1 = {
  key: 1,
  class: "co-preview"
};
const _hoisted_8$1 = { class: "co-hint" };

const {computed: computed$2,reactive: reactive$2,ref: ref$2,watch: watch$1} = await importShared('vue');


const _sfc_main$2 = {
  __name: 'CloudOrganize',
  props: {
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
},
  setup(__props) {

const props = __props;
const form = reactive$2({
  source_dir: '', target_dir: '', transfer_type: 'move', media_type: 'auto',
  library_type_folder: true, library_category_folder: false, scrape: false,
});
const action = ref$2('');
const busy = computed$2(() => Boolean(action.value));
const valid = computed$2(() => form.source_dir.trim() && form.target_dir.trim());
const feedback = ref$2({ type: 'info', text: '' });
const previewItems = ref$2([]);
const transferTypes = [{ title: '移动', value: 'move' }, { title: '复制（保留原资源）', value: 'copy' }];
const mediaTypes = [{ title: '自动识别', value: 'auto' }, { title: '电影', value: 'movie' }, { title: '电视剧', value: 'tv' }];
const currentPluginId = computed$2(() => props.pluginId || props.sourcePluginId || 'guangyasync');
watch$1(form, () => { previewItems.value = []; feedback.value.text = ''; });

async function submit(preview) {
  if (busy.value || !valid.value) return
  action.value = preview ? 'preview' : 'organize';
  feedback.value = { type: 'info', text: preview ? '正在递归读取目录并识别媒体，请稍候…' : '正在识别资源并提交整理请求，请稍候…' };
  previewItems.value = [];
  try {
    const path = `plugin/${currentPluginId.value}/organize`;
    const payload = { ...form, preview };
    let result;
    if (props.api?.post) {
      result = await props.api.post(path, payload, { feedback: 'silent', timeout: 0 });
    } else {
      const response = await fetch(`/api/v1/${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      result = await response.json();
    }
    if (preview && Array.isArray(result?.data?.result?.items)) previewItems.value = result.data.result.items;
    feedback.value = { type: result?.success ? 'success' : 'warning', text: result?.message || (result?.success ? '请求已完成' : '请求失败') };
  } catch (error) {
    feedback.value = { type: 'error', text: `整理请求未能确认：${error.message || error}。请先检查原生整理队列，避免重复提交。` };
  } finally {
    action.value = '';
  }
}

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$2("v-icon");
  const _component_v_chip = _resolveComponent$2("v-chip");
  const _component_v_select = _resolveComponent$2("v-select");
  const _component_v_checkbox = _resolveComponent$2("v-checkbox");
  const _component_v_btn = _resolveComponent$2("v-btn");
  const _component_v_alert = _resolveComponent$2("v-alert");
  const _component_v_table = _resolveComponent$2("v-table");

  return (_openBlock$2(), _createElementBlock$2("section", _hoisted_1$2, [
    _createElementVNode$2("div", _hoisted_2$2, [
      _createElementVNode$2("div", null, [
        _createElementVNode$2("div", _hoisted_3$2, [
          _createVNode$2(_component_v_icon, {
            icon: "mdi-folder-sync-outline",
            size: "20",
            class: "mr-1"
          }),
          _cache[9] || (_cache[9] = _createTextVNode$2("云盘资源整理", -1))
        ]),
        _cache[10] || (_cache[10] = _createElementVNode$2("div", { class: "co-subtitle" }, "选择转存资源所在目录，按 MoviePilot 的识别与命名规则整理到光鸭媒体库。", -1))
      ]),
      _createVNode$2(_component_v_chip, {
        size: "small",
        color: "primary",
        variant: "tonal"
      }, {
        default: _withCtx$2(() => [...(_cache[11] || (_cache[11] = [
          _createTextVNode$2("云盘内整理", -1)
        ]))]),
        _: 1
      })
    ]),
    _createElementVNode$2("div", _hoisted_4$2, [
      _createVNode$2(RemoteDirPicker, {
        modelValue: form.source_dir,
        "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form.source_dir) = $event)),
        api: __props.api,
        "plugin-id": __props.pluginId,
        "source-plugin-id": __props.sourcePluginId,
        label: "待整理目录（光鸭云盘）",
        placeholder: "/待整理",
        disabled: busy.value,
        hint: "请选择已经存在的转存目录，将递归整理其中的资源。"
      }, null, 8, ["modelValue", "api", "plugin-id", "source-plugin-id", "disabled"]),
      _createVNode$2(RemoteDirPicker, {
        modelValue: form.target_dir,
        "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.target_dir) = $event)),
        api: __props.api,
        "plugin-id": __props.pluginId,
        "source-plugin-id": __props.sourcePluginId,
        label: "媒体库目标目录（光鸭云盘）",
        placeholder: "/媒体库",
        disabled: busy.value,
        hint: "目标目录可手动填写；缺失目录会在实际整理时创建。"
      }, null, 8, ["modelValue", "api", "plugin-id", "source-plugin-id", "disabled"]),
      _createVNode$2(_component_v_select, {
        modelValue: form.transfer_type,
        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.transfer_type) = $event)),
        label: "整理方式",
        items: transferTypes,
        disabled: busy.value,
        "item-title": "title",
        "item-value": "value",
        density: "compact",
        variant: "outlined",
        "hide-details": ""
      }, null, 8, ["modelValue", "disabled"]),
      _createVNode$2(_component_v_select, {
        modelValue: form.media_type,
        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((form.media_type) = $event)),
        label: "媒体类型",
        items: mediaTypes,
        disabled: busy.value,
        "item-title": "title",
        "item-value": "value",
        density: "compact",
        variant: "outlined",
        "hide-details": ""
      }, null, 8, ["modelValue", "disabled"])
    ]),
    _createElementVNode$2("div", _hoisted_5$2, [
      _createVNode$2(_component_v_checkbox, {
        modelValue: form.library_type_folder,
        "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((form.library_type_folder) = $event)),
        label: "按电影 / 电视剧分目录",
        disabled: busy.value,
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue", "disabled"]),
      _createVNode$2(_component_v_checkbox, {
        modelValue: form.library_category_folder,
        "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((form.library_category_folder) = $event)),
        label: "按媒体类别分目录",
        disabled: busy.value,
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue", "disabled"]),
      _createVNode$2(_component_v_checkbox, {
        modelValue: form.scrape,
        "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((form.scrape) = $event)),
        label: "刮削元数据",
        disabled: busy.value,
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue", "disabled"])
    ]),
    _cache[15] || (_cache[15] = _createElementVNode$2("div", { class: "co-hint" }, "包含子目录。移动会将整理成功的文件移出待整理目录；复制会保留原资源。两个目录须相互独立。", -1)),
    _createElementVNode$2("div", _hoisted_6$2, [
      _createVNode$2(_component_v_btn, {
        variant: "tonal",
        "prepend-icon": "mdi-eye-outline",
        loading: action.value === 'preview',
        disabled: busy.value || !valid.value,
        onClick: _cache[7] || (_cache[7] = $event => (submit(true)))
      }, {
        default: _withCtx$2(() => [...(_cache[12] || (_cache[12] = [
          _createTextVNode$2("预览整理结果", -1)
        ]))]),
        _: 1
      }, 8, ["loading", "disabled"]),
      _createVNode$2(_component_v_btn, {
        color: "primary",
        "prepend-icon": "mdi-folder-sync-outline",
        loading: action.value === 'organize',
        disabled: busy.value || !valid.value,
        onClick: _cache[8] || (_cache[8] = $event => (submit(false)))
      }, {
        default: _withCtx$2(() => [...(_cache[13] || (_cache[13] = [
          _createTextVNode$2("开始整理", -1)
        ]))]),
        _: 1
      }, 8, ["loading", "disabled"])
    ]),
    (feedback.value.text)
      ? (_openBlock$2(), _createBlock$2(_component_v_alert, {
          key: 0,
          type: feedback.value.type,
          variant: "tonal",
          density: "compact"
        }, {
          default: _withCtx$2(() => [
            _createTextVNode$2(_toDisplayString$2(feedback.value.text), 1)
          ]),
          _: 1
        }, 8, ["type"]))
      : _createCommentVNode$2("", true),
    (previewItems.value.length)
      ? (_openBlock$2(), _createElementBlock$2("div", _hoisted_7$1, [
          _createElementVNode$2("div", _hoisted_8$1, "识别预览，共 " + _toDisplayString$2(previewItems.value.length) + " 项。实际整理会重新核对文件与覆盖规则。", 1),
          _createVNode$2(_component_v_table, { density: "compact" }, {
            default: _withCtx$2(() => [
              _cache[14] || (_cache[14] = _createElementVNode$2("thead", null, [
                _createElementVNode$2("tr", null, [
                  _createElementVNode$2("th", null, "源文件"),
                  _createElementVNode$2("th", null, "整理目标"),
                  _createElementVNode$2("th", null, "结果")
                ])
              ], -1)),
              _createElementVNode$2("tbody", null, [
                (_openBlock$2(true), _createElementBlock$2(_Fragment$1, null, _renderList$1(previewItems.value, (item, index) => {
                  return (_openBlock$2(), _createElementBlock$2("tr", {
                    key: `${item.source}-${index}`
                  }, [
                    _createElementVNode$2("td", null, _toDisplayString$2(item.source), 1),
                    _createElementVNode$2("td", null, _toDisplayString$2(item.target || '—'), 1),
                    _createElementVNode$2("td", null, [
                      _createVNode$2(_component_v_icon, {
                        icon: item.success ? 'mdi-check-circle-outline' : 'mdi-alert-circle-outline',
                        color: item.success ? 'success' : 'warning',
                        size: "16",
                        class: "mr-1"
                      }, null, 8, ["icon", "color"]),
                      _createTextVNode$2(_toDisplayString$2(item.message || (item.success ? '可整理' : '未能识别或规划')), 1)
                    ])
                  ]))
                }), 128))
              ])
            ]),
            _: 1
          })
        ]))
      : _createCommentVNode$2("", true),
    _cache[16] || (_cache[16] = _createElementVNode$2("div", { class: "co-hint" }, "任务进度和结果请在 MoviePilot「整理队列」与「整理记录」中查看；识别失败的资源可在那里手动指定媒体后重试。", -1))
  ]))
}
}

};
const CloudOrganize = /*#__PURE__*/_export_sfc(_sfc_main$2, [['__scopeId',"data-v-deae7b97"]]);

const ShareAutomation_vue_vue_type_style_index_0_scoped_911e9202_lang = '';

const {resolveComponent:_resolveComponent$1,createVNode:_createVNode$1,createTextVNode:_createTextVNode$1,createElementVNode:_createElementVNode$1,withCtx:_withCtx$1,toDisplayString:_toDisplayString$1,openBlock:_openBlock$1,createBlock:_createBlock$1,createCommentVNode:_createCommentVNode$1,renderList:_renderList,Fragment:_Fragment,createElementBlock:_createElementBlock$1} = await importShared('vue');


const _hoisted_1$1 = { class: "sa-card" };
const _hoisted_2$1 = { class: "sa-title" };
const _hoisted_3$1 = { class: "sa-grid" };
const _hoisted_4$1 = { class: "sa-actions" };
const _hoisted_5$1 = { class: "sa-actions" };
const _hoisted_6$1 = { class: "sa-actions" };
const _hoisted_7 = {
  key: 1,
  class: "sa-jobs"
};
const _hoisted_8 = { class: "sa-hint" };
const _hoisted_9 = { class: "sa-hint" };
const _hoisted_10 = {
  key: 2,
  class: "sa-hint"
};

const {computed: computed$1,onMounted: onMounted$1,onUnmounted,reactive: reactive$1,ref: ref$1,watch} = await importShared('vue');

const _sfc_main$1 = {
  __name: 'ShareAutomation',
  props: { api: { type: Object, default: () => ({}) }, pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' }, config: { type: Object, default: () => ({}) } },
  emits: ['update'],
  setup(__props, { emit: __emit }) {

const props = __props;
const emit = __emit;
const defaults = { telegram_enabled: false, telegram_user_ids: '', share_source_dir: '/待整理', share_target_dir: '/Media',
  share_transfer_type: 'move', share_scrape: false, share_type_folder: true, share_category_folder: false };
const form = reactive$1({ ...defaults });
watch(() => props.config, (config) => { for (const key of Object.keys(defaults)) form[key] = config[key] ?? defaults[key]; }, { immediate: true });
const saving = ref$1(false), submitting = ref$1(false), refreshing = ref$1(false), text = ref$1(''), jobs = ref$1([]);
const feedback = ref$1({ type: 'info', text: '' });
const prefix = computed$1(() => `plugin/${props.pluginId || props.sourcePluginId || 'guangyasync'}`);
const labels = { queued: '已排队', inspecting: '读取分享', saving: '转存中', confirming: '核对转存', saved: '转存完成',
  organizing: '整理中', completed: '已完成', partial: '请检查整理队列', failed: '失败', needs_review: '待人工核对' };
let timer;
async function request(path, payload) {
  if (payload !== undefined) {
    if (!props.api?.post) throw new Error('宿主 API 尚未就绪，请重新打开页面')
    return props.api.post(`${prefix.value}/${path}`, payload, { feedback: 'silent' })
  }
  if (!props.api?.get) throw new Error('宿主 API 尚未就绪，请重新打开页面')
  return props.api.get(`${prefix.value}/${path}`, { feedback: 'silent' })
}
async function save() {
  saving.value = true;
  try {
    const result = await request('config', { ...form });
    feedback.value = { type: result.success ? 'success' : 'error', text: result.message || '保存失败' };
    if (result.success) emit('update', result.data);
  } catch (error) { feedback.value = { type: 'error', text: error.message || '保存失败' }; }
  finally { saving.value = false; }
}
async function submit() {
  submitting.value = true;
  try {
    const result = await request('share/submit', { text: text.value });
    feedback.value = { type: result.success ? 'success' : 'error', text: `${result.message || '提交失败'} ${result.data?.id || ''}` };
    if (result.success) text.value = '';
    await load();
  } catch (error) { feedback.value = { type: 'error', text: `${error.message || '提交结果未确认'}，请先刷新任务，避免重复提交。` }; }
  finally { submitting.value = false; }
}
async function load() {
  if (refreshing.value) return
  refreshing.value = true;
  try { const result = await request('share/jobs'); if (result.success) jobs.value = result.data?.items || []; }
  catch (error) { feedback.value = { type: 'error', text: error.message || '读取任务失败' }; }
  finally { refreshing.value = false; }
}
onMounted$1(() => { load(); timer = setInterval(() => { if (!document.hidden) load(); }, 5000); });
onUnmounted(() => clearInterval(timer));

return (_ctx, _cache) => {
  const _component_v_icon = _resolveComponent$1("v-icon");
  const _component_v_switch = _resolveComponent$1("v-switch");
  const _component_v_text_field = _resolveComponent$1("v-text-field");
  const _component_v_select = _resolveComponent$1("v-select");
  const _component_v_checkbox = _resolveComponent$1("v-checkbox");
  const _component_v_btn = _resolveComponent$1("v-btn");
  const _component_v_divider = _resolveComponent$1("v-divider");
  const _component_v_textarea = _resolveComponent$1("v-textarea");
  const _component_v_alert = _resolveComponent$1("v-alert");
  const _component_v_table = _resolveComponent$1("v-table");

  return (_openBlock$1(), _createElementBlock$1("section", _hoisted_1$1, [
    _createElementVNode$1("div", _hoisted_2$1, [
      _createVNode$1(_component_v_icon, {
        icon: "mdi-telegram",
        size: "20"
      }),
      _cache[9] || (_cache[9] = _createTextVNode$1(" 分享转存并整理", -1))
    ]),
    _cache[14] || (_cache[14] = _createElementVNode$1("div", { class: "sa-hint" }, "发光鸭链接给 MoviePilot 的 Telegram Bot，自动转存，再按媒体库规则整理。每条链接独立排队。", -1)),
    _createVNode$1(_component_v_switch, {
      modelValue: form.telegram_enabled,
      "onUpdate:modelValue": _cache[0] || (_cache[0] = $event => ((form.telegram_enabled) = $event)),
      label: "接收 Telegram 分享",
      color: "primary",
      density: "compact",
      "hide-details": ""
    }, null, 8, ["modelValue"]),
    _createVNode$1(_component_v_text_field, {
      modelValue: form.telegram_user_ids,
      "onUpdate:modelValue": _cache[1] || (_cache[1] = $event => ((form.telegram_user_ids) = $event)),
      label: "允许的 Telegram 用户 ID",
      placeholder: "123456789, 987654321",
      hint: "数字 ID，逗号分隔。还需在 MoviePilot「通知渠道」配置 Telegram Bot 与交互权限。",
      "persistent-hint": "",
      density: "compact",
      variant: "outlined"
    }, null, 8, ["modelValue"]),
    _createElementVNode$1("div", _hoisted_3$1, [
      _createVNode$1(RemoteDirPicker, {
        modelValue: form.share_source_dir,
        "onUpdate:modelValue": _cache[2] || (_cache[2] = $event => ((form.share_source_dir) = $event)),
        api: __props.api,
        "plugin-id": __props.pluginId,
        "source-plugin-id": __props.sourcePluginId,
        label: "转存源目录（光鸭）",
        hint: "每次转存到此目录下的独立任务子目录。"
      }, null, 8, ["modelValue", "api", "plugin-id", "source-plugin-id"]),
      _createVNode$1(RemoteDirPicker, {
        modelValue: form.share_target_dir,
        "onUpdate:modelValue": _cache[3] || (_cache[3] = $event => ((form.share_target_dir) = $event)),
        api: __props.api,
        "plugin-id": __props.pluginId,
        "source-plugin-id": __props.sourcePluginId,
        label: "媒体库目录（光鸭）",
        hint: "须与源目录相互独立。新目录可手动填写。"
      }, null, 8, ["modelValue", "api", "plugin-id", "source-plugin-id"])
    ]),
    _createVNode$1(_component_v_select, {
      modelValue: form.share_transfer_type,
      "onUpdate:modelValue": _cache[4] || (_cache[4] = $event => ((form.share_transfer_type) = $event)),
      items: [{ title: '移动', value: 'move' }, { title: '复制', value: 'copy' }],
      label: "整理方式",
      density: "compact",
      variant: "outlined",
      "hide-details": ""
    }, null, 8, ["modelValue"]),
    _createElementVNode$1("div", _hoisted_4$1, [
      _createVNode$1(_component_v_checkbox, {
        modelValue: form.share_type_folder,
        "onUpdate:modelValue": _cache[5] || (_cache[5] = $event => ((form.share_type_folder) = $event)),
        label: "按电影 / 电视剧分目录",
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue"]),
      _createVNode$1(_component_v_checkbox, {
        modelValue: form.share_category_folder,
        "onUpdate:modelValue": _cache[6] || (_cache[6] = $event => ((form.share_category_folder) = $event)),
        label: "按媒体类别分目录",
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue"]),
      _createVNode$1(_component_v_checkbox, {
        modelValue: form.share_scrape,
        "onUpdate:modelValue": _cache[7] || (_cache[7] = $event => ((form.share_scrape) = $event)),
        label: "刮削元数据",
        density: "compact",
        "hide-details": ""
      }, null, 8, ["modelValue"])
    ]),
    _createElementVNode$1("div", _hoisted_5$1, [
      _createVNode$1(_component_v_btn, {
        color: "primary",
        variant: "tonal",
        loading: saving.value,
        onClick: save
      }, {
        default: _withCtx$1(() => [...(_cache[10] || (_cache[10] = [
          _createTextVNode$1("保存分享设置", -1)
        ]))]),
        _: 1
      }, 8, ["loading"])
    ]),
    _cache[15] || (_cache[15] = _createElementVNode$1("div", { class: "sa-hint" }, "私聊发送一条纯链接即可；开启全局 AI 或粘贴整段分享文案时，使用 /guangya 链接 提取码：1234。重复分享会返回已有任务。", -1)),
    _createVNode$1(_component_v_divider),
    _createVNode$1(_component_v_textarea, {
      modelValue: text.value,
      "onUpdate:modelValue": _cache[8] || (_cache[8] = $event => ((text).value = $event)),
      label: "手动提交分享（使用已保存的目录设置）",
      rows: "2",
      "auto-grow": "",
      density: "compact",
      variant: "outlined",
      "hide-details": ""
    }, null, 8, ["modelValue"]),
    _createElementVNode$1("div", _hoisted_6$1, [
      _createVNode$1(_component_v_btn, {
        color: "primary",
        disabled: !text.value.trim(),
        loading: submitting.value,
        onClick: submit
      }, {
        default: _withCtx$1(() => [...(_cache[11] || (_cache[11] = [
          _createTextVNode$1("转存并整理", -1)
        ]))]),
        _: 1
      }, 8, ["disabled", "loading"]),
      _createVNode$1(_component_v_btn, {
        variant: "text",
        loading: refreshing.value,
        onClick: load
      }, {
        default: _withCtx$1(() => [...(_cache[12] || (_cache[12] = [
          _createTextVNode$1("刷新任务", -1)
        ]))]),
        _: 1
      }, 8, ["loading"])
    ]),
    (feedback.value.text)
      ? (_openBlock$1(), _createBlock$1(_component_v_alert, {
          key: 0,
          type: feedback.value.type,
          variant: "tonal",
          density: "compact"
        }, {
          default: _withCtx$1(() => [
            _createTextVNode$1(_toDisplayString$1(feedback.value.text), 1)
          ]),
          _: 1
        }, 8, ["type"]))
      : _createCommentVNode$1("", true),
    (jobs.value.length)
      ? (_openBlock$1(), _createElementBlock$1("div", _hoisted_7, [
          _createVNode$1(_component_v_table, { density: "compact" }, {
            default: _withCtx$1(() => [
              _cache[13] || (_cache[13] = _createElementVNode$1("thead", null, [
                _createElementVNode$1("tr", null, [
                  _createElementVNode$1("th", null, "任务"),
                  _createElementVNode$1("th", null, "状态"),
                  _createElementVNode$1("th", null, "资源 / 源目录"),
                  _createElementVNode$1("th", null, "结果")
                ])
              ], -1)),
              _createElementVNode$1("tbody", null, [
                (_openBlock$1(true), _createElementBlock$1(_Fragment, null, _renderList(jobs.value, (job) => {
                  return (_openBlock$1(), _createElementBlock$1("tr", {
                    key: job.id
                  }, [
                    _createElementVNode$1("td", null, [
                      _createTextVNode$1(_toDisplayString$1(job.id), 1),
                      _createElementVNode$1("div", _hoisted_8, _toDisplayString$1(new Date(job.created_at * 1000).toLocaleString()), 1)
                    ]),
                    _createElementVNode$1("td", null, _toDisplayString$1(labels[job.state] || job.state), 1),
                    _createElementVNode$1("td", null, [
                      _createTextVNode$1(_toDisplayString$1(job.title || '待读取'), 1),
                      _createElementVNode$1("div", _hoisted_9, _toDisplayString$1(job.staging_dir), 1)
                    ]),
                    _createElementVNode$1("td", null, _toDisplayString$1(job.message), 1)
                  ]))
                }), 128))
              ])
            ]),
            _: 1
          })
        ]))
      : (_openBlock$1(), _createElementBlock$1("div", _hoisted_10, "暂无分享任务。")),
    _cache[16] || (_cache[16] = _createElementVNode$1("div", { class: "sa-hint" }, "任务中断或转存结果不明时会暂停，请检查光鸭目录和 MoviePilot 整理队列。自动处理只扫描本次任务目录；未识别的文件会保留，供手动处理。", -1))
  ]))
}
}

};
const ShareAutomation = /*#__PURE__*/_export_sfc(_sfc_main$1, [['__scopeId',"data-v-911e9202"]]);

const AppPage_vue_vue_type_style_index_0_scoped_590ae329_lang = '';

const {resolveComponent:_resolveComponent,createVNode:_createVNode,createElementVNode:_createElementVNode,toDisplayString:_toDisplayString,createTextVNode:_createTextVNode,withCtx:_withCtx,openBlock:_openBlock,createBlock:_createBlock,createCommentVNode:_createCommentVNode,createElementBlock:_createElementBlock} = await importShared('vue');


const _hoisted_1 = { class: "ap-page" };
const _hoisted_2 = { class: "ap-header" };
const _hoisted_3 = { class: "ap-header__left" };
const _hoisted_4 = { class: "ap-header__icon" };
const _hoisted_5 = { class: "ap-header__right" };
const _hoisted_6 = {
  key: 4,
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
  sync_remote_dir: '/',
});

const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'guangyasync');

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
          _createElementVNode("div", { class: "ap-header__title" }, "光鸭同步"),
          _createElementVNode("div", { class: "ap-header__sub" }, "整理光鸭云盘资源，或把服务器文件上传到云盘")
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
            _createTextVNode(" 未登录光鸭云盘。请先点击右上角「插件页」扫码登录，登录后即可整理云盘资源、上传与同步。 ", -1)
          ]))]),
          _: 1
        }))
      : _createCommentVNode("", true),
    (status.logged_in)
      ? (_openBlock(), _createBlock(ShareAutomation, {
          key: 1,
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId,
          config: fullConfig.value,
          onUpdate: onConfigUpdate
        }, null, 8, ["api", "plugin-id", "source-plugin-id", "config"]))
      : _createCommentVNode("", true),
    (status.logged_in)
      ? (_openBlock(), _createBlock(CloudOrganize, {
          key: 2,
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId
        }, null, 8, ["api", "plugin-id", "source-plugin-id"]))
      : _createCommentVNode("", true),
    _createVNode(DirectorySync, {
      api: __props.api,
      "plugin-id": __props.pluginId,
      "source-plugin-id": __props.sourcePluginId,
      config: fullConfig.value,
      onUpdate: onConfigUpdate
    }, null, 8, ["api", "plugin-id", "source-plugin-id", "config"]),
    (status.logged_in)
      ? (_openBlock(), _createBlock(ManualUpload, {
          key: 3,
          api: __props.api,
          "plugin-id": __props.pluginId,
          "source-plugin-id": __props.sourcePluginId,
          "logged-in": status.logged_in,
          "default-remote-dir": status.sync_remote_dir
        }, null, 8, ["api", "plugin-id", "source-plugin-id", "logged-in", "default-remote-dir"]))
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
const AppPage = /*#__PURE__*/_export_sfc(_sfc_main, [['__scopeId',"data-v-590ae329"]]);

export { AppPage as default };
