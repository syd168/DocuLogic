<template>
  <div class="workspace-layout" :class="{ 'is-mobile': isMobile }">
    <div v-if="isMobile && mobileNavOpen" class="workspace-sider-backdrop" aria-hidden="true"
      @click="mobileNavOpen = false" />
    <aside class="workspace-sider" :class="{ 'is-open': !isMobile || mobileNavOpen }">
      <div class="sider-brand">
        <router-link class="brand" to="/app" @click="onSiderBrandClick"><span class="brand-mark">📄</span>
          DocuLogic</router-link>
        <button v-if="isMobile" type="button" class="sider-close-btn" aria-label="关闭菜单" @click="mobileNavOpen = false">
          ×
        </button>
      </div>
      <el-menu class="sider-menu" :default-active="activeMenu" background-color="transparent"
        text-color="var(--text-muted)" active-text-color="var(--accent)" @select="onMenuSelect">
        <el-menu-item index="parse">
          <span class="menu-icon">📄</span>
          <span>文档解析</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="settings">
          <span class="menu-icon">⚙️</span>
          <span>系统设置</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="model-config">
          <span class="menu-icon">🧩</span>
          <span>模型配置</span>
        </el-menu-item>
        <el-menu-item index="profile">
          <span class="menu-icon">👤</span>
          <span>个人中心</span>
        </el-menu-item>
        <el-menu-item index="records">
          <span class="menu-icon">📋</span>
          <span>生成记录</span>
        </el-menu-item>
        <el-menu-item index="cache">
          <span class="menu-icon">🗑️</span>
          <span>缓存清除</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="users">
          <span class="menu-icon">👥</span>
          <span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <div class="workspace-main">
      <header class="workspace-header">
        <div class="workspace-header-left">
          <button v-if="isMobile" type="button" class="nav-toggle" aria-label="打开菜单" :aria-expanded="mobileNavOpen"
            @click="mobileNavOpen = !mobileNavOpen">
            <span class="nav-toggle-bars" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </span>
          </button>
          <span class="workspace-header-title">{{ menuTitle }}</span>
        </div>
        <div class="workspace-header-actions">
          <router-link to="/" class="home-link" title="返回首页">
            <span class="home-icon">🏠</span>
            <span class="home-text">首页</span>
          </router-link>
          <span class="user-pill">已登录：<strong>{{ username }}</strong></span>
          <el-button class="btn-ghost" link type="info" @click="logout">退出</el-button>
        </div>
      </header>
      <div class="workspace-body">
        <!-- 文档解析 -->
        <WorkspaceParseView
          v-show="activeMenu === 'parse'"
          :admin-form="adminForm"
          :pdf-page-count-loading="pdfPageCountLoading"
          :drag-over="dragOver"
          :on-drop="onDrop"
          :on-file-pick="onFilePick"
          :file-label="fileLabel"
          :parse-queue="parseQueue"
          :parsing="parsing"
          :clear-parse-queue="clearParseQueue"
          :is-pdf-file-name="isPdfFileName"
          :remove-queue-item="removeQueueItem"
          :has-queue="hasQueue"
          :prompt="prompt"
          :set-parse-prompt-example="setParsePromptExample"
          :pdf-pages-requested="pdfPagesRequested"
          :pdf-pages-slider-max="pdfPagesSliderMax"
          :clamp-pdf-pages-requested="clampPdfPagesRequested"
          :queue-total-pages="queueTotalPages"
          :format-pdf-pages-tooltip="formatPdfPagesTooltip"
          :pdf-pages-max="pdfPagesMax"
          :start-parse="startParse"
          :show-stop="showStop"
          :current-job-id="currentJobId"
          :stop-job="stopJob"
          :show-progress="showProgress"
          :progress-pct="progressPct"
          :progress-msg="progressMsg"
          :parse-err="parseErr"
          :show-result="showResult"
          :result-partial="resultPartial"
          :parse-batch-results="parseBatchResults"
          :batch-file-links="batchFileLinks"
          :result-links="resultLinks"
          @update:prompt="(v) => (prompt = v)"
          @update:pdf-pages-requested="(v) => (pdfPagesRequested = v)"
        />

        <!-- 系统设置 -->
        <WorkspaceSettingsView
          v-show="activeMenu === 'settings'"
          :is-admin="isAdmin"
          :settings-load-error="settingsLoadError"
          :settings-summary="settingsSummary"
          :admin-save-loading="adminSaveLoading"
          :save-admin-settings="saveAdminSettings"
          :admin-settings-tab="adminSettingsTab"
          :active-security-panels="activeSecurityPanels"
          :admin-form="adminForm"
          :upload-size-validation="uploadSizeValidation"
          :nginx-config="nginxConfig"
          @update:admin-settings-tab="(v) => (adminSettingsTab = v)"
          @update:active-security-panels="(v) => (activeSecurityPanels = v)"
        />

        <!-- 模型配置 -->
        <WorkspaceModelConfigView
          v-show="activeMenu === 'model-config'"
          :is-admin="isAdmin"
          :settings-load-error="settingsLoadError"
          :admin-save-loading="adminSaveLoading"
          :save-admin-settings="saveAdminSettings"
          :admin-form="adminForm"
          :model-status="modelStatus"
          :dl-source="dlSource"
          :dl-loading="dlLoading"
          :reload-loading="reloadLoading"
          :unload-loading="unloadLoading"
          :reload-error="reloadError"
          :run-model-download="runModelDownload"
          :stop-model-download="stopModelDownload"
          :clear-model-files="clearModelFiles"
          :reload-model="reloadModel"
          :unload-model="unloadModel"
          :check-paddle-config="checkPaddleConfig"
          :converter-config-data="converterConfigData"
          :converter-config-loading="converterConfigLoading"
          :converter-config-saving="converterConfigSaving"
          :download-schema="downloadSchema"
          :effective-paths="effectivePaths"
          :save-converter-config="saveConverterConfig"
          :update-converter-config-field="updateConverterConfigField"
          :update-converter-config-download-field="updateConverterConfigDownloadField"
          @update:dl-source="(v) => (dlSource = v)"
        />

        <!-- 个人中心 -->
        <div v-show="activeMenu === 'profile'" class="view-panel">
          <WorkspaceProfilePanel
            :user-profile="userProfile"
            :fmt-time="fmtTime"
            :pw-err="pwErr"
            :pw-ok="pwOk"
            :pw="pw"
            :pw-loading="pwLoading"
            @navigate="(menu) => (activeMenu = menu)"
            @refresh-profile="refreshProfile"
            @change-password="changePassword"
          />
        </div>

        <!-- 生成记录 -->
        <div v-show="activeMenu === 'records'" class="view-panel">
          <WorkspaceRecordsPanel
            ref="recordsPanelRef"
            :is-admin="isAdmin"
            :recovering-stale-jobs="recoveringStaleJobs"
            :batch-downloading="batchDownloading"
            :batch-deleting="batchDeleting"
            :records-selection-length="recordsSelection.length"
            :records-loading="recordsLoading"
            :records="records"
            :records-date-range="recordsDateRange"
            :records-filename="recordsFilename"
            :records-page="recordsPage"
            :records-page-size="recordsPageSize"
            :records-total="recordsTotal"
            :deleting-job-id="deletingJobId"
            :records-row-selectable="recordsRowSelectable"
            :fmt-time="fmtTime"
            :status-label="statusLabel"
            :dl="dl"
            @update-date-range="(v) => (recordsDateRange = v)"
            @update-filename="(v) => (recordsFilename = v)"
            @update-page="(v) => (recordsPage = v)"
            @update-page-size="(v) => (recordsPageSize = v)"
            @selection-change="(rows) => (recordsSelection = rows)"
            @search="searchRecords"
            @refresh="loadRecords"
            @recover-stale="confirmRecoverStaleJobs"
            @batch-download="handleBatchDownload"
            @batch-delete="confirmBatchDeleteJobs"
            @delete-one="confirmDeleteJob"
          />
        </div>

        <!-- 缓存清除 -->
        <div v-show="activeMenu === 'cache'" class="view-panel">
          <WorkspaceCachePanel
            :loading="cacheLoading"
            :rows="cacheRows"
            :selection="cacheSelection"
            :fmt-time="fmtTime"
            :status-label="statusLabel"
            @refresh="loadCacheList"
            @clear="clearCache"
            @selection-change="(rows) => (cacheSelection = rows)"
          />
        </div>

        <!-- 用户管理（仅管理员） -->
        <div v-show="activeMenu === 'users' && isAdmin" class="view-panel">
          <WorkspaceUsersPanel
            ref="usersPanelRef"
            :user-search-q="userSearchQ"
            :users-selection-length="usersSelection.length"
            :users-batch-loading="usersBatchLoading"
            :users-loading="usersLoading"
            :users-list="usersList"
            :username="username"
            :current-user-id="currentUserId"
            :user-page="userPage"
            :user-page-size="userPageSize"
            :user-total="userTotal"
            :users-row-selectable="usersRowSelectable"
            :fmt-time="fmtTime"
            :user-pdf-effective-display="userPdfEffectiveDisplay"
            @update-search-q="(v) => (userSearchQ = v)"
            @update-page="(v) => (userPage = v)"
            @update-page-size="(v) => (userPageSize = v)"
            @search="searchUsers"
            @refresh="loadUsers"
            @open-create-user="openCreateUserDialog"
            @batch-active="batchUsersActive"
            @batch-admin="batchUsersAdmin"
            @open-batch-pdf="openBatchPdfDialog"
            @batch-delete="batchUsersDelete"
            @selection-change="(rows) => (usersSelection = rows)"
            @edit-user="openUserEdit"
            @view-session="viewUserSession"
            @kick-user="kickUserConfirm"
          />
        </div>

        <WorkspaceUserEditDialog
          v-model="userEditVisible"
          :form="userEditForm"
          :loading="userSaveLoading"
          @closed="resetUserEditForm"
          @submit="submitUserEdit"
        />

        <WorkspaceCreateUserDialog
          ref="createUserDialogRef"
          v-model="createUserVisible"
          :form="createUserForm"
          :rules="createUserRules"
          :loading="createUserLoading"
          @closed="resetCreateUserForm"
          @submit="submitCreateUser"
        />

        <WorkspaceBatchPdfDialog
          v-model="batchPdfDialogVisible"
          :use-default="batchPdfUseDefault"
          :pages="batchPdfPages"
          :loading="usersBatchLoading"
          @update:use-default="(v) => (batchPdfUseDefault = v)"
          @update:pages="(v) => (batchPdfPages = v)"
          @submit="submitBatchPdf"
        />

        <WorkspaceUserSessionDialog
          v-model="sessionDialogVisible"
          :session-loading="sessionLoading"
          :session-data="sessionData"
          :session-user-id="sessionUserId"
          :current-user-id="currentUserId"
          :kicking-user="kickingUser"
          :fmt-time="fmtTime"
          @kick-user="confirmKickUser"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

import http from '@/api/http'
import { startTokenRefresh, stopTokenRefresh } from '@/api/http'

import WorkspaceProfilePanel from '@/components/workspace/WorkspaceProfilePanel.vue'
import WorkspaceParseView from '@/components/workspace/WorkspaceParseView.vue'
import WorkspaceSettingsView from '@/components/workspace/WorkspaceSettingsView.vue'
import WorkspaceModelConfigView from '@/components/workspace/WorkspaceModelConfigView.vue'
import WorkspaceCachePanel from '@/components/workspace/WorkspaceCachePanel.vue'
import WorkspaceRecordsPanel from '@/components/workspace/WorkspaceRecordsPanel.vue'
import WorkspaceUsersPanel from '@/components/workspace/WorkspaceUsersPanel.vue'
import WorkspaceUserEditDialog from '@/components/workspace/WorkspaceUserEditDialog.vue'
import WorkspaceCreateUserDialog from '@/components/workspace/WorkspaceCreateUserDialog.vue'
import WorkspaceBatchPdfDialog from '@/components/workspace/WorkspaceBatchPdfDialog.vue'
import WorkspaceUserSessionDialog from '@/components/workspace/WorkspaceUserSessionDialog.vue'

import { useWorkspaceSettings } from '@/composables/WorkspaceSettings'
import { useWorkspaceCachePanel } from '@/composables/WorkspaceCachePanel'
import { useWorkspaceParse } from '@/composables/WorkspaceParse'
import { useWorkspaceProfilePanel } from '@/composables/WorkspaceProfilePanel'
import { useWorkspaceRecordsPanel } from '@/composables/WorkspaceRecordsPanel'
import { useWorkspaceUsersPanel } from '@/composables/WorkspaceUsersPanel'
import { dl, fmtTime, statusLabel } from '@/utils/workspaceFormatters'

// PDF worker 配置：默认本地打包，支持通过环境变量切换 CDN 兜底
if (typeof window !== 'undefined') {
  const cdnUrls = [
    `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`,
    `https://cdn.jsdelivr.net/npm/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`,
    `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`
  ]
  const useCdnFallback = String(import.meta.env.VITE_PDF_WORKER_USE_CDN_FALLBACK || '').toLowerCase() === 'true'

  if (useCdnFallback) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = cdnUrls[0]
    console.log('[PDF] 使用 CDN worker:', cdnUrls[0])
  } else {
    pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl
    console.log('[PDF] 使用本地 worker:', pdfWorkerUrl)
  }
}

/** 模板与逻辑共用：判断是否为 PDF 扩展名（const 保证在 script setup 中稳定暴露给模板） */
const isPdfFileName = (name) => /\.pdf$/i.test(String(name || ''))

/** 生成 UUID v4（兼容不支持 crypto.randomUUID 的环境） */
function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // 降级方案：使用 Math.random 生成 UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

/** 从 Axios 错误中取 detail；responseType 为 blob 时响应体为 Blob，需异步解析 */
async function axiosErrorDetail(error, fallback = '请求失败') {
  const msg = error?.message
  const data = error?.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      try {
        const json = JSON.parse(text)
        if (json?.detail != null) {
          return typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail)
        }
      } catch {
        if (text) return text.length > 500 ? `${text.slice(0, 500)}…` : text
      }
    } catch {
      /* ignore */
    }
    return msg || fallback
  }
  if (data?.detail != null) {
    return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
  }
  return msg || fallback
}

const router = useRouter()
const username = ref('…')
/** 当前用户 ID */
const currentUserId = ref(null)
/** 用户详细信息 */
const userProfile = reactive({
  id: null,
  username: '',
  email: '',
  phone: '',
  is_admin: false,
  is_active: true,
  created_at: null,
  // PDF 配额
  pdf_max_pages_global: 80,
  pdf_max_pages_personal: null,
  pdf_max_pages_effective: 80,
  pdf_use_default: true,
  // 图片输出配置
  can_download_images: true,
  image_output_mode: null,
  image_output_use_default: true,
})
/** 视口 ≤768px 时使用抽屉侧栏 */
const isMobile = ref(false)
const mobileNavOpen = ref(false)
const activeMenu = ref('parse')
const dragOver = ref(false)

/** 注入全局 Tooltip 样式，覆盖 Element Plus 默认白色背景 */
function injectTooltipStyles() {
  const styleId = 'custom-tooltip-styles'
  // 避免重复注入
  if (document.getElementById(styleId)) return
  
  const style = document.createElement('style')
  style.id = styleId
  style.textContent = `
    /* 强制覆盖所有 dark 主题的 Tooltip */
    .el-popper.is-dark,
    .el-tooltip__popper.is-dark {
      background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
      border: 1px solid rgba(99, 102, 241, 0.3) !important;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4), 
                  0 0 0 1px rgba(99, 102, 241, 0.1),
                  inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
      color: #e8eef8 !important;
      backdrop-filter: blur(8px);
      z-index: 9999 !important;
    }
    
    .el-popper.is-dark .el-popper__arrow::before,
    .el-tooltip__popper.is-dark .el-popper__arrow::before {
      background: linear-gradient(135deg, #1a2540 0%, #141c2f 100%) !important;
      border: 1px solid rgba(99, 102, 241, 0.3) !important;
    }
    
    .el-popper.is-dark .el-popper__content,
    .el-tooltip__popper.is-dark .el-popper__content {
      color: #e8eef8 !important;
      line-height: 1.6;
      padding: 2px 0;
    }
    
    .el-popper.is-dark code,
    .el-tooltip__popper.is-dark code {
      background: rgba(0, 0, 0, 0.35) !important;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
      color: #7dd3fc !important;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      border: 1px solid rgba(125, 211, 252, 0.2);
    }
  `
  document.head.appendChild(style)
  console.log('[Tooltip Styles] Custom dark theme injected')
}

// settings/admin
const {
  settingsLoadError,
  settingsSummary,
  effectivePaths,
  nginxConfig,
  isAdmin,
  adminSaveLoading,
  adminSettingsTab,
  activeSecurityPanels,
  activeEmailPanels,
  activeSmsPanels,
  dlLoading,
  reloadLoading,
  unloadLoading,
  reloadError,
  dlSource,
  modelStatus,
  adminForm,
  converterConfigData,
  converterConfigLoading,
  converterConfigSaving,
  downloadSchema,
  dirPickerSupported,
  uploadSizeValidation,
  pickOutputDir,
  pasteOutputPathFromClipboard,
  loadSettings,
  loadConverterConfig,
  updateConverterConfigField,
  updateConverterConfigDownloadField,
  saveConverterConfig,
  saveAdminSettings,
  runModelDownload,
  stopModelDownload,
  clearModelFiles,
  checkModelStatus,
  reloadModel,
  unloadModel,
  checkPaddleConfig,
  disposeAdminSettings,
} = useWorkspaceSettings({
  http,
  ElMessage,
  ElMessageBox,
  ElNotification,
  axiosErrorDetail,
})

// profile/auth
const { pw, pwErr, pwOk, pwLoading, changePassword, refreshProfile } = useWorkspaceProfilePanel({
  http,
  ElMessage,
  userProfile,
})

// records
const {
  records,
  recordsLoading,
  recordsPage,
  recordsPageSize,
  recordsTotal,
  recordsDateRange,
  recordsFilename,
  recordsPanelRef,
  recordsSelection,
  batchDeleting,
  batchDownloading,
  recoveringStaleJobs,
  deletingJobId,
  recordsRowSelectable,
  searchRecords,
  loadRecords,
  confirmDeleteJob,
  confirmBatchDeleteJobs,
  handleBatchDownload,
  confirmRecoverStaleJobs,
} = useWorkspaceRecordsPanel({
  http,
  ElMessage,
  ElMessageBox,
  axiosErrorDetail,
  staleJobTimeoutMinutesRef: computed(() => adminForm.stale_job_timeout_minutes),
})
// users
const {
  usersPanelRef,
  usersSelection,
  usersBatchLoading,
  batchPdfDialogVisible,
  batchPdfUseDefault,
  batchPdfPages,
  usersList,
  usersLoading,
  userPage,
  userPageSize,
  userTotal,
  userSearchQ,
  userEditVisible,
  userSaveLoading,
  userEditForm,
  sessionDialogVisible,
  sessionLoading,
  sessionData,
  sessionUserId,
  kickingUser,
  createUserVisible,
  createUserLoading,
  createUserDialogRef,
  createUserForm,
  createUserRules,
  usersRowSelectable,
  searchUsers,
  userPdfEffectiveDisplay,
  loadUsers,
  openUserEdit,
  resetUserEditForm,
  submitUserEdit,
  viewUserSession,
  kickUserConfirm,
  confirmKickUser,
  openCreateUserDialog,
  resetCreateUserForm,
  submitCreateUser,
  batchUsersActive,
  batchUsersAdmin,
  openBatchPdfDialog,
  submitBatchPdf,
  batchUsersDelete,
} = useWorkspaceUsersPanel({
  http,
  ElMessage,
  ElMessageBox,
  isAdmin,
  username,
  currentUserId,
  settingsSummary,
})

// cache
const {
  cacheRows,
  cacheLoading,
  cacheSelection,
  loadCacheList,
  clearCache,
} = useWorkspaceCachePanel({
  http,
  ElMessage,
  ElMessageBox,
  refreshRecords: loadRecords,
})
// parse workflow
const {
  parseQueue,
  parseBatchResults,
  prompt,
  pdfPagesRequested,
  parsing,
  progressPct,
  progressMsg,
  parseErr,
  showProgress,
  showResult,
  resultPartial,
  currentJobId,
  resultJobId,
  showStop,
  pdfPagesMax,
  hasQueue,
  queueTotalPages,
  pdfPagesSliderMax,
  pdfPageCountLoading,
  fileLabel,
  clampPdfPagesRequested,
  setParsePromptExample,
  formatPdfPagesTooltip,
  addFilesToQueue,
  removeQueueItem,
  clearParseQueue,
  startParse,
  stopJob,
  disposeParseWorkflow,
} = useWorkspaceParse({
  http,
  ElMessage,
  pdfjsLib,
  generateUUID,
  isPdfFileName,
  allowMultiFileUploadRef: computed(() => adminForm.allow_multi_file_upload),
  pdfMaxPagesRef: computed(() => settingsSummary.pdf_max_pages),
  refreshRecords: loadRecords,
})

const menuTitle = computed(() => {
  const map = {
    parse: '文档解析',
    settings: '系统设置',
    'model-config': '模型配置',
    profile: '个人中心',
    records: '生成记录',
    cache: '缓存清除',
    users: '用户管理',
  }
  return map[activeMenu.value] || ''
})


const resultLinks = computed(() => {
  const id = resultJobId.value
  if (!id) return []
  return batchFileLinks(id)
})

function batchFileLinks(jobId) {
  if (!jobId) return []
  const links = [
    { name: '可视化（单页 PNG / 多页 ZIP）', path: `/download/${jobId}/visualization` },
    { name: '原始输出 _raw.md', path: `/download/${jobId}/raw` },
    { name: '转换输出 .md', path: `/download/${jobId}/markdown` },
  ]
  
  // 检查是否有完整结果 ZIP 文件
  const job = records.value.find(r => r.job_id === jobId)
  if (job && job.has_result_zip) {
    links.push({ name: '完整结果（ZIP，含图片）', path: `/download/${jobId}/result` })
  }
  
  return links
}

function onMenuSelect(index) {
  activeMenu.value = index
  if (isMobile.value) mobileNavOpen.value = false
}

function onSiderBrandClick() {
  if (isMobile.value) mobileNavOpen.value = false
}

function updateMobileLayout() {
  const mq = window.matchMedia('(max-width: 768px)')
  isMobile.value = mq.matches
  if (!mq.matches) mobileNavOpen.value = false
}

watch(activeMenu, (m) => {
  if (m === 'settings') loadSettings()
  if (m === 'model-config') {
    loadSettings()
    checkModelStatus()
  }
  if (m === 'records') loadRecords()
  if (m === 'cache') loadCacheList()
  if (m === 'users' && isAdmin.value) loadUsers()
})

watch([mobileNavOpen, isMobile], () => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = isMobile.value && mobileNavOpen.value ? 'hidden' : ''
})

onMounted(async () => {
  // 注入全局 Tooltip 样式
  injectTooltipStyles()
  
  updateMobileLayout()
  window.addEventListener('resize', updateMobileLayout, { passive: true })
  window.addEventListener('keydown', onNavEscape)
  const mq = window.matchMedia('(max-width: 768px)')
  if (mq.addEventListener) {
    mq.addEventListener('change', updateMobileLayout)
  } else {
    mq.addListener(updateMobileLayout)
  }
  try {
    const { data } = await http.get('/api/auth/me')
    username.value = data?.username || '用户'
    isAdmin.value = !!data?.is_admin
    currentUserId.value = data?.id || null
    
    // 初始化个人资料
    Object.assign(userProfile, {
      id: data.id,
      username: data.username,
      email: data.email,
      phone: data.phone || '',
      is_admin: !!data.is_admin,
      is_active: !!data.is_active,
      created_at: data.created_at,
      pdf_max_pages_global: data.pdf_max_pages_global || 80,
      pdf_max_pages_personal: data.pdf_max_pages_personal,
      pdf_max_pages_effective: data.pdf_max_pages_effective || 80,
      pdf_use_default: !!data.pdf_use_default,
      can_download_images: !!data.can_download_images,
      image_output_mode: data.image_output_mode || null,
      image_output_use_default: !!data.image_output_use_default,
    })
    
    // 普通用户不能停留在管理侧菜单
    if (!isAdmin.value && (activeMenu.value === 'settings' || activeMenu.value === 'model-config')) {
      activeMenu.value = 'parse'
    }
    
    await loadSettings()
    await checkModelStatus()

    // 启动 Token 自动刷新（页面刷新后重新挂载）
    startTokenRefresh()
    console.log('[Workspace] Token 刷新机制已启动')
  } catch {
    router.replace('/login')
  }
})

function onNavEscape(e) {
  if (e.key === 'Escape' && mobileNavOpen.value) mobileNavOpen.value = false
}

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
  window.removeEventListener('resize', updateMobileLayout)
  window.removeEventListener('keydown', onNavEscape)
  const mq = window.matchMedia('(max-width: 768px)')
  if (mq.removeEventListener) {
    mq.removeEventListener('change', updateMobileLayout)
  } else {
    mq.removeListener(updateMobileLayout)
  }
  // 清理 settings/admin 侧定时器
  disposeAdminSettings()
  // 清理解析流程中的 ws 连接
  disposeParseWorkflow()
  // 停止 Token 刷新
  stopTokenRefresh()
})

async function logout() {
  // 停止 Token 刷新机制
  stopTokenRefresh()
  console.log('[退出] Token 刷新机制已停止')
  
  await http.post('/api/auth/logout')
  router.replace('/')
}

function onFilePick(e) {
  addFilesToQueue(e.target.files)
  if (e?.target) e.target.value = ''
}

function onDrop(e) {
  dragOver.value = false
  addFilesToQueue(e.dataTransfer.files)
}

</script>

<style scoped src="../styles/Workspace.css"></style>
