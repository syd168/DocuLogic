import { computed, reactive, ref, toRaw, watch } from 'vue'

/**
 * useAdminSettings
 * - 用途：封装系统设置/管理员侧状态与动作（读取、保存、模型下载/重载/卸载、状态轮询）
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - ElMessageBox: Element Plus 确认框
 *   - ElNotification: Element Plus 通知组件
 *   - axiosErrorDetail: 统一错误解析函数
 * - 返回值：
 *   - 状态：settingsSummary、adminForm、modelStatus、loading 状态等
 *   - 动作：load/save/checkModelStatus/reload/unload/download/dispose 等方法
 */
export function useWorkspaceSettings({
  http,
  ElMessage,
  ElMessageBox,
  ElNotification,
  axiosErrorDetail,
}) {
  const settingsLoadError = ref('')
  const settingsSummary = reactive({
    pdf_max_pages: 80,
    pdf_max_pages_global: 80,
    model_loaded: false,
    output_dir: '',
    is_admin: false,
  })

  const effectivePaths = reactive({
    output: '',
    model: '',
  })

  const nginxConfig = reactive({
    max_body_size_mb: 55,
  })

  const isAdmin = ref(false)
  const adminSaveLoading = ref(false)
  const adminSettingsTab = ref('security')
  const activeSecurityPanels = ref([])
  const activeEmailPanels = ref([])
  const activeSmsPanels = ref([])
  const dlLoading = ref(false)
  const reloadLoading = ref(false)
  const unloadLoading = ref(false)
  const reloadError = ref('')
  const dlSource = ref('modelscope')
  const modelStatus = ref({
    model_loaded: false,
    downloading: false,
    download_success: false,
    download_error: null,
    download_message: '',
    download_task_id: '',
  })
  let statusCheckInterval = null
  const converterConfigData = ref({})
  const converterConfigLoading = ref(false)
  const converterConfigSaving = ref(false)
  const converterConfigApiWarned = ref(false)
  const downloadSchema = ref({})
  const downloadTaskId = ref('')

  // 注意：转换器 ID 的标准化由后端统一处理（converts/middleware/registry.normalize_engine_id）
  // 前端直接使用后端返回的标准化 ID，不再进行额外的别名映射

  const adminForm = reactive({
    registration_enabled: true,
    captcha_login_enabled: false,
    captcha_register_enabled: false,
    captcha_forgot_enabled: false,
    pdf_max_pages: 80,
    output_dir: '',
    default_converter_id: '', // 将在加载配置后动态设置
    available_converters: [],
    email_mock: true,
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_from: '',
    smtp_password: '',
    smtp_use_tls: true,
    smtp_password_configured: false,
    register_email_enabled: true,
    register_phone_enabled: true,
    login_email_enabled: true,
    login_phone_enabled: true,
    forgot_email_enabled: true,
    forgot_phone_enabled: true,
    sms_mock: true,
    sms_http_url: '',
    sms_http_secret: '',
    sms_http_headers_json: '',
    sms_http_body_template: '',
    sms_http_secret_configured: false,
    show_page_numbers: true,
    image_output_mode: 'base64',
    stale_job_timeout_minutes: 10,
    login_timeout_minutes: 10,
    password_min_length: 8,
    password_require_uppercase: true,
    password_require_lowercase: true,
    password_require_digit: true,
    password_require_special: false,
    max_upload_size_mb: 50,
    allow_multi_file_upload: true,
  })

  const dirPickerSupported = computed(
    () => typeof window !== 'undefined' && typeof window.showDirectoryPicker === 'function'
  )

  const uploadSizeValidation = computed(() => {
    const backend = adminForm.max_upload_size_mb
    const nginx = nginxConfig.max_body_size_mb
    if (backend > nginx) {
      return {
        valid: false,
        type: 'error',
        message: `⚠️ 后端配置 (${backend}MB) 超过 Nginx 限制 (${nginx}MB)<br>用户将无法上传 ${nginx}-${backend}MB 之间的文件<br>建议将 NGINX_MAX_BODY_SIZE 设置为 ${Math.ceil(backend * 1.1)}m`,
      }
    } else if (backend === nginx) {
      return {
        valid: true,
        type: 'warning',
        message: `💡 提示：后端与 Nginx 配置相同 (${backend}MB)<br>建议 Nginx 略大于后端（如 ${Math.ceil(backend * 1.1)}m），以留有余量`,
      }
    } else if (nginx < backend * 1.05) {
      const recommended = Math.ceil(backend * 1.1)
      const margin = Math.round((recommended / backend - 1) * 100)
      return {
        valid: true,
        type: 'info',
        message: `💡 提示：Nginx 余量较小 (${nginx}MB vs ${backend}MB)<br>建议设置为 ${recommended}m（${margin}% 余量）`,
      }
    }
    return {
      valid: true,
      type: 'success',
      message: `✅ 配置合理（后端 ${backend}MB < Nginx ${nginx}MB）`,
    }
  })

  function applyAdminSettings(a = {}) {
    adminForm.registration_enabled = a.registration_enabled !== false
    adminForm.captcha_login_enabled = !!a.captcha_login_enabled
    adminForm.captcha_register_enabled = !!a.captcha_register_enabled
    adminForm.captcha_forgot_enabled = !!a.captcha_forgot_enabled
    adminForm.pdf_max_pages = a.pdf_max_pages || 80
    adminForm.output_dir = a.output_dir ?? ''
    
    // 动态设置转换器列表，不再使用硬编码 fallback
    const converters = Array.isArray(a.available_converters) ? a.available_converters : []
    adminForm.available_converters = converters
    
    // 设置默认转换器 ID：优先使用后端返回的值，否则使用第一个可用的转换器
    const backendId = String(a.default_converter_id || '').trim()
    if (backendId && converters.some(c => c.id === backendId)) {
      adminForm.default_converter_id = backendId
    } else if (converters.length > 0) {
      adminForm.default_converter_id = converters[0].id
    } else {
      adminForm.default_converter_id = '' // 无可用转换器时保持空值
    }
    
    adminForm.email_mock = a.email_mock !== false
    adminForm.smtp_host = a.smtp_host ?? ''
    adminForm.smtp_port = a.smtp_port ?? 587
    adminForm.smtp_user = a.smtp_user ?? ''
    adminForm.smtp_from = a.smtp_from ?? ''
    adminForm.smtp_password = ''
    adminForm.smtp_use_tls = a.smtp_use_tls !== false
    adminForm.smtp_password_configured = !!a.smtp_password_configured
    adminForm.register_email_enabled = a.register_email_enabled !== false
    adminForm.register_phone_enabled = a.register_phone_enabled !== false
    adminForm.login_email_enabled = a.login_email_enabled !== false
    adminForm.login_phone_enabled = a.login_phone_enabled !== false
    adminForm.forgot_email_enabled = a.forgot_email_enabled !== false
    adminForm.forgot_phone_enabled = a.forgot_phone_enabled !== false
    adminForm.sms_mock = a.sms_mock !== false
    adminForm.sms_http_url = a.sms_http_url ?? ''
    adminForm.sms_http_secret = ''
    adminForm.sms_http_headers_json = a.sms_http_headers_json ?? ''
    adminForm.sms_http_body_template = a.sms_http_body_template ?? ''
    adminForm.sms_http_secret_configured = !!a.sms_http_secret_configured
    adminForm.show_page_numbers = a.show_page_numbers !== false
    adminForm.image_output_mode = a.image_output_mode || 'base64'
    adminForm.stale_job_timeout_minutes = a.stale_job_timeout_minutes ?? 10
    adminForm.login_timeout_minutes = a.login_timeout_minutes ?? 10
    adminForm.password_min_length = a.password_min_length ?? 8
    adminForm.password_require_uppercase = a.password_require_uppercase !== false
    adminForm.password_require_lowercase = a.password_require_lowercase !== false
    adminForm.password_require_digit = a.password_require_digit !== false
    adminForm.password_require_special = !!a.password_require_special
    adminForm.max_upload_size_mb = a.max_upload_size_mb ?? 50
    adminForm.allow_multi_file_upload = a.allow_multi_file_upload !== false
    nginxConfig.max_body_size_mb = a.nginx_max_body_size_mb ?? 55
    effectivePaths.output = a.effective_output_dir || ''
    effectivePaths.model = a.effective_model_path || ''
  }

  async function pickOutputDir() {
    if (typeof window.showDirectoryPicker !== 'function') return
    try {
      const dir = await window.showDirectoryPicker()
      ElMessage({
        message: `已选择文件夹「${dir.name}」。因浏览器安全限制，无法自动填入完整磁盘路径。若该目录在运行后端的机器上，请在该机资源管理器地址栏或终端中复制其绝对路径，粘贴到上方输入框。`,
        type: 'info',
        duration: 12000,
        showClose: true,
      })
    } catch (e) {
      if (e?.name === 'AbortError') return
      ElMessage.error(e?.message || '无法打开文件夹选择')
    }
  }

  async function pasteOutputPathFromClipboard() {
    try {
      if (!navigator.clipboard || typeof navigator.clipboard.readText !== 'function') {
        ElMessage.warning('当前环境无法读取剪贴板，请直接在输入框中 Ctrl+V 粘贴')
        return
      }
      const t = (await navigator.clipboard.readText()).trim()
      if (!t) {
        ElMessage.warning('剪贴板为空')
        return
      }
      adminForm.output_dir = t
      ElMessage.success('已粘贴到输出目录')
    } catch {
      ElMessage.error('读取剪贴板失败（需 HTTPS 或 localhost，且需浏览器授权）')
    }
  }

  async function loadSettings() {
    settingsLoadError.value = ''
    try {
      const { data } = await http.get('/api/settings')
      settingsSummary.pdf_max_pages = data.pdf_max_pages ?? 80
      settingsSummary.pdf_max_pages_global = data.pdf_max_pages_global ?? data.pdf_max_pages ?? 80
      settingsSummary.model_loaded = !!data.model_loaded
      settingsSummary.output_dir = data.output_dir || '—'
      settingsSummary.is_admin = !!data.is_admin
      effectivePaths.output = ''
      effectivePaths.model = ''
      if (data.is_admin && data.admin) {
        applyAdminSettings(data.admin)
        await loadConverterConfig(data.admin.default_converter_id || adminForm.default_converter_id)
        await loadDownloadSchema(data.admin.default_converter_id || adminForm.default_converter_id)
      }
    } catch (e) {
      settingsLoadError.value = e.response?.data?.detail || e.message || '加载失败'
    }
  }

  async function loadConverterConfig(engineId = adminForm.default_converter_id) {
    const id = engineId
    if (!id) return
    converterConfigLoading.value = true
    try {
      const { data } = await http.get(`/api/admin/converter/config-data/${encodeURIComponent(id)}`)
      converterConfigData.value = data?.data && typeof data.data === 'object' ? data.data : {}
    } catch (e) {
      const status = e?.response?.status
      if (status === 404) {
        // 兼容后端尚未重启到新路由时，避免页面反复报错
        converterConfigData.value = {}
        if (!converterConfigApiWarned.value) {
          converterConfigApiWarned.value = true
          ElMessage.warning('文档解析器配置接口未就绪，请重启后端后重试')
        }
        return
      }
      ElMessage.error(e.response?.data?.detail || e.message || '加载文档解析器配置失败')
    } finally {
      converterConfigLoading.value = false
    }
  }

  async function loadDownloadSchema(engineId = adminForm.default_converter_id) {
    const id = engineId
    if (!id) return
    try {
      const { data } = await http.get(`/api/admin/converter/${encodeURIComponent(id)}/download/schema`)
      const schema = data?.schema && typeof data.schema === 'object' ? data.schema : {}
      downloadSchema.value = schema
      const allowed = Array.isArray(schema.allowed_sources) ? schema.allowed_sources : []
      if (schema.default_source && String(schema.default_source).trim()) {
        dlSource.value = String(schema.default_source).trim()
      } else if (allowed.length && !allowed.includes(dlSource.value)) {
        dlSource.value = String(allowed[0])
      }
    } catch (e) {
      downloadSchema.value = {}
      console.warn('Failed to load download schema:', e)
    }
  }

  async function saveConverterConfig() {
    const id = adminForm.default_converter_id
    if (!id) return
    converterConfigSaving.value = true
    try {
      await http.put(`/api/admin/converter/config-data/${encodeURIComponent(id)}`, {
        data: converterConfigData.value ?? {},
      })
      ElMessage.success('文档解析器配置已保存')
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '保存文档解析器配置失败')
    } finally {
      converterConfigSaving.value = false
    }
  }

  function updateConverterConfigField(key, value) {
    const k = String(key || '').trim()
    if (!k) return
    converterConfigData.value = {
      ...(converterConfigData.value || {}),
      [k]: value,
    }
  }

  /** 写入 download 子字段（与上方「下载目标目录」、下载按钮共用，不再在下方用 JSON 编辑整段 download） */
  function updateConverterConfigDownloadField(subKey, value) {
    const sub = String(subKey || '').trim()
    if (!sub) return
    const root = converterConfigData.value || {}
    const prev = root.download
    const base = prev && typeof prev === 'object' && !Array.isArray(prev) ? { ...prev } : {}
    converterConfigData.value = {
      ...root,
      download: { ...base, [sub]: value },
    }
  }

  async function saveAdminSettings() {
    adminSaveLoading.value = true
    try {
      const raw = toRaw(adminForm)
      const payload = { ...raw }
      delete payload.smtp_password_configured
      delete payload.sms_http_secret_configured
      delete payload.available_converters
      if (!payload.smtp_password || !String(payload.smtp_password).trim()) delete payload.smtp_password
      if (!payload.sms_http_secret || !String(payload.sms_http_secret).trim()) delete payload.sms_http_secret
      const { data: updatedSettings } = await http.put('/api/admin/settings', payload)
      if (updatedSettings) applyAdminSettings(updatedSettings)
      ElMessage.success('已保存')
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message)
    } finally {
      adminSaveLoading.value = false
    }
  }

  async function runModelDownload() {
    if (modelStatus.value.downloading) {
      ElMessage.warning('已有下载任务正在进行中，请稍后再试')
      return
    }
    dlLoading.value = true
    try {
      const engineId = adminForm.default_converter_id
      const { data } = await http.post(`/api/admin/converter/${encodeURIComponent(engineId)}/download/start`, {
        source: dlSource.value,
      })
      downloadTaskId.value = data?.task_id || ''
      ElMessage({ message: '✅ 下载任务已启动，请在下方查看实时日志', type: 'success', duration: 3000 })
      startStatusChecking()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message)
    } finally {
      dlLoading.value = false
    }
  }

  async function stopModelDownload() {
    const engineId = adminForm.default_converter_id
    const taskId = modelStatus.value.download_task_id || downloadTaskId.value
    if (!taskId) {
      ElMessage.warning('未找到可停止的下载任务')
      return
    }
    try {
      await http.post(`/api/admin/converter/${encodeURIComponent(engineId)}/download/stop/${encodeURIComponent(taskId)}`)
      ElMessage.success('已发送停止下载请求')
      await checkModelStatus()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '停止下载失败')
    }
  }

  async function clearModelFiles() {
    const engineId = adminForm.default_converter_id
    try {
      await ElMessageBox.confirm(
        '确定删除当前文档解析器模型文件夹吗？删除后如需使用需重新下载，可能耗时较长。',
        '确认删除模型文件',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    try {
      const { data } = await http.post(`/api/admin/converter/${encodeURIComponent(engineId)}/model-files/clear`, {})
      ElMessage.success(data?.message || '模型文件已删除')
      await checkModelStatus()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '删除模型文件失败')
    }
  }

  function startStatusChecking() {
    if (statusCheckInterval) clearInterval(statusCheckInterval)
    statusCheckInterval = setInterval(async () => {
      await checkModelStatus()
      if (!modelStatus.value.downloading) {
        stopStatusChecking()
        const downloadErrorText = String(modelStatus.value.download_error || '')
        const userStopped = downloadErrorText.includes('用户停止下载')
        if (modelStatus.value.download_success) {
          ElNotification({
            title: modelStatus.value.model_loaded ? '✅ 模型就绪' : '⚠️ 下载完成',
            message: modelStatus.value.model_loaded ? '模型已成功下载并加载，可以开始使用' : '模型已下载，但加载失败，请查看下方日志',
            type: modelStatus.value.model_loaded ? 'success' : 'warning',
            duration: 5000,
          })
        }
        if (userStopped) {
          ElNotification({
            title: '⛔ 已停止下载',
            message: '下载任务已由你手动停止',
            type: 'info',
            duration: 3000,
          })
        } else if (modelStatus.value.download_error) {
          ElNotification({
            title: '❌ 下载失败',
            message: '请查看下方日志了解详细错误信息',
            type: 'error',
            duration: 5000,
          })
        }
      }
    }, 5000)
  }

  function stopStatusChecking() {
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval)
      statusCheckInterval = null
    }
  }

  async function checkModelStatus() {
    try {
      const engineId = adminForm.default_converter_id
      const { data } = await http.get('/api/admin/model/status', {
        params: { engine_id: engineId },
      })
      downloadTaskId.value = data.download_task_id || downloadTaskId.value
      modelStatus.value = {
        model_loaded: data.model_loaded,
        downloading: data.downloading,
        download_success: data.download_success,
        download_error: data.download_error,
        download_message: data.download_message,
        download_dest: data.download_dest,
        download_source: data.download_source,
        download_repo: data.download_repo,
        download_task_id: data.download_task_id || '',
      }
      // 页面刷新后若后台仍在下载，自动恢复轮询，避免用户误以为任务中断
      if (modelStatus.value.downloading && !statusCheckInterval) {
        startStatusChecking()
        ElMessage.info('检测到后台下载任务仍在进行，已恢复状态追踪')
      }
    } catch (e) {
      console.error('Failed to check model status:', e)
    }
  }

  async function reloadModel() {
    if (modelStatus.value.downloading) {
      ElMessage.warning('下载任务正在进行中，请等待下载完成后再尝试重新加载')
      return
    }
    reloadLoading.value = true
    reloadError.value = ''
    try {
      const { data } = await http.post('/api/admin/model/reload')
      if (data.model_loaded) {
        reloadError.value = ''
        ElMessage.success('✅ 模型已成功重新加载')
      } else {
        reloadError.value = '⚠️ 模型未加载'
        ElMessage.warning(data.message || '模型目录不存在或加载失败')
      }
      await checkModelStatus()
      await loadSettings()
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message
      const hideBottomReloadError =
        String(errorMsg).includes('模型文件夹不存在') ||
        String(errorMsg).includes('模型不存在') ||
        String(errorMsg).includes('模型已损坏')
      const shortMsg =
        errorMsg.includes('No such file')
          ? '模型文件不存在'
          : errorMsg.includes('CUDA out of memory')
            ? '显存不足'
            : errorMsg.split('：').pop()?.slice(0, 50) || '加载失败'
      reloadError.value = hideBottomReloadError ? '' : `❌ ${shortMsg}`
      ElMessage.error(`重新加载失败：${shortMsg}`)
    } finally {
      reloadLoading.value = false
    }
  }

  async function unloadModel() {
    if (modelStatus.value.downloading) {
      ElMessage.warning('下载任务正在进行中，请等待下载完成后再尝试卸载')
      return
    }
    if (!modelStatus.value.model_loaded) {
      ElMessage.info('ℹ️ 模型未加载，无需卸载')
      return
    }
    try {
      await ElMessageBox.confirm(
        '确定要卸载模型吗？这将释放显存，下次上传文档时将自动重新加载。',
        '确认卸载',
        { type: 'warning', confirmButtonText: '卸载', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    unloadLoading.value = true
    try {
      const { data } = await http.post('/api/admin/model/unload')
      ElMessage.success(data.message || '✅ 模型已成功卸载')
      await checkModelStatus()
      await loadSettings()
    } catch (e) {
      const errorMsg = await axiosErrorDetail(e, '卸载失败')
      ElMessage.error(`卸载失败：${errorMsg}`)
    } finally {
      unloadLoading.value = false
    }
  }

  async function checkConverterConfig() {
    try {
      const engineId = adminForm.default_converter_id
      if (!engineId) {
        ElMessage.warning('请先选择解析器')
        return
      }
      
      const { data } = await http.post(`/api/admin/converter/${engineId}/check-config`)
      const converterName = (adminForm.available_converters || []).find(c => c.id === engineId)?.name || engineId
      ElMessage.success(data?.message || `${converterName} 配置检查通过`)
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || '配置检查失败'
      ElMessage.error(detail)
    }
  }

  watch(
    () => adminForm.default_converter_id,
    (id) => {
      if (id) {
        loadConverterConfig(id)
        loadDownloadSchema(id)
      }
    }
  )

  function disposeAdminSettings() {
    stopStatusChecking()
  }

  return {
    // State
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
    
    // Actions
    pickOutputDir,
    pasteOutputPathFromClipboard,
    loadSettings,
    loadConverterConfig,
    loadDownloadSchema,
    updateConverterConfigField,
    updateConverterConfigDownloadField,
    saveConverterConfig,
    saveAdminSettings,
    runModelDownload,
    stopModelDownload,
    clearModelFiles,
    startStatusChecking,
    stopStatusChecking,
    checkModelStatus,
    reloadModel,
    unloadModel,
    checkConverterConfig,
    disposeAdminSettings,
  }
}
