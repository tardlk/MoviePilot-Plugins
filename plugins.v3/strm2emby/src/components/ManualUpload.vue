<template>
  <div class="mu-card">
    <div class="mu-card__header">
      <span class="mu-card__title">
        <v-icon icon="mdi-cloud-upload-outline" size="18" color="#f59e0b" class="mr-1" />
        手动上传
      </span>
      <v-chip size="x-small" variant="tonal" color="primary">已选 {{ selected.length }} 项</v-chip>
    </div>

    <div class="mu-grid">
      <!-- 服务器文件浏览 -->
      <div class="mu-browser">
        <div class="mu-toolbar">
          <v-text-field
            v-model="localPath"
            label="服务器目录"
            density="compact"
            variant="outlined"
            hide-details
            class="mu-input"
            placeholder="/vol2/1000/Media"
            @keyup.enter="browseLocal(localPath)"
          />
          <v-btn color="primary" variant="tonal" density="comfortable" :loading="fsLoading" icon="mdi-folder-search-outline" @click="browseLocal(localPath)" />
          <v-btn variant="tonal" density="comfortable" :disabled="!fsParent" icon="mdi-arrow-up" @click="browseLocal(fsParent)" />
        </div>
        <div class="mu-list">
          <div v-if="fsLoading" class="mu-empty">正在加载...</div>
          <div v-else-if="!fsItems.length" class="mu-empty">该目录为空</div>
          <div
            v-for="entry in fsItems"
            :key="entry.path"
            class="mu-item"
            :class="{ 'mu-item--selected': isSelected(entry.path) }"
          >
            <div class="mu-item__main" @click="onEntryClick(entry)">
              <v-icon
                :icon="entry.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline'"
                size="18"
                :color="entry.type === 'dir' ? '#f59e0b' : undefined"
              />
              <span class="mu-item__name">{{ entry.name }}</span>
              <span v-if="entry.type === 'file'" class="mu-item__meta">{{ formatSize(entry.size) }}</span>
            </div>
            <v-btn
              v-if="entry.type === 'dir'"
              variant="text"
              density="comfortable"
              size="x-small"
              icon="mdi-plus"
              :disabled="isSelected(entry.path)"
              @click.stop="addSelected(entry)"
            />
            <v-icon v-else-if="isSelected(entry.path)" icon="mdi-check-circle" size="18" color="success" class="mr-1" />
          </div>
        </div>
      </div>

      <!-- 已选与目标目录 -->
      <div class="mu-side">
        <v-text-field
          v-model="uploadRemoteDir"
          label="光鸭目标目录"
          density="compact"
          variant="outlined"
          hide-details
          class="mu-input"
          placeholder="/Media"
          @update:model-value="markRemoteDirTouched"
        />
        <div class="mu-selected">
          <v-chip
            v-for="item in selected"
            :key="item.path"
            size="small"
            variant="tonal"
            closable
            @click:close="removeSelected(item.path)"
          >
            <v-icon :icon="item.type === 'dir' ? 'mdi-folder' : 'mdi-file-outline'" size="14" start />
            {{ item.name }}
          </v-chip>
          <span v-if="!selected.length" class="mu-selected__empty">尚未选择文件或文件夹</span>
        </div>
        <div class="mu-actions">
          <v-btn
            color="primary"
            :loading="uploading"
            :disabled="!selected.length || !loggedIn"
            prepend-icon="mdi-cloud-upload-outline"
            @click="startUpload"
          >
            开始上传
          </v-btn>
          <v-btn v-if="selected.length" variant="text" @click="clearSelected">清空</v-btn>
        </div>
        <v-alert v-if="feedback.text" :type="feedback.type || 'info'" variant="tonal" density="compact">
          {{ feedback.text }}
        </v-alert>
        <div class="mu-hint">同名文件按「目录同步」的同名策略处理；手动上传不会删除本地源文件。</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  // 宿主注入的实例作用域 API 客户端
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  // 是否已登录光鸭云盘（由父组件传入，用于禁用上传按钮）
  loggedIn: { type: Boolean, default: false },
  // 初始浏览目录与默认目标目录（可由父组件异步传入）
  defaultSourceDir: { type: String, default: '' },
  defaultRemoteDir: { type: String, default: '/' },
})

const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'Strm2Emby')
const localPath = ref('')
const fsItems = ref([])
const fsParent = ref('')
const fsLoading = ref(false)
const selected = ref([])
const uploading = ref(false)
const uploadRemoteDir = ref(props.defaultRemoteDir || '/')
const remoteDirTouched = ref(false)
const feedback = ref({ type: '', text: '' })

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
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const response = await fetch(`/api/v1/${pluginPath(path)}`, { headers, ...options })
  return response.json()
}

function setFeedback(type, text) {
  feedback.value = { type, text }
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function markRemoteDirTouched() {
  remoteDirTouched.value = true
}

async function browseLocal(path) {
  fsLoading.value = true
  try {
    const query = path ? `?path=${encodeURIComponent(path)}` : ''
    const result = await request(`/fs/list${query}`)
    if (!result.success) {
      setFeedback('error', result.message || '打开目录失败')
      return
    }
    const data = result.data || {}
    localPath.value = data.path || path || '/'
    fsParent.value = data.parent || ''
    fsItems.value = Array.isArray(data.items) ? data.items : []
  } catch (error) {
    setFeedback('error', `打开目录失败：${error.message || error}`)
  } finally {
    fsLoading.value = false
  }
}

function isSelected(path) {
  return selected.value.some(item => item.path === path)
}

function addSelected(entry) {
  if (isSelected(entry.path)) {
    return
  }
  selected.value.push({ name: entry.name, path: entry.path, type: entry.type })
}

function toggleSelected(entry) {
  if (isSelected(entry.path)) {
    removeSelected(entry.path)
  } else {
    addSelected(entry)
  }
}

function onEntryClick(entry) {
  if (entry.type === 'dir') {
    browseLocal(entry.path)
  } else {
    toggleSelected(entry)
  }
}

function removeSelected(path) {
  selected.value = selected.value.filter(item => item.path !== path)
}

function clearSelected() {
  selected.value = []
}

async function startUpload() {
  if (!selected.value.length) {
    return
  }
  uploading.value = true
  setFeedback('info', '正在上传，请稍候...')
  try {
    const result = await request('/upload', {
      method: 'POST',
      body: JSON.stringify({
        paths: selected.value.map(item => item.path),
        remote_dir: uploadRemoteDir.value || props.defaultRemoteDir || '/',
      }),
    })
    if (!result.success) {
      setFeedback('error', result.message || '上传失败')
    } else {
      setFeedback('success', result.message || '上传完成')
      clearSelected()
    }
  } catch (error) {
    setFeedback('error', `上传失败：${error.message || error}`)
  } finally {
    uploading.value = false
  }
}

watch(() => props.defaultRemoteDir, (value) => {
  if (!remoteDirTouched.value && value) {
    uploadRemoteDir.value = value
  }
})

watch(() => props.defaultSourceDir, (value) => {
  if (!localPath.value && value) {
    browseLocal(value)
  }
})

onMounted(() => {
  browseLocal(props.defaultSourceDir || '/')
})
</script>

<style scoped>
.mu-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mu-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mu-card__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.mu-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  gap: 16px;
}

.mu-browser {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.mu-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mu-list {
  height: 260px;
  overflow-y: auto;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.02);
  padding: 4px;
}

.mu-empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.mu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  transition: background 0.15s ease;
}

.mu-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.06);
}

.mu-item--selected {
  background: rgba(34, 197, 94, 0.1);
}

.mu-item__main {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
  cursor: pointer;
}

.mu-item__name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mu-item__meta {
  margin-left: auto;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  flex-shrink: 0;
}

.mu-side {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.mu-selected {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 64px;
  max-height: 160px;
  overflow-y: auto;
  padding: 8px;
  border: 0.5px dashed rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 12px;
}

.mu-selected__empty {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.mu-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mu-hint {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  line-height: 1.5;
}

.mu-input :deep(.v-field) {
  border-radius: 12px;
  background: rgba(var(--v-theme-surface, 255, 255, 255), 0.72);
}

@media (max-width: 960px) {
  .mu-grid {
    grid-template-columns: 1fr;
  }
}
</style>
