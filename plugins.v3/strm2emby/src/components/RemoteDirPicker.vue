<template>
  <div class="rdp-field">
    <v-text-field
      v-model="value"
      :label="label"
      :placeholder="placeholder"
      :disabled="disabled"
      density="compact"
      variant="outlined"
      hide-details
      class="rdp-input"
    >
      <template #append-inner>
        <v-btn
          variant="text"
          density="comfortable"
          size="small"
          :disabled="disabled"
          icon="mdi-folder-search-outline"
          :title="'浏览云盘目录'"
          @click="openPicker"
        />
      </template>
    </v-text-field>

    <v-dialog v-model="dialog" max-width="520" scrollable>
      <div class="rdp-card">
        <div class="rdp-head">
          <span class="rdp-title">选择光鸭云盘目录</span>
          <v-btn variant="text" density="comfortable" size="small" icon="mdi-close" @click="dialog = false" />
        </div>

        <div class="rdp-toolbar">
          <v-btn
            variant="tonal"
            density="comfortable"
            size="small"
            icon="mdi-arrow-up"
            :disabled="!parentPath || loading"
            title="上一级"
            @click="goUp"
          />
          <v-text-field
            v-model="pathInput"
            label="当前路径"
            density="compact"
            variant="outlined"
            hide-details
            class="rdp-input"
            @keyup.enter="browse(pathInput)"
          />
          <v-btn
            variant="tonal"
            density="comfortable"
            size="small"
            icon="mdi-refresh"
            :loading="loading"
            title="刷新"
            @click="browse(currentPath)"
          />
        </div>

        <div class="rdp-list">
          <div v-if="loading" class="rdp-empty">正在读取云盘目录...</div>
          <div v-else-if="error" class="rdp-error">{{ error }}</div>
          <div v-else-if="!items.length" class="rdp-empty">此目录下没有子文件夹</div>
          <template v-else>
            <div
              v-for="entry in items"
              :key="entry.path"
              class="rdp-item"
              @click="browse(entry.path)"
            >
              <v-icon icon="mdi-folder" size="18" color="#f59e0b" />
              <span class="rdp-item__name">{{ entry.name }}</span>
              <v-icon icon="mdi-chevron-right" size="16" class="rdp-item__arrow" />
            </div>
          </template>
        </div>

        <div class="rdp-current">
          将选择：<strong>{{ currentPath || '/' }}</strong>
        </div>
        <div class="rdp-hint">也可以直接在输入框里手填新目录，上传时会自动创建。</div>

        <div class="rdp-actions">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" :disabled="loading" @click="choose">选择此目录</v-btn>
        </div>
      </div>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '/' },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  label: { type: String, default: '光鸭目标目录' },
  placeholder: { type: String, default: '/Media' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const value = computed({
  get: () => props.modelValue || '/',
  set: (next) => emit('update:modelValue', next),
})

const dialog = ref(false)
const currentPath = ref('/')
const parentPath = ref('')
const pathInput = ref('/')
const items = ref([])
const loading = ref(false)
const error = ref('')

const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'Strm2Emby')

async function request(path) {
  const apiPath = `plugin/${currentPluginId.value}${path}`
  if (props.api?.get) {
    return props.api.get(apiPath, { feedback: 'silent' })
  }
  const response = await fetch(`/api/v1/${apiPath}`, {
    headers: { 'Content-Type': 'application/json' },
  })
  return response.json()
}

function parentOf(path) {
  if (!path || path === '/') return ''
  const parts = path.split('/').filter(Boolean)
  parts.pop()
  return parts.length ? `/${parts.join('/')}` : '/'
}

async function browse(path) {
  const target = (path || '/').trim() || '/'
  loading.value = true
  error.value = ''
  try {
    const result = await request(`/remote/list?path=${encodeURIComponent(target)}`)
    if (!result.success) {
      // 目标目录可能还不存在（用户打算新建）：自动回退到最近的已存在父目录
      const fallback = parentOf(target)
      if (fallback && fallback !== target) {
        loading.value = false
        return browse(fallback)
      }
      error.value = result.message || '打开目录失败'
      return
    }
    const data = result.data || {}
    currentPath.value = data.path || target
    parentPath.value = data.parent || ''
    pathInput.value = currentPath.value
    items.value = Array.isArray(data.items) ? data.items : []
  } catch (err) {
    error.value = `打开目录失败：${err.message || err}`
  } finally {
    loading.value = false
  }
}

function openPicker() {
  currentPath.value = props.modelValue || '/'
  pathInput.value = currentPath.value
  items.value = []
  error.value = ''
  dialog.value = true
  browse(currentPath.value)
}

function goUp() {
  if (parentPath.value) {
    browse(parentPath.value)
  }
}

function choose() {
  emit('update:modelValue', currentPath.value || '/')
  dialog.value = false
}
</script>

<style scoped>
.rdp-field {
  width: 100%;
}

.rdp-card {
  background: rgb(var(--v-theme-surface, 255, 255, 255));
  color: rgb(var(--v-theme-on-surface, 0, 0, 0));
  border-radius: 12px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rdp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.rdp-title {
  font-size: 14px;
  font-weight: 600;
}

.rdp-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rdp-input {
  flex: 1;
  min-width: 0;
}

.rdp-list {
  min-height: 180px;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
}

.rdp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.rdp-item:last-child {
  border-bottom: none;
}

.rdp-item:hover {
  background: rgba(0, 0, 0, 0.035);
}

.rdp-item__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.rdp-item__arrow {
  opacity: 0.45;
}

.rdp-empty,
.rdp-error {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.5);
}

.rdp-error {
  color: #b3261e;
}

.rdp-current {
  font-size: 13px;
  word-break: break-all;
}

.rdp-hint {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.5);
}

.rdp-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
