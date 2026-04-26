import { computed, ref, watch } from 'vue'

/**
 * useParseWorkflow
 * - 用途：封装解析流程主链路（队列管理、页数约束、上传解析、WS 进度、停止解析）
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - pdfjsLib: PDF.js 模块（用于读取 PDF 页数）
 *   - generateUUID: 队列项 ID 生成函数
 *   - isPdfFileName: PDF 文件名判断函数
 *   - allowMultiFileUploadRef: 是否允许多文件上传
 *   - pdfMaxPagesRef: 当前账号可解析页数上限
 *   - refreshRecords: 解析完成后刷新记录的回调
 * - 返回值：
 *   - 状态：parseQueue/进度/结果相关响应式对象
 *   - 动作：add/remove/clear/start/stop/dispose 等方法
 */
const PDF_PAGES_DEFAULT = 5
const PARSE_ALLOWED_EXT = new Set(['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.pdf'])

function parseFileExt(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

function parseQueueFileKey(f) {
  return `${f.name}\0${f.size}\0${f.lastModified}`
}

export function useWorkspaceParse({
  http,
  ElMessage,
  pdfjsLib,
  generateUUID,
  isPdfFileName,
  allowMultiFileUploadRef,
  pdfMaxPagesRef,
  refreshRecords,
}) {
  const parseQueue = ref([])
  const parseBatchResults = ref([])
  const batchAbort = ref(false)
  const prompt = ref('')
  const pdfPagesRequested = ref(PDF_PAGES_DEFAULT)
  const parsing = ref(false)
  const progressPct = ref(0)
  const progressMsg = ref('')
  const parseErr = ref('')
  const showProgress = ref(false)
  const showResult = ref(false)
  const resultPartial = ref(false)
  const currentJobId = ref(null)
  const resultJobId = ref(null)
  let ws = null

  const showStop = computed(() => parsing.value && !!currentJobId.value)
  const hasQueue = computed(() => parseQueue.value.length > 0)
  const pdfPagesMax = computed(() => Math.max(1, pdfMaxPagesRef.value || 80))

  function queueItemPageContribution(x) {
    if (!isPdfFileName(x.file.name)) return { ready: true, n: 1 }
    if (x.pdfNumPages === undefined) return { ready: false }
    if (typeof x.pdfNumPages === 'number' && x.pdfNumPages > 0) return { ready: true, n: x.pdfNumPages }
    return { ready: false }
  }

  const queueTotalPages = computed(() => {
    let sum = 0
    for (const x of parseQueue.value) {
      const c = queueItemPageContribution(x)
      if (!c.ready) return null
      sum += c.n
    }
    return sum
  })

  const queueMaxSingleFilePages = computed(() => {
    let maxPages = 0
    for (const x of parseQueue.value) {
      const c = queueItemPageContribution(x)
      if (!c.ready) return null
      maxPages = Math.max(maxPages, c.n)
    }
    return maxPages
  })

  const pdfPagesSliderMax = computed(() => {
    const userCap = pdfPagesMax.value
    const maxSingleFile = queueMaxSingleFilePages.value
    if (maxSingleFile != null && maxSingleFile > 0) return Math.min(userCap, maxSingleFile)
    return userCap
  })

  const pdfPageCountLoading = computed(() =>
    parseQueue.value.some((x) => isPdfFileName(x.file.name) && x.pdfNumPages === undefined)
  )

  const fileLabel = computed(() => {
    const q = parseQueue.value
    if (!q.length) return '尚未添加文件，点击上方区域或拖拽添加（可多选、可多次添加）'
    const kb = Math.round(q.reduce((s, x) => s + x.file.size, 0) / 1024)
    return `已添加 ${q.length} 个文件（合计约 ${kb} KB），解析前可移除单项或清空`
  })

  function clampPdfPagesRequested() {
    const m = pdfPagesSliderMax.value
    let v = pdfPagesRequested.value
    if (typeof v !== 'number' || Number.isNaN(v)) v = PDF_PAGES_DEFAULT
    v = Math.round(v)
    pdfPagesRequested.value = Math.min(Math.max(1, v), m)
  }

  watch([pdfPagesMax, pdfPagesSliderMax], () => {
    clampPdfPagesRequested()
  })

  function setParsePromptExample(text) {
    prompt.value = text
  }

  function formatPdfPagesTooltip(val) {
    return `${val} 页`
  }

  async function loadPdfNumPagesForQueueItem(item) {
    if (!/\.pdf$/i.test(item.file.name)) return

    let retryCount = 0
    const maxRetries = 2

    while (retryCount <= maxRetries) {
      try {
        const buf = await item.file.arrayBuffer()
        if (buf.byteLength < 5) throw new Error('文件太小，不是有效的 PDF')
        const doc = await pdfjsLib.getDocument({
          data: buf,
          cMapUrl: undefined,
          cMapPacked: false,
          disableFontFace: true,
          maxImageSize: -1,
        }).promise

        const numPages = doc.numPages
        const index = parseQueue.value.findIndex((x) => x.id === item.id)
        if (index !== -1) {
          parseQueue.value[index] = { ...parseQueue.value[index], pdfNumPages: numPages }
        }
        return
      } catch (err) {
        retryCount++
        if (retryCount > maxRetries) {
          let errorMsg = '无法读取'
          if (err.message.includes('worker') || err.message.includes('Worker')) errorMsg = '浏览器不支持'
          else if (err.message.includes('Invalid') || err.message.includes('损坏')) errorMsg = '格式无效'
          else if (err.message.includes('Network') || err.message.includes('network')) errorMsg = '网络错误'

          const index = parseQueue.value.findIndex((x) => x.id === item.id)
          if (index !== -1) {
            parseQueue.value[index] = { ...parseQueue.value[index], pdfNumPages: null, pdfError: errorMsg }
          }
        }
        if (retryCount <= maxRetries) {
          await new Promise((resolve) => setTimeout(resolve, 500))
        }
      }
    }

    clampPdfPagesRequested()
  }

  function effectivePdfPagesForItem(item) {
    const cap = pdfPagesMax.value
    const want = Math.min(cap, Math.max(1, Math.round(Number(pdfPagesRequested.value) || PDF_PAGES_DEFAULT)))
    if (!/\.pdf$/i.test(item.file.name)) return want
    const doc = item.pdfNumPages
    if (typeof doc === 'number' && doc > 0) return Math.min(want, doc)
    return want
  }

  function addFilesToQueue(fileList) {
    const arr = Array.from(fileList || []).filter((f) => f && PARSE_ALLOWED_EXT.has(parseFileExt(f.name)))
    if (!arr.length) {
      if (fileList && fileList.length) ElMessage.warning('没有可添加的文件（仅支持图片或 PDF）')
      return
    }

    if (!allowMultiFileUploadRef.value) {
      const file = arr[0]
      parseQueue.value = []
      const row = { id: generateUUID(), file }
      if (/\.pdf$/i.test(file.name)) {
        row.pdfNumPages = undefined
        loadPdfNumPagesForQueueItem(row)
      }
      parseQueue.value = [row]
      parseErr.value = ''
      showResult.value = false
      showProgress.value = false
      clampPdfPagesRequested()
      ElMessage.info('已替换当前文件')
      return
    }

    const existing = new Set(parseQueue.value.map((x) => parseQueueFileKey(x.file)))
    const seenThisPick = new Set()
    const newFiles = []
    let skipped = 0
    for (const f of arr) {
      const k = parseQueueFileKey(f)
      if (existing.has(k) || seenThisPick.has(k)) {
        skipped += 1
        continue
      }
      seenThisPick.add(k)
      existing.add(k)
      newFiles.push(f)
    }
    if (!newFiles.length) {
      ElMessage.warning(skipped ? '所选文件均已在待解析列表中，未重复添加' : '')
      return
    }
    if (skipped) {
      ElMessage.info(`已跳过 ${skipped} 个重复项（与列表中或本次选择重复）`)
    }
    const added = newFiles.map((file) => {
      const row = { id: generateUUID(), file }
      if (/\.pdf$/i.test(file.name)) {
        row.pdfNumPages = undefined
        loadPdfNumPagesForQueueItem(row)
      }
      return row
    })
    parseQueue.value = [...parseQueue.value, ...added]
    parseErr.value = ''
    showResult.value = false
    showProgress.value = false
    clampPdfPagesRequested()
  }

  function removeQueueItem(id) {
    parseQueue.value = parseQueue.value.filter((x) => x.id !== id)
  }

  function clearParseQueue() {
    parseQueue.value = []
  }

  function closeWs() {
    if (ws) {
      try {
        ws.close()
      } catch {
        // ignore
      }
      ws = null
    }
  }

  function waitForJobWs(jobId) {
    return new Promise((resolve, reject) => {
      closeWs()
      currentJobId.value = jobId
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${proto}//${window.location.host}/ws/${jobId}`
      const sock = new WebSocket(url)
      ws = sock

      sock.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'progress') {
          progressPct.value = data.progress
          progressMsg.value = data.message || ''
        } else if (data.type === 'error') {
          parseErr.value = data.message
          currentJobId.value = null
          try {
            sock.close()
          } catch {
            // ignore
          }
          reject(new Error(data.message || '解析失败'))
        } else if (data.type === 'completion') {
          progressPct.value = 100
          progressMsg.value = data.user_stopped ? '已停止，可下载当前已生成部分。' : '处理完成！'
          resultPartial.value = !!data.partial
          currentJobId.value = null
          try {
            sock.close()
          } catch {
            // ignore
          }
          refreshRecords().catch(() => {})
          resolve(data)
        }
      }

      sock.onerror = () => {
        parseErr.value = 'WebSocket 连接失败'
        currentJobId.value = null
        reject(new Error('WebSocket 连接失败'))
      }
    })
  }

  async function startParse() {
    const queue = [...parseQueue.value]
    if (!queue.length) return

    const filesToProcess = allowMultiFileUploadRef.value ? queue : [queue[0]]
    batchAbort.value = false
    parseErr.value = ''
    parseBatchResults.value = []
    showResult.value = false
    resultPartial.value = false
    resultJobId.value = null
    parsing.value = true
    showProgress.value = true
    progressPct.value = 0
    const p = prompt.value.trim()
    const results = []
    const total = filesToProcess.length

    for (let i = 0; i < filesToProcess.length; i++) {
      if (batchAbort.value) break
      parseErr.value = ''
      const item = filesToProcess[i]
      const name = item.file.name
      progressMsg.value = total > 1 ? `（${i + 1}/${total}）${name}：正在上传…` : '正在上传文件…'

      const fd = new FormData()
      fd.append('file', item.file)
      if (p) fd.append('prompt', p)
      if (/\.pdf$/i.test(name)) {
        fd.append('pdf_pages', String(effectivePdfPagesForItem(item)))
      }

      try {
        const { data } = await http.post('/upload', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        progressPct.value = 0
        progressMsg.value = total > 1 ? `（${i + 1}/${total}）${name}：解析中…` : '正在解析文件…'
        await waitForJobWs(data.job_id)
        results.push({ ok: true, job_id: data.job_id, filename: name })
      } catch (e) {
        const msg = e?.response?.data?.detail || e?.message || '失败'
        parseErr.value = msg
        results.push({ ok: false, filename: name, error: msg })
      }
    }

    parseBatchResults.value = results
    parsing.value = false
    showProgress.value = false
    currentJobId.value = null
    closeWs()

    const anyOk = results.some((r) => r.ok)
    showResult.value = anyOk
    if (anyOk) {
      const lastOk = [...results].reverse().find((r) => r.ok)
      if (lastOk) resultJobId.value = lastOk.job_id
    }

    if (!batchAbort.value && results.length && results.every((r) => r.ok)) {
      parseQueue.value = []
      ElMessage.success(allowMultiFileUploadRef.value ? `已完成 ${results.length} 个文件的解析` : '解析完成')
    } else if (batchAbort.value) {
      ElMessage.info('已停止，后续文件未继续解析')
    } else if (results.some((r) => !r.ok)) {
      ElMessage.warning('部分文件未成功，请查看说明或生成记录')
    }
  }

  async function stopJob() {
    batchAbort.value = true
    if (!currentJobId.value) return
    try {
      await http.post(`/api/jobs/${encodeURIComponent(currentJobId.value)}/stop`)
      progressMsg.value = '正在停止…请稍候'
    } catch {
      progressMsg.value = '停止请求已发送'
    }
  }

  function disposeParseWorkflow() {
    closeWs()
  }

  return {
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
  }
}
