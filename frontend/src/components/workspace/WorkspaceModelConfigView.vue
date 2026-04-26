<template>
  <div class="view-panel">
    <div class="container card settings-container">
      <div class="settings-header">
        <h1>
          <span class="settings-icon">🧩</span>
          模型配置
        </h1>
        <p class="lead">集中管理当前转换器的路径、模型状态与运行操作。</p>
      </div>

      <el-alert v-if="settingsLoadError" :title="settingsLoadError" type="error" :closable="false"
        style="margin-bottom: 16px" />

      <div v-if="isAdmin" class="admin-settings">
        <!-- <h3 class="settings-h3">转换器配置（保存至数据库）</h3> -->

        <div class="settings-save-bar settings-save-bar--top">
          <el-button type="primary" :loading="adminSaveLoading" @click="saveAdminSettings">保存到数据库</el-button>
          <!-- <span class="muted settings-save-bar-tip">所有分栏中的修改一次保存即可写入数据库</span> -->
        </div>

        <div class="admin-settings-form">
          <div class="model-config-overview">
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">当前模型：</span>
              <span class="model-config-overview__value">
                {{
                  adminForm.default_converter_id === 'paddle-ocr-v3.5'
                    ? 'PaddleOCR-3.5.0'
                    : 'Logics-Parsing-v2'
                }}
              </span>
            </div>
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">切换模型：</span>
              <el-select v-model="adminForm.default_converter_id" size="small" style="width: 220px">
                <el-option v-for="item in ((adminForm.available_converters && adminForm.available_converters.length
                  ? adminForm.available_converters
                  : [{ id: 'logics-parsing-v2', name: 'Logics-Parsing-v2', enabled: true }]))" :key="item.id"
                  :label="item.name || item.id" :value="item.id" />
              </el-select>
            </div>
            <div class="model-config-overview__item">
              <span class="model-config-overview__label">{{ isPaddle ? '服务状态：' : '模型状态：' }}</span>
              <el-tag :type="isPaddle ? 'info' : (modelStatus.model_loaded ? 'success' : 'warning')" size="small">
                {{
                  isPaddle
                    ? (String(converterConfigData?.runtime_mode || 'api').toLowerCase() === 'local' ? '本地模式' : 'API 模式')
                    : (modelStatus.model_loaded ? '已加载' : '未加载')
                }}
              </el-tag>
            </div>
            <div class="model-config-overview__item model-config-overview__item--wide">
              <span class="model-config-overview__label">{{ isPaddle ? '配置端点：' : '模型目录：' }}</span>
              <span class="model-config-overview__value model-config-overview__value--path">
                {{
                  isPaddle
                    ? (String(converterConfigData?.api_url || '').trim() || '（未配置 API URL）')
                    : (String(converterConfigData?.download?.dest_dir || '').trim() || '（未配置，使用默认路径）')
                }}
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
                    模型下载保存路径
                  </label>
                </div>
                <el-input :model-value="String(converterConfigData?.download?.dest_dir || '')"
                  placeholder="相对项目根目录，例如 weights/…" class="path-input" clearable
                  @update:model-value="(v) => updateConverterConfigDownloadField('dest_dir', v ?? '')" />
              </div>


            </el-card>

            <el-card class="config-card model-management-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">🧩</span>
                  <span class="card-title">模型配置</span>
                </div>
              </template>

              <div class="repo-config-grid">
                <div v-if="isPaddle" class="repo-item">
                  <label class="repo-label">
                    <span class="label-icon">🔁</span>
                    {{ fieldLabel('runtime_mode') }}
                  </label>
                  <el-select :model-value="String(converterConfigData?.runtime_mode || 'api')" size="small"
                    style="width: 220px" @update:model-value="(v) => updateConverterConfigField('runtime_mode', v)">
                    <el-option label="API 模式" value="api" />
                    <el-option label="本地模式" value="local" />
                  </el-select>
                  <span v-if="fieldHint('runtime_mode')" class="muted" style="font-size: 12px">{{
                    fieldHint('runtime_mode')
                    }}</span>
                </div>
                <div v-for="item in configEntries" :key="item.key" class="repo-item">
                  <template v-if="!(isPaddle && item.key === 'runtime_mode')">
                    <label class="repo-label">
                      <span class="label-icon">⚙️</span>
                      {{ fieldLabel(item.key) }}
                    </label>
                    <el-switch v-if="typeof item.value === 'boolean'" :model-value="item.value"
                      @update:model-value="(v) => updateConverterConfigField(item.key, v)" />
                    <el-input-number v-else-if="typeof item.value === 'number'" :model-value="item.value" :min="0"
                      :max="1000000" size="small"
                      @update:model-value="(v) => updateConverterConfigField(item.key, Number(v ?? 0))" />
                    <el-input v-else-if="typeof item.value === 'string'" :model-value="item.value"
                      :placeholder="fieldHint(item.key)" size="small" clearable
                      @update:model-value="(v) => updateConverterConfigField(item.key, v)" />
                    <el-input v-else :model-value="toJsonString(item.value)" type="textarea" :rows="4"
                      @change="(v) => updateObjectField(item.key, v)" />
                    <span v-if="fieldHint(item.key)" class="muted" style="font-size: 12px">{{ fieldHint(item.key)
                      }}</span>
                  </template>
                </div>
              </div>
              <div class="action-buttons action-buttons--config-save">
                <el-button type="success" size="large" :loading="converterConfigSaving" @click="saveConverterConfig"
                  class="save-config-btn">
                  💾 保存参数到配置文件
                </el-button>
                <el-tag v-if="converterConfigLoading" type="info" size="small">加载中...</el-tag>
              </div>
              <p class="model-actions-hint muted">修改模型参数后，请先点击“保存参数到配置文件”，再执行下载或重载。</p>
            </el-card>

            <el-card v-if="isLogics" class="config-card model-management-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">⚙️</span>
                  <span class="card-title">模型加载</span>
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

              <div class="download-source-section">
                <label class="section-label">
                  <span class="label-icon">📥</span>
                  下载源选择
                </label>
                <el-radio-group :model-value="dlSource" @update:model-value="$emit('update:dl-source', $event)"
                  :disabled="modelStatus.downloading" class="source-radio-group">
                  <el-radio-button v-for="source in availableSources" :key="source" :value="source">
                    {{ sourceLabel(source) }}
                  </el-radio-button>
                </el-radio-group>
              </div>

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
            <el-card v-else-if="isPaddle" class="config-card model-management-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span class="card-icon">⚙️</span>
                  <span class="card-title">模型下载与配置检查</span>
                </div>
              </template>
              <el-alert title="支持与其他转换器一致的下载入口；实际下载行为由当前转换器配置决定。" type="info" :closable="false"
                class="model-status-alert" />
              <div class="action-buttons">
                <el-radio-group :model-value="dlSource" @update:model-value="$emit('update:dl-source', $event)"
                  :disabled="modelStatus.downloading" class="source-radio-group">
                  <el-radio-button v-for="source in availableSources" :key="source" :value="source">
                    {{ sourceLabel(source) }}
                  </el-radio-button>
                </el-radio-group>
              </div>
              <div class="action-buttons">
                <el-button :loading="dlLoading || modelStatus.downloading" :disabled="modelStatus.downloading"
                  @click="runModelDownload" class="download-btn">
                  <span v-if="!modelStatus.downloading">📥 按配置下载模型文件</span>
                  <span v-else>⏳ 下载中...</span>
                </el-button>
                <el-button v-if="modelStatus.downloading" type="warning" @click="stopModelDownload">
                  ⛔ 停止下载
                </el-button>
                <el-button type="danger" plain :disabled="modelStatus.downloading || modelStatus.model_loaded"
                  @click="clearModelFiles">
                  🗑️ 删除模型文件
                </el-button>
                <el-button @click="checkPaddleConfig" class="reload-btn">
                  ✅ 检查 Paddle 配置
                </el-button>
              </div>
              <p class="model-actions-hint muted">
                建议流程：先保存参数配置，再执行下载；下载后可进行配置检查。
              </p>
              <p class="model-actions-hint muted">
                提示：删除模型后需要重新下载，可能耗时较长；模型已加载时禁止删除。
              </p>
              <el-alert v-if="hasDownloadStatus" :title="downloadStatusTitle" :type="downloadStatusType"
                :closable="false" class="model-status-alert">
                <template #default>
                  <div style="white-space: pre-wrap; line-height: 1.55;">
                    {{ modelStatus.download_message || modelStatus.download_error || '暂无状态信息' }}
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
import { computed } from 'vue'

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
  checkPaddleConfig: { type: Function, required: true },
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

const isLogics = computed(() => props.adminForm.default_converter_id === 'logics-parsing-v2')
const isPaddle = computed(() => props.adminForm.default_converter_id === 'paddle-ocr-v3.5')
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
    if (k.startsWith('_') || k === 'download') return false
    // 内置长命令，管理员界面不展示；仍随配置读写，本地模式由插件使用
    if (isPaddle.value && k === 'local_command') return false
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
