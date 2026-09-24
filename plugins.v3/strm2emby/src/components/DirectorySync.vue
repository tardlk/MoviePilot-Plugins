<template>
  <div class="ds-card">
    <div class="ds-card__header">
      <span class="ds-card__title">
        <v-icon icon="mdi-folder-sync-outline" size="18" color="#10b981" class="mr-1" />
        目录同步
      </span>
      <v-chip :color="form.sync_enabled ? 'success' : 'grey'" size="x-small" variant="tonal">
        {{ form.sync_enabled ? '已启用' : '未启用' }}
      </v-chip>
    </div>

    <div class="ds-grid">
      <div class="ds-item">
        <v-switch v-model="form.sync_enabled" label="启用目录同步" density="compact" hide-details color="primary" />
        <div class="ds-hint">把本地目录上传到光鸭云盘（独立于整理链）</div>
      </div>
      <div class="ds-item">
        <v-switch v-model="form.sync_watch" label="目录监控（实时）" density="compact" hide-details color="primary" />
        <div class="ds-hint">基于 watchfiles 实时上传，可不填 Cron</div>
      </div>
      <div class="ds-item">
        <v-text-field v-model="form.sync_source_dir" label="本地源目录" placeholder="/vol2/1000/Vol2/Media" density="compact" variant="outlined" hide-details class="ds-input" />
      </div>
      <div class="ds-item">
        <v-text-field v-model="form.sync_remote_dir" label="光鸭目标目录" placeholder="/Media" density="compact" variant="outlined" hide-details class="ds-input" />
      </div>
      <div class="ds-item">
        <v-text-field v-model="form.sync_cron" label="同步周期（Cron）" placeholder="0 3 * * *" density="compact" variant="outlined" hide-details class="ds-input" />
      </div>
      <div class="ds-item">
        <v-select v-model="form.sync_conflict" :items="conflictOptions" item-title="title" item-value="value" label="同名文件处理" density="compact" variant="outlined" hide-details class="ds-input" />
      </div>
      <div class="ds-item">
        <v-text-field v-model="form.sync_extensions" label="仅同步扩展名（可选）" placeholder=".mkv,.mp4,.srt" density="compact" variant="outlined" hide-details class="ds-input" />
      </div>
      <div class="ds-item">
        <v-switch v-model="form.sync_delete_source" label="上传成功后删除本地" density="compact" hide-details color="error" />
        <div class="ds-hint">谨慎开启，删除不可恢复</div>
      </div>
    </div>

    <div class="ds-actions">
      <v-btn color="primary" :loading="saving" @click="save">保存同步设置</v-btn>
      <v-btn variant="tonal" prepend-icon="mdi-sync" :loading="syncing" :disabled="!loggedIn" @click="runNow">立即同步</v-btn>
      <span v-if="!loggedIn" class="ds-hint">未登录光鸭云盘，无法同步</span>
    </div>

    <v-alert v-if="feedback.text" :type="feedback.type || 'info'" variant="tonal" density="compact">
      {{ feedback.text }}
    </v-alert>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  loggedIn: { type: Boolean, default: false },
  // 父组件传入的完整插件配置（含 sync_* 字段）
  config: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update'])

const conflictOptions = [
  { title: '跳过（保留云端）', value: 'skip' },
  { title: '覆盖（删除云端后上传）', value: 'overwrite' },
  { title: '保留两者（自动重命名）', value: 'rename' },
]

const form = reactive({
  sync_enabled: false,
  sync_watch: false,
  sync_source_dir: '',
  sync_remote_dir: '/',
  sync_cron: '',
  sync_conflict: 'skip',
  sync_delete_source: false,
  sync_extensions: '',
})
const saving = ref(false)
const syncing = ref(false)
const feedback = ref({ type: '', text: '' })

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

function applyConfig(config = {}) {
  form.sync_enabled = Boolean(config.sync_enabled)
  form.sync_watch = Boolean(config.sync_watch)
  form.sync_source_dir = config.sync_source_dir || ''
  form.sync_remote_dir = config.sync_remote_dir || '/'
  form.sync_cron = config.sync_cron || ''
  form.sync_conflict = config.sync_conflict || (config.sync_overwrite ? 'overwrite' : 'skip')
  form.sync_delete_source = Boolean(config.sync_delete_source)
  form.sync_extensions = config.sync_extensions || ''
}

watch(() => props.config, (value) => applyConfig(value), { immediate: true, deep: true })

async function save() {
  saving.value = true
  feedback.value = { type: '', text: '' }
  try {
    const result = await request('/config', {
      method: 'POST',
      body: JSON.stringify({
        sync_enabled: form.sync_enabled,
        sync_watch: form.sync_watch,
        sync_source_dir: form.sync_source_dir,
        sync_remote_dir: form.sync_remote_dir,
        sync_cron: form.sync_cron,
        sync_conflict: form.sync_conflict,
        sync_delete_source: form.sync_delete_source,
        sync_extensions: form.sync_extensions,
      }),
    })
    if (!result.success) {
      feedback.value = { type: 'error', text: result.message || '保存失败' }
      return
    }
    if (result.data) {
      applyConfig(result.data)
      emit('update', result.data)
    }
    feedback.value = { type: 'success', text: result.message || '同步设置已保存' }
  } catch (error) {
    feedback.value = { type: 'error', text: `保存失败：${error.message || error}` }
  } finally {
    saving.value = false
  }
}

async function runNow() {
  syncing.value = true
  feedback.value = { type: 'info', text: '正在同步，请稍候...' }
  try {
    const result = await request('/sync')
    if (!result.success) {
      feedback.value = { type: 'error', text: result.message || '同步失败' }
    } else {
      feedback.value = { type: 'success', text: result.message || '同步任务已执行，请查看插件日志' }
    }
  } catch (error) {
    feedback.value = { type: 'error', text: `同步失败：${error.message || error}` }
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped>
.ds-card {
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

.ds-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.ds-card__title {
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.ds-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
}

.ds-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.ds-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.ds-hint {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  line-height: 1.5;
}

.ds-input :deep(.v-field) {
  border-radius: 12px;
  background: rgba(var(--v-theme-surface, 255, 255, 255), 0.72);
}

@media (max-width: 960px) {
  .ds-grid {
    grid-template-columns: 1fr;
  }
}
</style>
