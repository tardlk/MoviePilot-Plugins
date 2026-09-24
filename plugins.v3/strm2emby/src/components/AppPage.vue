<template>
  <div class="ap-page">
    <div class="ap-header">
      <div class="ap-header__left">
        <div class="ap-header__icon">
          <v-icon icon="mdi-duck" size="26" />
        </div>
        <div class="ap-header__meta">
          <div class="ap-header__title">Strm2Emby</div>
          <div class="ap-header__sub">浏览 MoviePilot 主机文件并上传到光鸭云盘</div>
        </div>
      </div>
      <div class="ap-header__right">
        <v-chip :color="status.logged_in ? 'success' : 'warning'" variant="tonal" size="small">
          {{ status.logged_in ? '已登录' : '未登录' }}
        </v-chip>
        <v-chip v-if="status.logged_in && status.total_space" variant="tonal" size="small" color="primary">
          已用 {{ formatSize(status.used_space) }} / {{ formatSize(status.total_space) }}
        </v-chip>
        <v-btn color="primary" variant="tonal" size="small" prepend-icon="mdi-refresh" :loading="loading" @click="loadStatus">刷新</v-btn>
        <v-btn variant="tonal" size="small" prepend-icon="mdi-cog" @click="openPluginPage">插件页</v-btn>
      </div>
    </div>

    <v-alert v-if="!status.logged_in" type="warning" variant="tonal" class="ap-alert">
      未登录光鸭云盘。请先点击右上角「插件页」扫码登录，登录后即可在此上传与同步。
    </v-alert>

    <DirectorySync
      :api="api"
      :plugin-id="pluginId"
      :source-plugin-id="sourcePluginId"
      :logged-in="status.logged_in"
      :config="fullConfig"
      @update="onConfigUpdate"
    />

    <ManualUpload
      v-if="status.logged_in"
      :api="api"
      :plugin-id="pluginId"
      :source-plugin-id="sourcePluginId"
      :logged-in="status.logged_in"
      :default-source-dir="status.sync_source_dir"
      :default-remote-dir="status.sync_remote_dir"
    />

    <div v-else class="ap-empty">
      <v-icon icon="mdi-cloud-off-outline" size="48" color="grey" />
      <div class="ap-empty__text">登录后即可在「整理」菜单里直接把服务器文件上传到光鸭云盘。</div>
    </div>

    <UploadHistory
      :api="api"
      :plugin-id="pluginId"
      :source-plugin-id="sourcePluginId"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import DirectorySync from './DirectorySync.vue'
import ManualUpload from './ManualUpload.vue'
import UploadHistory from './UploadHistory.vue'

const props = defineProps({
  // 宿主注入的实例作用域 API 客户端
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: '' },
  sourcePluginId: { type: String, default: '' },
  navKey: { type: String, default: 'main' },
  // 侧栏全页宿主会注入，保留以免未声明属性告警
  nativeSubscribe: { type: Function, default: null },
})

const loading = ref(false)
const fullConfig = ref({})
const status = reactive({
  logged_in: false,
  total_space: 0,
  used_space: 0,
  sync_source_dir: '',
  sync_remote_dir: '/',
})

const currentPluginId = computed(() => props.pluginId || props.sourcePluginId || 'Strm2Emby')

async function loadStatus() {
  loading.value = true
  try {
    let data
    if (props.api?.get) {
      data = await props.api.get(`plugin/${currentPluginId.value}/config`, { feedback: 'silent' })
    } else {
      const response = await fetch(`/api/v1/plugin/${currentPluginId.value}/config`)
      data = await response.json()
    }
    fullConfig.value = data?.data || {}
    status.logged_in = Boolean(data?.data?.logged_in)
    status.total_space = Number(data?.data?.total_space || 0)
    status.used_space = Number(data?.data?.used_space || 0)
    status.sync_source_dir = data?.data?.sync_source_dir || ''
    status.sync_remote_dir = data?.data?.sync_remote_dir || '/'
  } catch (error) {
    console.error('获取光鸭云盘状态失败', error)
  } finally {
    loading.value = false
  }
}

function onConfigUpdate(data) {
  if (!data) {
    return
  }
  fullConfig.value = data
  status.sync_source_dir = data.sync_source_dir || ''
  status.sync_remote_dir = data.sync_remote_dir || '/'
}

function openPluginPage() {
  window.location.hash = '#/plugins'
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(loadStatus)
</script>

<style scoped>
.ap-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 20px;
  min-height: 100%;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.ap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.ap-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.ap-header__icon {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  background: rgba(245, 158, 11, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #f59e0b;
  flex-shrink: 0;
}

.ap-header__title {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.3px;
}

.ap-header__sub {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
}

.ap-header__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ap-alert {
  margin: 0;
}

.ap-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px 16px;
  border: 0.5px dashed rgba(var(--v-theme-on-surface), 0.2);
  border-radius: 14px;
}

.ap-empty__text {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  text-align: center;
}
</style>
