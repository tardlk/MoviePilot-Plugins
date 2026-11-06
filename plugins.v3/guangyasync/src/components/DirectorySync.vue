<template>
  <div class="ds-card">
    <div class="ds-card__header">
      <span class="ds-card__title">
        <v-icon icon="mdi-folder-move-outline" size="18" color="#10b981" class="mr-1" />
        整理联动上传
      </span>
      <v-chip :color="form.sync_on_transfer ? 'success' : 'grey'" size="x-small" variant="tonal">
        {{ form.sync_on_transfer ? '已启用' : '未启用' }}
      </v-chip>
    </div>

    <div class="ds-grid">
      <div class="ds-item">
        <v-switch v-model="form.sync_on_transfer" label="整理成功后自动上传" density="compact" hide-details color="primary" />
        <div class="ds-hint">订阅 MoviePilot「整理完成」事件，自动读取整理后的成品文件与媒体目录并上传；无需填写本地路径，不扫描目录、不参与整理过程。</div>
      </div>
      <div class="ds-item">
        <RemoteDirPicker
          v-model="form.sync_remote_dir"
          :api="api"
          :plugin-id="pluginId"
          :source-plugin-id="sourcePluginId"
        />
      </div>
      <div class="ds-item">
        <v-select v-model="form.sync_conflict" :items="conflictOptions" item-title="title" item-value="value" label="同名文件处理" density="compact" variant="outlined" hide-details class="ds-input" />
        <div class="ds-hint">云端已有同名文件时的处理方式，默认跳过</div>
      </div>
    </div>

    <div class="ds-actions">
      <v-btn color="primary" :loading="saving" @click="save">保存设置</v-btn>
      <span class="ds-hint">上传记录与逐文件进度见下方「上传记录」</span>
    </div>

    <v-alert v-if="feedback.text" :type="feedback.type || 'info'" variant="tonal" density="compact">
      {{ feedback.text }}
    </v-alert>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import RemoteDirPicker from './RemoteDirPicker.vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  // 父组件传入的完整插件配置
  config: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update'])

const conflictOptions = [
  { title: '跳过（保留云端）', value: 'skip' },
  { title: '覆盖（删除云端后上传）', value: 'overwrite' },
  { title: '保留两者（自动重命名）', value: 'rename' },
]

const form = reactive({
  sync_on_transfer: false,
  sync_remote_dir: '/',
  sync_conflict: 'skip',
})
const saving = ref(false)
const feedback = ref({ type: '', text: '' })

function currentPluginId() {
  return props.pluginId || props.sourcePluginId || 'guangyasync'
}

async function request(path, options = {}) {
  const apiPath = `plugin/${currentPluginId()}${path}`
  if (props.api?.post) {
    return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, { feedback: 'silent', ...options })
  }
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const response = await fetch(`/api/v1/${apiPath}`, { headers, ...options })
  return response.json()
}

function applyConfig(config = {}) {
  form.sync_on_transfer = Boolean(config.sync_on_transfer)
  form.sync_remote_dir = config.sync_remote_dir || '/'
  form.sync_conflict = config.sync_conflict || 'skip'
}

watch(() => props.config, (value) => applyConfig(value), { immediate: true, deep: true })

async function save() {
  saving.value = true
  feedback.value = { type: '', text: '' }
  try {
    const result = await request('/config', {
      method: 'POST',
      body: JSON.stringify({
        sync_on_transfer: form.sync_on_transfer,
        sync_remote_dir: form.sync_remote_dir,
        sync_conflict: form.sync_conflict,
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
    feedback.value = { type: 'success', text: result.message || '设置已保存' }
  } catch (error) {
    feedback.value = { type: 'error', text: `保存失败：${error.message || error}` }
  } finally {
    saving.value = false
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
