<template>
  <section class="sa-card">
    <div class="sa-title"><v-icon icon="mdi-telegram" size="20" /> 分享转存并整理</div>
    <div class="sa-hint">发光鸭链接给 MoviePilot 的 Telegram Bot，自动转存，再按媒体库规则整理。每条链接独立排队。</div>
    <v-switch v-model="form.telegram_enabled" label="接收 Telegram 分享" color="primary" density="compact" hide-details />
    <v-text-field v-model="form.telegram_user_ids" label="允许的 Telegram 用户 ID" placeholder="123456789, 987654321"
      hint="数字 ID，逗号分隔。还需在 MoviePilot「通知渠道」配置 Telegram Bot 与交互权限。" persistent-hint density="compact" variant="outlined" />
    <div class="sa-grid">
      <RemoteDirPicker v-model="form.share_source_dir" :api="api" :plugin-id="pluginId" :source-plugin-id="sourcePluginId"
        label="转存源目录（光鸭）" hint="每次转存到此目录下的独立任务子目录。" />
      <RemoteDirPicker v-model="form.share_target_dir" :api="api" :plugin-id="pluginId" :source-plugin-id="sourcePluginId"
        label="媒体库目录（光鸭）" hint="须与源目录相互独立。新目录可手动填写。" />
    </div>
    <v-select v-model="form.share_transfer_type" :items="[{ title: '移动', value: 'move' }, { title: '复制', value: 'copy' }]"
      label="整理方式" density="compact" variant="outlined" hide-details />
    <div class="sa-actions">
      <v-checkbox v-model="form.share_type_folder" label="按电影 / 电视剧分目录" density="compact" hide-details />
      <v-checkbox v-model="form.share_category_folder" label="按媒体类别分目录" density="compact" hide-details />
      <v-checkbox v-model="form.share_scrape" label="刮削元数据" density="compact" hide-details />
    </div>
    <div class="sa-actions"><v-btn color="primary" variant="tonal" :loading="saving" @click="save">保存分享设置</v-btn></div>
    <div class="sa-hint">私聊发送一条纯链接即可；开启全局 AI 或粘贴整段分享文案时，使用 /guangya 链接 提取码：1234。重复分享会返回已有任务。</div>
    <v-divider />
    <v-textarea v-model="text" label="手动提交分享（使用已保存的目录设置）" rows="2" auto-grow density="compact" variant="outlined" hide-details />
    <div class="sa-actions">
      <v-btn color="primary" :disabled="!text.trim()" :loading="submitting" @click="submit">转存并整理</v-btn>
      <v-btn variant="text" :loading="refreshing" @click="load">刷新任务</v-btn>
    </div>
    <v-alert v-if="feedback.text" :type="feedback.type" variant="tonal" density="compact">{{ feedback.text }}</v-alert>
    <div v-if="jobs.length" class="sa-jobs">
      <v-table density="compact"><thead><tr><th>任务</th><th>状态</th><th>资源 / 源目录</th><th>结果</th></tr></thead>
        <tbody><tr v-for="job in jobs" :key="job.id">
          <td>{{ job.id }}<div class="sa-hint">{{ new Date(job.created_at * 1000).toLocaleString() }}</div></td>
          <td>{{ labels[job.state] || job.state }}</td>
          <td>{{ job.title || '待读取' }}<div class="sa-hint">{{ job.staging_dir }}</div></td><td>{{ job.message }}</td>
        </tr></tbody>
      </v-table>
    </div>
    <div v-else class="sa-hint">暂无分享任务。</div>
    <div class="sa-hint">任务中断或转存结果不明时会暂停，请检查光鸭目录和 MoviePilot 整理队列。自动处理只扫描本次任务目录；未识别的文件会保留，供手动处理。</div>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import RemoteDirPicker from './RemoteDirPicker.vue'
const props = defineProps({ api: { type: Object, default: () => ({}) }, pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' }, config: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update'])
const defaults = { telegram_enabled: false, telegram_user_ids: '', share_source_dir: '/待整理', share_target_dir: '/Media',
  share_transfer_type: 'move', share_scrape: false, share_type_folder: true, share_category_folder: false }
const form = reactive({ ...defaults })
watch(() => props.config, (config) => { for (const key of Object.keys(defaults)) form[key] = config[key] ?? defaults[key] }, { immediate: true })
const saving = ref(false), submitting = ref(false), refreshing = ref(false), text = ref(''), jobs = ref([])
const feedback = ref({ type: 'info', text: '' })
const prefix = computed(() => `plugin/${props.pluginId || props.sourcePluginId || 'guangyasync'}`)
const labels = { queued: '已排队', inspecting: '读取分享', saving: '转存中', confirming: '核对转存', saved: '转存完成',
  organizing: '整理中', completed: '已完成', partial: '请检查整理队列', failed: '失败', needs_review: '待人工核对' }
let timer
async function request(path, payload) {
  if (payload !== undefined) {
    if (!props.api?.post) throw new Error('宿主 API 尚未就绪，请重新打开页面')
    return props.api.post(`${prefix.value}/${path}`, payload, { feedback: 'silent' })
  }
  if (!props.api?.get) throw new Error('宿主 API 尚未就绪，请重新打开页面')
  return props.api.get(`${prefix.value}/${path}`, { feedback: 'silent' })
}
async function save() {
  saving.value = true
  try {
    const result = await request('config', { ...form })
    feedback.value = { type: result.success ? 'success' : 'error', text: result.message || '保存失败' }
    if (result.success) emit('update', result.data)
  } catch (error) { feedback.value = { type: 'error', text: error.message || '保存失败' } }
  finally { saving.value = false }
}
async function submit() {
  submitting.value = true
  try {
    const result = await request('share/submit', { text: text.value })
    feedback.value = { type: result.success ? 'success' : 'error', text: `${result.message || '提交失败'} ${result.data?.id || ''}` }
    if (result.success) text.value = ''
    await load()
  } catch (error) { feedback.value = { type: 'error', text: `${error.message || '提交结果未确认'}，请先刷新任务，避免重复提交。` } }
  finally { submitting.value = false }
}
async function load() {
  if (refreshing.value) return
  refreshing.value = true
  try { const result = await request('share/jobs'); if (result.success) jobs.value = result.data?.items || [] }
  catch (error) { feedback.value = { type: 'error', text: error.message || '读取任务失败' } }
  finally { refreshing.value = false }
}
onMounted(() => { load(); timer = setInterval(() => { if (!document.hidden) load() }, 5000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.sa-card { display: flex; flex-direction: column; gap: 14px; padding: 20px; border: 1px solid rgba(var(--v-theme-on-surface), .12); border-radius: 14px; }
.sa-title { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
.sa-hint { font-size: 12px; color: rgba(var(--v-theme-on-surface), .6); line-height: 1.7; overflow-wrap: anywhere; }
.sa-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.sa-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.sa-jobs { max-height: 420px; overflow: auto; }
.sa-jobs td { min-width: 100px; max-width: 360px; overflow-wrap: anywhere; }
@media(max-width: 640px) { .sa-grid { grid-template-columns: 1fr; } .sa-card { padding: 16px; } }
</style>
