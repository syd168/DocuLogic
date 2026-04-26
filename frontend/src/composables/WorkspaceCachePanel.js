import { ref } from 'vue'

/**
 * useCacheManagement
 * - 用途：管理缓存清理页的列表、勾选和清理动作
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - ElMessageBox: Element Plus 确认框
 *   - refreshRecords: 清理后刷新记录列表的回调
 * - 返回值：
 *   - 状态：cacheRows, cacheLoading, cacheSelection
 *   - 动作：loadCacheList, clearCache
 */
export function useWorkspaceCachePanel({ http, ElMessage, ElMessageBox, refreshRecords }) {
  const cacheRows = ref([])
  const cacheLoading = ref(false)
  const cacheSelection = ref([])

  async function loadCacheList() {
    cacheLoading.value = true
    cacheSelection.value = []
    try {
      const { data } = await http.get('/api/jobs', { params: { page: 1, page_size: 200 } })
      const jobs = data.jobs || []
      cacheRows.value = jobs.filter((j) => j.clearable)
    } catch {
      cacheRows.value = []
    } finally {
      cacheLoading.value = false
    }
  }

  async function clearCache() {
    const ids = cacheSelection.value.map((r) => r.job_id)
    if (!ids.length) return
    try {
      await ElMessageBox.confirm(`确定删除选中 ${ids.length} 个任务的输出目录？此操作不可恢复。`, '确认', {
        type: 'warning',
      })
    } catch {
      return
    }
    try {
      const { data } = await http.post('/api/jobs/clear-cache', { job_ids: ids })
      await loadCacheList()
      await refreshRecords()
      ElMessage.success(`已清除 ${data.cleared?.length ?? 0} 个任务缓存`)
    } catch (e) {
      if (e !== 'cancel') ElMessage.error(String(e.response?.data?.detail || e.message || e))
    }
  }

  return {
    cacheRows,
    cacheLoading,
    cacheSelection,
    loadCacheList,
    clearCache,
  }
}
