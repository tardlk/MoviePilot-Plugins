<template>
  <div class="uh-card">
    <div class="uh-card__header">
      <span class="uh-card__title">
        <v-icon icon="mdi-history" size="18" color="#6366f1" class="mr-1" />
        上传记录
      </span>
      <div class="uh-header-actions">
        <v-chip size="x-small" variant="tonal" color="primary">共 {{ history.length }} 条</v-chip>
        <v-btn size="x-small" variant="text" icon="mdi-refresh" :loading="loading" @click="loadHistory" />
        <v-btn size="x-small" variant="text" color="error" icon="mdi-delete-outline" :disabled="!history.length" @click="clearHistory" />
      </div>
    </div>

    <!-- 实时进度 -->
    <div v-if="showProgress" class="uh-progress">
      <div class="uh-progress__top">
        <v-chip size="x-small" variant="tonal" :color="progress.active ? 'info' : 'success'">
          {{ triggerLabel(progress.trigger) }}
        </v-chip>
        <span class="uh-progress__current">{{ progress.current || progress.message || '-' }}</span>
        <span class="uh-progress__percent">{{ progress.percent }}%</span>
      </div>
      <v-progress-linear
        :model-value="progress.percent"
        :color="progress.active ? 'primary' : 'success'"
        height="8"
        rounded
      />
      <div class="uh-progress__stats">
        成功 {{ progress.uploaded }} · 跳过 {{ progress.skipped }} · 失败 {{ progress.failed }} · 共 {{ progress.total }}
      </div>

      <!-- 每个文件一行：进行中/成功/跳过/失败 -->
      <div v-if="progressItems.length" class="uh-progress__items">
        <div v-for="(it, idx) in progressItems" :key="`${it.name}-${idx}`" class="uh-pitem">
          <v-icon :icon="itemIcon(it.status)" :color="itemColor(it.status)" size="15" />
          <span class="uh-pitem__name" :title="it.remote || it.local">{{ it.name }}</span>
          <span v-if="it.status === 'running'" class="uh-pitem__phase">{{ itemPhaseLabel(it.phase) }}</span>
          <span v-if="it.status === 'running'" class="uh-pitem__percent">{{ it.percent }}%</span>
          <template v-else>
            <span v-if="it.flash" class="uh-pitem__flash">秒传</span>
            <v-chip size="x-small" variant="tonal" :color="itemColor(it.status)">{{ itemStatusLabel(it.status) }}</v-chip>
          </template>
        </div>
      </div>
      <div v-if="progress.total > progressItems.length" class="uh-progress__more">
        仅显示最近 {{ progressItems.length }} / 共 {{ progress.total }} 个文件，完整结果见下方记录
      </div>
    </div>

    <div class="uh-legend">
      「秒传」表示云端已存在相同内容（按文件 MD5 命中），实际上传字节为 0，仅新增云端文件引用。
    </div>

    <!-- 过滤 -->
    <div class="uh-filters">
      <v-chip
        v-for="opt in filterOptions"
        :key="opt.value"
        size="x-small"
        variant="tonal"
        :color="filter === opt.value ? 'primary' : 'default'"
        @click="filter = opt.value"
      >
        {{ opt.title }}
      </v-chip>
    </div>

    <!-- 记录列表 -->
    <div class="uh-list">
      <div v-if="!filtered.length" class="uh-empty">暂无上传记录</div>
      <div v-for="(item, idx) in filtered" :key="`${item.time}-${idx}`" class="uh-item">
        <v-icon :icon="actionIcon(item.action)" :color="actionColor(item.action)" size="16" />
        <div class="uh-item__body">
          <div class="uh-item__name">{{ item.name }}</div>
          <div class="uh-item__meta">
            <span>{{ formatTime(item.time) }}</span>
            <span class="uh-sep">·</span>
            <span>{{ triggerLabel(item.trigger) }}</span>
            <span v-if="item.size" class="uh-sep">·</span>
            <span v-if="item.size">{{ formatSize(item.size) }}</span>
            <span class="uh-item__remote" :title="item.remote || item.local">{{ item.remote || item.local }}</span>
          </div>
          <div v-if="item.error" class="uh-item__error">{{ item.error }}</div>
        </div>
        <v-chip
          v-if="item.flash && item.action === 'uploaded'"
          size="x-small"
          variant="tonal"
          color="info"
          class="uh-item__flash"
        >
          秒传
        </v-chip>
        <v-chip size="x-small" variant="tonal" :color="actionColor(item.action)">{{ actionLabel(item.action) }}</v-chip>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
})

const history = ref([])
const loading = ref(false)
const filter = ref('all')
const progress = ref(emptyProgress())
const progressVisible = ref(false)
let pollTimer = null
let hideTimer = null
let wasActive = false

const filterOptions = [
  { title: '全部', value: 'all' },
  { title: '手动上传', value: 'manual' },
  { title: '目录同步', value: 'sync' },
  { title: '目录监控', value: 'watch' },
  { title: '整理联动', value: 'transfer' },
]

const filtered = computed(() => {
  if (filter.value === 'all') {
    return history.value
  }
  return history.value.filter(item => item.trigger === filter.value)
})

// 最新的文件排在最上面
const progressItems = computed(() => [...(progress.value.items || [])].reverse())

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

const showProgress = computed(() => progressVisible.value)

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
  const apiPath = `plugin/${currentPluginId()}${path}`
  if (options.method === 'POST' && props.api?.post) {
    return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  if (options.method !== 'POST' && props.api?.get) {
    return props.api.get(apiPath, { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const response = await fetch(`/api/v1/${apiPath}`, { headers, ...options })
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
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatTime(timestamp) {
  const value = Number(timestamp || 0)
  if (!value) return '-'
  const date = new Date(value * 1000)
  const pad = num => String(num).padStart(2, '0')
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

async function loadHistory() {
  loading.value = true
  try {
    const result = await request('/history?limit=200')
    const data = result.data || {}
    history.value = Array.isArray(data.items) ? data.items : []
  } catch (error) {
    console.error('获取上传记录失败', error)
  } finally {
    loading.value = false
  }
}

function scheduleHideProgress(delay = 6000) {
  if (hideTimer) {
    clearTimeout(hideTimer)
  }
  hideTimer = setTimeout(() => {
    progressVisible.value = false
    hideTimer = null
  }, delay)
}

async function loadProgress() {
  try {
    const result = await request('/progress')
    const data = result.data || {}
    progress.value = { ...emptyProgress(), ...data }
    if (progress.value.active) {
      // 运行中：持续显示
      if (hideTimer) {
        clearTimeout(hideTimer)
        hideTimer = null
      }
      progressVisible.value = true
    } else if (wasActive) {
      // 刚从运行转为完成：保留最终结果几秒后自动隐藏
      progressVisible.value = true
      scheduleHideProgress(6000)
      loadHistory()
    }
    wasActive = progress.value.active
  } catch (error) {
    progress.value = emptyProgress()
  }
}

function scheduleNext() {
  pollTimer = setTimeout(async () => {
    await loadProgress()
    scheduleNext()
  }, progress.value.active ? 1500 : 5000)
}

async function clearHistory() {
  try {
    const result = await request('/history/clear', { method: 'POST' })
    if (result.success) {
      history.value = []
    }
  } catch (error) {
    console.error('清空上传记录失败', error)
  }
}

onMounted(async () => {
  await Promise.all([loadHistory(), loadProgress()])
  scheduleNext()
})

onBeforeUnmount(() => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
})
</script>

<style scoped>
.uh-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.uh-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.uh-card__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.uh-header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.uh-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.03);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
}

.uh-progress__top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.uh-progress__current {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uh-progress__percent {
  font-size: 12px;
  font-weight: 600;
}

.uh-progress__stats {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.uh-progress__items {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-top: 4px;
}

.uh-pitem {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: 8px;
  font-size: 12px;
}

.uh-pitem:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.uh-pitem__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uh-pitem__phase {
  flex-shrink: 0;
  font-size: 11px;
  color: rgb(var(--v-theme-info));
}

.uh-pitem__percent {
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-variant-numeric: tabular-nums;
}

.uh-pitem__flash {
  flex-shrink: 0;
  font-size: 11px;
  color: rgb(var(--v-theme-info));
}

.uh-progress__more {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin-top: 2px;
}

.uh-legend {
  font-size: 11px;
  line-height: 1.5;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.uh-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.uh-item__flash {
  flex-shrink: 0;
  margin-right: 4px;
}

.uh-list {
  max-height: 340px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.uh-empty {
  padding: 24px 12px;
  text-align: center;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.uh-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 6px;
  border-radius: 8px;
}

.uh-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.uh-item__body {
  flex: 1;
  min-width: 0;
}

.uh-item__name {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uh-item__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin-top: 2px;
  min-width: 0;
}

.uh-item__remote {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-left: 4px;
}

.uh-item__error {
  font-size: 11px;
  color: #ef4444;
  margin-top: 2px;
}

.uh-sep {
  opacity: 0.5;
}
</style>
