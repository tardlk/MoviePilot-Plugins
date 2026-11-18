<template>
  <section class="co-card">
    <div class="co-header">
      <div>
        <div class="co-title"><v-icon icon="mdi-folder-sync-outline" size="20" class="mr-1" />云盘资源整理</div>
        <div class="co-subtitle">选择转存资源所在目录，按 MoviePilot 的识别与命名规则整理到光鸭媒体库。</div>
      </div>
      <v-chip size="small" color="primary" variant="tonal">云盘内整理</v-chip>
    </div>
    <div class="co-grid">
      <RemoteDirPicker v-model="form.source_dir" :api="api" :plugin-id="pluginId"
        :source-plugin-id="sourcePluginId" label="待整理目录（光鸭云盘）" placeholder="/待整理"
        :disabled="busy" hint="请选择已经存在的转存目录，将递归整理其中的资源。" />
      <RemoteDirPicker v-model="form.target_dir" :api="api" :plugin-id="pluginId"
        :source-plugin-id="sourcePluginId" label="媒体库目标目录（光鸭云盘）" placeholder="/媒体库"
        :disabled="busy" hint="目标目录可手动填写；缺失目录会在实际整理时创建。" />
      <v-select v-model="form.transfer_type" label="整理方式" :items="transferTypes" :disabled="busy"
        item-title="title" item-value="value" density="compact" variant="outlined" hide-details />
      <v-select v-model="form.media_type" label="媒体类型" :items="mediaTypes" :disabled="busy"
        item-title="title" item-value="value" density="compact" variant="outlined" hide-details />
    </div>
    <div class="co-options">
      <v-checkbox v-model="form.library_type_folder" label="按电影 / 电视剧分目录" :disabled="busy" density="compact" hide-details />
      <v-checkbox v-model="form.library_category_folder" label="按媒体类别分目录" :disabled="busy" density="compact" hide-details />
      <v-checkbox v-model="form.scrape" label="刮削元数据" :disabled="busy" density="compact" hide-details />
    </div>
    <div class="co-hint">包含子目录。移动会将整理成功的文件移出待整理目录；复制会保留原资源。两个目录须相互独立。</div>
    <div class="co-actions">
      <v-btn variant="tonal" prepend-icon="mdi-eye-outline" :loading="action === 'preview'"
        :disabled="busy || !valid" @click="submit(true)">预览整理结果</v-btn>
      <v-btn color="primary" prepend-icon="mdi-folder-sync-outline" :loading="action === 'organize'"
        :disabled="busy || !valid" @click="submit(false)">开始整理</v-btn>
    </div>
    <v-alert v-if="feedback.text" :type="feedback.type" variant="tonal" density="compact">{{ feedback.text }}</v-alert>
    <div v-if="previewItems.length" class="co-preview">
      <div class="co-hint">识别预览，共 {{ previewItems.length }} 项。实际整理会重新核对文件与覆盖规则。</div>
      <v-table density="compact">
        <thead><tr><th>源文件</th><th>整理目标</th><th>结果</th></tr></thead>
        <tbody>
          <tr v-for="(item, index) in previewItems" :key="`${item.source}-${index}`">
            <td>{{ item.source }}</td><td>{{ item.target || '—' }}</td>
            <td><v-icon :icon="item.success ? 'mdi-check-circle-outline' : 'mdi-alert-circle-outline'"
              :color="item.success ? 'success' : 'warning'" size="16" class="mr-1" />{{ item.message || (item.success ? '可整理' : '未能识别或规划') }}</td>
          </tr>
        </tbody>
      </v-table>
    </div>
    <div class="co-hint">任务进度和结果请在 MoviePilot「整理队列」与「整理记录」中查看；识别失败的资源可在那里手动指定媒体后重试。</div>
  </section>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import RemoteDirPicker from './RemoteDirPicker.vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
})
const form = reactive({
  source_dir: '', target_dir: '', transfer_type: 'move', media_type: 'auto',
  library_type_folder: true, library_category_folder: false, scrape: false,
})
const action = ref('')
const busy = computed(() => Boolean(action.value))
const valid = computed(() => form.source_dir.trim() && form.target_dir.trim())
const feedback = ref({ type: 'info', text: '' })
const previewItems = ref([])
const transferTypes = [{ title: '移动', value: 'move' }, { title: '复制（保留原资源）', value: 'copy' }]
const mediaTypes = [{ title: '自动识别', value: 'auto' }, { title: '电影', value: 'movie' }, { title: '电视剧', value: 'tv' }]
const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'guangyasync')
watch(form, () => { previewItems.value = []; feedback.value.text = '' })

async function submit(preview) {
  if (busy.value || !valid.value) return
  action.value = preview ? 'preview' : 'organize'
  feedback.value = { type: 'info', text: preview ? '正在递归读取目录并识别媒体，请稍候…' : '正在识别资源并提交整理请求，请稍候…' }
  previewItems.value = []
  try {
    const path = `plugin/${currentPluginId.value}/organize`
    const payload = { ...form, preview }
    let result
    if (props.api?.post) {
      result = await props.api.post(path, payload, { feedback: 'silent', timeout: 0 })
    } else {
      const response = await fetch(`/api/v1/${path}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      })
      result = await response.json()
    }
    if (preview && Array.isArray(result?.data?.result?.items)) previewItems.value = result.data.result.items
    feedback.value = { type: result?.success ? 'success' : 'warning', text: result?.message || (result?.success ? '请求已完成' : '请求失败') }
  } catch (error) {
    feedback.value = { type: 'error', text: `整理请求未能确认：${error.message || error}。请先检查原生整理队列，避免重复提交。` }
  } finally {
    action.value = ''
  }
}
</script>

<style scoped>
.co-card { display: flex; flex-direction: column; gap: 16px; padding: 20px; border: 1px solid rgba(var(--v-theme-on-surface), 0.12); border-radius: 14px; }
.co-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.co-title { font-size: 15px; font-weight: 600; }
.co-subtitle, .co-hint { font-size: 12px; color: rgba(var(--v-theme-on-surface), 0.6); line-height: 1.7; }
.co-subtitle { margin-top: 4px; }
.co-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.co-options, .co-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.co-preview { max-height: 420px; overflow: auto; }
.co-preview td { min-width: 180px; overflow-wrap: anywhere; font-size: 12px; }
@media (max-width: 640px) { .co-grid { grid-template-columns: 1fr; } .co-card { padding: 16px; } }
</style>
