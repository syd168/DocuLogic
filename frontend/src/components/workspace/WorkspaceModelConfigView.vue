<template>
  <div class="view-panel">
    <div class="container card settings-container">
      <div class="settings-header">
        <h1>
          <span class="settings-icon">🧩</span>
          解析器配置
        </h1>
        <p class="lead">集中管理当前文档解析器的路径、解析器状态与运行操作。</p>
      </div>

      <el-alert v-if="settingsLoadError" :title="settingsLoadError" type="error" :closable="false"
        style="margin-bottom: 16px" />

      <div v-if="isAdmin" class="admin-settings">
        <!-- <h3 class="settings-h3">文档解析器配置（保存至数据库）</h3> -->

        <div class="settings-save-bar settings-save-bar--top">
          <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
          <!-- <span class="muted settings-save-bar-tip">所有分栏中的修改一次保存即可写入数据库</span> -->
        </div>

        <div class="admin-settings-form">
          <div class="model-config-overview">
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">当前解析器：</span>
              <span class="model-config-overview__value">
                {{
                  (() => {
                    const id = adminForm.default_converter_id
                    const converter = (adminForm.available_converters || []).find(c => c.id === id)
                    return converter ? (converter.name || converter.id) : (id || '未选择')
                  })()
                }}
              </span>
            </div>
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">切换解析器：</span>
              <el-select v-model="adminForm.default_converter_id" size="small" style="width: 220px"
                :disabled="modelStatus.downloading || dlLoading"
                :placeholder="(adminForm.available_converters && adminForm.available_converters.length) ? '请选择解析器' : '暂无可用解析器'">
                <el-option v-for="item in (adminForm.available_converters || [])" :key="item.id"
                  :label="item.name || item.id" :value="item.id" />
              </el-select>
            </div>
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">{{ currentConverterMeta?.status_label || '解析器状态：' }}</span>
              <el-tag :type="getCurrentStatusType()" size="small">
                {{ getCurrentStatusText() }}
              </el-tag>
            </div>
            <div class="model-config-overview__item model-config-overview__item--wide">
              <span class="model-config-overview__label">{{ currentConverterMeta?.path_label || '解析器目录：' }}</span>
              <span class="model-config-overview__value model-config-overview__value--path">
                {{ getCurrentPathDisplay() }}
              </span>
            </div>
          </div>

          <div class="path-model-container">
            <el-card class="config-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">📁</span>
                  <span class="card-title">路径配置</span>
                </div>
              </template>

              <div class="config-item">
                <div class="item-header">
                  <label class="item-label">
                    <span class="label-icon">📤</span>
                    解析结果输出路径
                  </label>
                </div>
                <el-input v-model="adminForm.output_dir" :placeholder="outputDirPlaceholder" class="path-input"
                  clearable />
              </div>

              <el-divider />

              <div class="config-item">
                <div class="item-header">
                  <label class="item-label">
                    <span class="label-icon">📦</span>
                    {{ currentConverterMeta?.model_path_label || '解析器的模型下载保存路径' }}
                  </label>
                </div>
                <el-input :model-value="getCurrentModelPathValue()"
                  :placeholder="currentConverterMeta?.model_path_placeholder || '相对项目根目录，例如 weights/…'" 
                  class="path-input" clearable
                  @update:model-value="(v) => updateCurrentModelPath(v ?? '')" />
              </div>
            </el-card>

            <el-card class="config-card model-management-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">🧩</span>
                  <span class="card-title">解析器参数配置</span>
                </div>
              </template>

              <!-- 使用动态表单组件 -->
              <DynamicConfigForm 
                v-if="configSchema && converterConfigData"
                :schema="configSchema"
                :model-value="converterConfigData"
                @update:model-value="(val) => Object.assign(converterConfigData, val)"
              />

              <div class="action-buttons action-buttons--config-save">
                <el-button type="success" size="large" :loading="converterConfigSaving" @click="saveConverterConfig"
                  class="save-config-btn">
                  💾 保存参数到配置文件
                </el-button>
                <el-tag v-if="converterConfigLoading" type="info" size="small">加载中...</el-tag>
              </div>
              <p class="model-actions-hint muted">修改模型参数后，请先点击“保存参数到配置文件”，再执行下载或重载。</p>
            </el-card>

            <!-- 通用模型管理卡片（适用于所有支持动态 Schema 的解析器） -->
            <el-card v-if="configSchema" class="config-card model-management-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">⚙️</span>
                  <span class="card-title">模型下载与生命周期管理</span>
                </div>
              </template>

              <el-alert v-if="modelStatus.model_loaded" title="✅ 模型已加载" type="success" :closable="false"
                class="model-status-alert">
                <template #default>
                  <span>模型已就绪，可以开始解析文档</span>
                </template>
              </el-alert>
              <el-alert v-else-if="!modelStatus.downloading && !modelStatus.download_message" title="⚠️ 模型未加载"
                type="warning" :closable="false" class="model-status-alert">
                <template #default>
                  <span>请下载模型后点击「重新加载模型」</span>
                </template>
              </el-alert>

              <div class="action-buttons">
                <el-button :loading="dlLoading || modelStatus.downloading" :disabled="modelStatus.downloading"
                  @click="runModelDownload" class="download-btn">
                  <span v-if="!modelStatus.downloading">📥 后台下载模型</span>
                  <span v-else>⏳ 下载中...</span>
                </el-button>
                <el-button v-if="modelStatus.downloading" type="warning" @click="stopModelDownload">
                  ⛔ 停止下载
                </el-button>
                <el-button type="danger" plain :disabled="modelStatus.downloading || modelStatus.model_loaded"
                  @click="clearModelFiles">
                  🗑️ 删除模型文件
                </el-button>

                <el-button :loading="reloadLoading" :disabled="modelStatus.downloading" @click="reloadModel"
                  class="reload-btn">
                  🔄 重新加载模型
                </el-button>
                <el-button v-if="modelStatus.model_loaded" :loading="unloadLoading" :disabled="modelStatus.downloading"
                  @click="unloadModel" class="unload-btn" type="danger">
                  🗑️ 卸载模型
                </el-button>
              </div>
              <p class="model-actions-hint muted" style="margin-top: 10px; margin-bottom: 10px;">
                建议流程：先下载模型，再执行重载；仅在确认无任务时执行卸载。</p>
              <el-alert v-if="hasDownloadStatus" :type="downloadStatusType" :closable="false"
                class="model-status-alert">
                <template #default>
                  <div style="white-space: pre-wrap; line-height: 1.55;">状态：{{ modelStatus.download_message ||
                    modelStatus.download_error || '暂无状态信息' }}
                    <template
                      v-if="modelStatus.download_source || modelStatus.download_repo || modelStatus.download_dest">
                      <br>
                      <span v-if="modelStatus.download_source">来源：{{ modelStatus.download_source }}</span>
                      <span v-if="modelStatus.download_repo"><br>仓库：{{ modelStatus.download_repo }}</span>
                      <span v-if="modelStatus.download_dest"><br>目标：{{ modelStatus.download_dest }}</span>
                    </template>
                  </div>
                </template>
              </el-alert>
              <span v-if="reloadError" class="reload-error-text">{{ reloadError }}</span>
            </el-card>
          </div>

          <div class="settings-save-bar settings-save-bar--bottom">
            <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
            <!-- <span class="muted settings-save-bar-tip">与顶部按钮相同，保存全部配置</span> -->
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import http from '@/api/http'
import DynamicConfigForm from '@/components/DynamicConfigForm.vue'

const props = defineProps({
  isAdmin: { type: Boolean, required: true },
  settingsLoadError: { type: String, default: '' },
  adminSaveLoading: { type: Boolean, required: true },
  saveAdminSettings: { type: Function, required: true },
  adminForm: { type: Object, required: true },
  modelStatus: { type: Object, required: true },
  dlSource: { type: String, required: true },
  dlLoading: { type: Boolean, required: true },
  reloadLoading: { type: Boolean, required: true },
  unloadLoading: { type: Boolean, required: true },
  reloadError: { type: String, default: '' },
  runModelDownload: { type: Function, required: true },
  stopModelDownload: { type: Function, required: true },
  clearModelFiles: { type: Function, required: true },
  reloadModel: { type: Function, required: true },
  unloadModel: { type: Function, required: true },
  checkConverterConfig: { type: Function, required: true },
  converterConfigData: { type: Object, required: true },
  converterConfigLoading: { type: Boolean, required: true },
  converterConfigSaving: { type: Boolean, required: true },
  downloadSchema: { type: Object, default: () => ({}) },
  effectivePaths: { type: Object, default: () => ({}) },
  saveConverterConfig: { type: Function, required: true },
  updateConverterConfigField: { type: Function, required: true },
  updateConverterConfigDownloadField: { type: Function, required: true },
})

defineEmits(['update:dl-source'])

// 动态 Schema 相关状态
const configSchema = ref(null)

// 获取配置 Schema
const fetchConfigSchema = async () => {
  try {
    const engineId = props.adminForm.default_converter_id
    // 📌 防御性检查：避免 engineId 为空时发起无效请求
    if (!engineId || !String(engineId).trim()) {
      console.debug('[ConfigSchema] 跳过请求：转换器 ID 为空')
      configSchema.value = null
      return
    }
    
    // 使用封装的 http 实例，并带上 /api 前缀
    const res = await http.get(`/api/admin/converter/${encodeURIComponent(engineId)}/config-schema`)
    if (res.data && res.data.ok) {
      configSchema.value = res.data.schema
    }
  } catch (e) {
    console.error('Failed to fetch config schema:', e)
    configSchema.value = null
  }
}

// 监听解析器切换，重新加载 Schema
watch(() => props.adminForm.default_converter_id, () => {
  fetchConfigSchema()
})

onMounted(() => {
  fetchConfigSchema()
})

// 获取当前选中的转换器元数据
const currentConverterMeta = computed(() => {
  const engineId = props.adminForm.default_converter_id
  const converter = (props.adminForm.available_converters || []).find(c => c.id === engineId)
  return converter?.meta || {}
})

// 动态获取状态类型
const getCurrentStatusType = () => {
  const meta = currentConverterMeta.value
  if (meta.status_type === 'info') return 'info'
  if (meta.status_type === 'success') return 'success'
  if (meta.status_type === 'warning') return 'warning'
  // 默认逻辑：如果有 runtime_mode 字段，显示 info，否则根据 model_loaded 判断
  if (props.converterConfigData?.runtime_mode !== undefined) return 'info'
  return props.modelStatus.model_loaded ? 'success' : 'warning'
}

// 动态获取状态文本
const getCurrentStatusText = () => {
  const meta = currentConverterMeta.value
  // 如果转换器提供了自定义状态文本函数
  if (meta.get_status_text && typeof meta.get_status_text === 'function') {
    return meta.get_status_text(props.modelStatus, props.converterConfigData)
  }
  
  // 默认逻辑：检查是否有 runtime_mode（某些转换器支持 API/本地模式切换）
  if (props.converterConfigData?.runtime_mode !== undefined) {
    const mode = String(props.converterConfigData.runtime_mode).toLowerCase()
    return mode === 'local' ? '本地模式' : 'API 模式'
  }
  
  // 标准模型加载状态
  return props.modelStatus.model_loaded ? '已加载' : '未加载'
}

// 动态获取路径显示
const getCurrentPathDisplay = () => {
  const meta = currentConverterMeta.value
  // 如果转换器提供了自定义路径获取函数
  if (meta.get_path_display && typeof meta.get_path_display === 'function') {
    return meta.get_path_display(props.converterConfigData)
  }
  
  // 默认逻辑：优先显示 download.dest_dir，其次显示 api_url
  const destDir = String(props.converterConfigData?.download?.dest_dir || '').trim()
  const apiUrl = String(props.converterConfigData?.api_url || '').trim()
  
  if (destDir) return destDir
  if (apiUrl) return apiUrl
  return '（未配置，使用默认路径）'
}

// 动态获取模型路径输入框的值
const getCurrentModelPathValue = () => {
  const meta = currentConverterMeta.value
  if (meta.get_model_path_value && typeof meta.get_model_path_value === 'function') {
    return meta.get_model_path_value(props.converterConfigData)
  }
  return String(props.converterConfigData?.download?.dest_dir || '')
}

// 动态更新模型路径
const updateCurrentModelPath = (value) => {
  const meta = currentConverterMeta.value
  if (meta.update_model_path && typeof meta.update_model_path === 'function') {
    meta.update_model_path(value, props.converterConfigData, props.updateConverterConfigDownloadField)
  } else {
    // 默认更新 download.dest_dir
    props.updateConverterConfigDownloadField('dest_dir', value)
  }
}

// 过滤配置项时排除特定转换器的内部字段
const shouldExcludeConfigKey = (key) => {
  const meta = currentConverterMeta.value
  // 如果转换器定义了需要排除的字段列表
  if (meta.excluded_config_keys && Array.isArray(meta.excluded_config_keys)) {
    return meta.excluded_config_keys.includes(key)
  }
  // 默认排除以下划线开头的字段和 download 字段
  return key.startsWith('_') || key === 'download'
}

const availableSources = computed(() => {
  const arr = props.downloadSchema?.allowed_sources
  if (Array.isArray(arr) && arr.length) return arr
  return ['modelscope', 'huggingface']
})
const hasDownloadStatus = computed(
  () => !!(props.modelStatus?.download_message || props.modelStatus?.download_error)
)
const outputDirPlaceholder = computed(() => {
  const p = String(props.effectivePaths?.output || '').trim()
  return p ? `留空使用默认路径：${p}` : '留空使用默认路径'
})
const downloadStatusType = computed(() => {
  if (props.modelStatus?.download_error) return 'error'
  if (props.modelStatus?.downloading) return 'info'
  if (props.modelStatus?.download_success) return 'success'
  return 'info'
})
const downloadStatusTitle = computed(() => {
  if (props.modelStatus?.downloading) return '下载中'
  if (props.modelStatus?.download_error) return '下载失败'
  if (props.modelStatus?.download_success) return '下载完成'
  return '下载状态'
})
const uiMeta = computed(() => {
  const ui = props.converterConfigData?._ui
  return ui && typeof ui === 'object' ? ui : {}
})
const configEntries = computed(() => {
  const data = props.converterConfigData || {}
  const keys = Object.keys(data).filter((k) => {
    // 使用动态过滤函数，支持不同转换器的自定义排除规则
    if (shouldExcludeConfigKey(k)) return false
    return true
  })
  const order = Array.isArray(uiMeta.value?.order) ? uiMeta.value.order : []
  const ordered = [
    ...order.filter((k) => keys.includes(k)),
    ...keys.filter((k) => !order.includes(k)),
  ]
  return ordered.map((key) => ({ key, value: data[key] }))
})

function fieldLabel(key) {
  const labels = uiMeta.value?.labels
  if (labels && typeof labels === 'object' && typeof labels[key] === 'string' && labels[key]) {
    return labels[key]
  }
  return key
}

function fieldHint(key) {
  const hints = uiMeta.value?.hints
  if (hints && typeof hints === 'object' && typeof hints[key] === 'string') {
    return hints[key]
  }
  return ''
}

function toJsonString(value) {
  try {
    return JSON.stringify(value ?? {}, null, 2)
  } catch {
    return '{}'
  }
}

function updateObjectField(key, raw) {
  try {
    const parsed = JSON.parse(String(raw || '{}'))
    props.updateConverterConfigField(key, parsed)
  } catch {
    // 保持现值，避免错误 JSON 覆盖
  }
}

function sourceLabel(source) {
  return source === 'modelscope' ? '🇨🇳 ModelScope' : source === 'huggingface' ? '🌐 HuggingFace' : source
}
</script>
