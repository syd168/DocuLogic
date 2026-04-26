import { ref } from 'vue'

/**
 * useRecordsManagement
 * - 用途：管理生成记录页的数据加载、筛选、批量操作与恢复僵尸任务
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - ElMessageBox: Element Plus 确认框
 *   - axiosErrorDetail: 统一错误解析函数（支持 blob）
 *   - staleJobTimeoutMinutesRef: 僵尸任务恢复阈值（分钟）
 * - 返回值：
 *   - 状态：records*、batch*、recoveringStaleJobs、deletingJobId
 *   - 动作：load/search/delete/batch-download/recover 相关方法
 */
function formatDateParam(d) {
  if (!d) return null
  if (typeof d === 'string') return d.slice(0, 10)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function useWorkspaceRecordsPanel({
  http,
  ElMessage,
  ElMessageBox,
  axiosErrorDetail,
  staleJobTimeoutMinutesRef,
}) {
  const records = ref([])
  const recordsLoading = ref(false)
  const recordsPage = ref(1)
  const recordsPageSize = ref(20)
  const recordsTotal = ref(0)
  const recordsDateRange = ref(null)
  const recordsFilename = ref('')
  const recordsPanelRef = ref(null)
  const recordsSelection = ref([])
  const batchDeleting = ref(false)
  const batchDownloading = ref(false)
  const recoveringStaleJobs = ref(false)
  const deletingJobId = ref(null)

  function clearRecordsSelection() {
    recordsSelection.value = []
    recordsPanelRef.value?.clearSelection?.()
  }

  function recordsRowSelectable(row) {
    return row.status !== 'processing'
  }

  function searchRecords() {
    recordsPage.value = 1
    clearRecordsSelection()
    loadRecords()
  }

  async function loadRecords() {
    recordsLoading.value = true
    try {
      const params = {
        page: recordsPage.value,
        page_size: recordsPageSize.value,
      }
      if (recordsDateRange.value && recordsDateRange.value.length === 2) {
        const [a, b] = recordsDateRange.value
        params.date_from = typeof a === 'string' ? a : formatDateParam(a)
        params.date_to = typeof b === 'string' ? b : formatDateParam(b)
      }
      if (recordsFilename.value.trim()) params.filename = recordsFilename.value.trim()
      const { data } = await http.get('/api/jobs', { params })
      records.value = data.jobs || []
      recordsTotal.value = data.total ?? 0
    } catch {
      records.value = []
      recordsTotal.value = 0
    } finally {
      recordsLoading.value = false
    }
  }

  async function confirmDeleteJob(row) {
    try {
      await ElMessageBox.confirm(
        `确定删除任务「${row.original_filename || row.job_id}」吗？将删除数据库记录与输出目录，不可恢复。`,
        '确认删除',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    deletingJobId.value = row.job_id
    try {
      await http.delete(`/api/jobs/${encodeURIComponent(row.job_id)}`)
      ElMessage.success('已删除')
      await loadRecords()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '删除失败')
    } finally {
      deletingJobId.value = null
    }
  }

  async function confirmBatchDeleteJobs() {
    const rows = recordsSelection.value.filter((r) => r.status !== 'processing')
    if (!rows.length) {
      ElMessage.warning('请选择可删除的任务（进行中的任务不可选，需先停止）')
      return
    }
    try {
      await ElMessageBox.confirm(
        `确定批量删除 ${rows.length} 条任务吗？将删除数据库记录与对应输出目录，不可恢复。进行中的任务已自动排除。`,
        '批量删除',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    batchDeleting.value = true
    try {
      const { data } = await http.post('/api/jobs/batch-delete', {
        job_ids: rows.map((r) => r.job_id),
      })
      const n = (data.deleted && data.deleted.length) || 0
      const failed = data.failed || []
      if (failed.length) {
        ElMessage.warning(`已删除 ${n} 条；${failed.length} 条未删除（可能进行中或无权）`)
      } else {
        ElMessage.success(`已删除 ${n} 条`)
      }
      clearRecordsSelection()
      await loadRecords()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '批量删除失败')
    } finally {
      batchDeleting.value = false
    }
  }

  async function handleBatchDownload() {
    const rows = recordsSelection.value.filter((r) => r.status === 'completed' && !r.cache_cleared && r.can_download)
    if (!rows.length) {
      ElMessage.warning('请选择已完成且缓存未清除的任务')
      return
    }

    batchDownloading.value = true
    try {
      const response = await http.post('/api/jobs/batch-download', { job_ids: rows.map((r) => r.job_id) }, { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'application/zip' })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      link.download = `DocuLogic_批量下载_${timestamp}.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      ElMessage.success(`已开始下载 ${rows.length} 个任务的解析结果`)
    } catch (e) {
      console.error('批量下载失败:', e)
      const errorMsg = await axiosErrorDetail(e, '批量下载失败')
      ElMessage.error(errorMsg)
    } finally {
      batchDownloading.value = false
    }
  }

  async function confirmRecoverStaleJobs() {
    try {
      await ElMessageBox.confirm(
        `将检测并恢复所有超过 ${staleJobTimeoutMinutesRef.value} 分钟仍处于“进行中”状态的僵尸任务。这些任务将被标记为“失败”，并清理对应的磁盘文件。是否继续？`,
        '恢复僵尸任务',
        { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
      )
    } catch {
      return
    }

    recoveringStaleJobs.value = true
    try {
      const { data } = await http.post('/api/admin/recover-stale-jobs', {
        max_stale_minutes: staleJobTimeoutMinutesRef.value,
      })
      ElMessage.success(data.message || `已恢复 ${data.recovered_count} 个僵尸任务`)
      await loadRecords()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '恢复失败')
    } finally {
      recoveringStaleJobs.value = false
    }
  }

  return {
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
  }
}
