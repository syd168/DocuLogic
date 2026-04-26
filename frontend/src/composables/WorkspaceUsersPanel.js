import { reactive, ref } from 'vue'

/**
 * useUserManagement
 * - 用途：管理用户页业务（列表、筛选、批量操作、编辑/创建用户、会话查看与踢出）
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - ElMessageBox: Element Plus 确认框
 *   - isAdmin: 当前用户是否管理员
 *   - username: 当前用户名
 *   - currentUserId: 当前用户 ID
 *   - settingsSummary: 设置摘要（用于展示回退值）
 * - 返回值：
 *   - 状态：users 列表/分页/弹窗/会话等响应式对象
 *   - 动作：load/search/batch/edit/create/session/kick 等方法
 */
export function useWorkspaceUsersPanel({
  http,
  ElMessage,
  ElMessageBox,
  isAdmin,
  username,
  currentUserId,
  settingsSummary,
}) {
  const usersPanelRef = ref(null)
  const usersSelection = ref([])
  const usersBatchLoading = ref(false)
  const batchPdfDialogVisible = ref(false)
  const batchPdfUseDefault = ref(true)
  const batchPdfPages = ref(80)

  const usersList = ref([])
  const usersPdfGlobalCap = ref(80)
  const usersLoading = ref(false)
  const userPage = ref(1)
  const userPageSize = ref(20)
  const userTotal = ref(0)
  const userSearchQ = ref('')

  const userEditVisible = ref(false)
  const userSaveLoading = ref(false)
  const userEditForm = reactive({
    id: null,
    username: '',
    email: '',
    phone: '',
    is_admin: false,
    is_active: true,
    is_self: false,
    is_target_other_admin: false,
    new_password: '',
    pdf_max_pages: 80,
    pdf_use_default: true,
    image_output_mode: null,
    image_output_use_default: true,
  })

  const sessionDialogVisible = ref(false)
  const sessionLoading = ref(false)
  const sessionData = reactive({
    has_session: false,
    session: null,
  })
  const sessionUserId = ref(null)
  const kickingUser = ref(false)

  const createUserVisible = ref(false)
  const createUserLoading = ref(false)
  const createUserDialogRef = ref(null)
  const createUserForm = reactive({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    is_admin: false,
    is_active: true,
    pdf_max_pages: 80,
    pdf_use_default: true,
    image_output_mode: null,
    image_output_use_default: true,
  })

  const validatePass2 = (rule, value, callback) => {
    if (value === '') {
      callback(new Error('请再次输入密码'))
    } else if (value !== createUserForm.password) {
      callback(new Error('两次输入密码不一致!'))
    } else {
      callback()
    }
  }

  const createUserRules = {
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' },
      { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' },
    ],
    email: [
      { required: true, message: '请输入邮箱地址', trigger: 'blur' },
      { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] },
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 8, message: '密码至少 8 位', trigger: 'blur' },
    ],
    confirmPassword: [{ required: true, validator: validatePass2, trigger: 'blur' }],
  }

  function usersRowSelectable(row) {
    return !row.is_admin
  }

  function clearUsersSelection() {
    usersSelection.value = []
    usersPanelRef.value?.clearSelection?.()
  }

  function searchUsers() {
    userPage.value = 1
    clearUsersSelection()
    loadUsers()
  }

  function userPdfEffectiveDisplay(row) {
    const eff = row.pdf_effective_max_pages
    if (eff != null && eff !== '') return Math.max(1, Number(eff))
    const g = usersPdfGlobalCap.value
    if (g != null && g !== '') return Math.max(1, Number(g))
    const fb = settingsSummary.pdf_max_pages_global ?? settingsSummary.pdf_max_pages
    return Math.max(1, Number(fb) || 80)
  }

  async function loadUsers() {
    if (!isAdmin.value) return
    usersLoading.value = true
    try {
      const [usersRes, onlineRes] = await Promise.all([
        http.get('/api/admin/users', {
          params: {
            page: userPage.value,
            page_size: userPageSize.value,
            q: userSearchQ.value.trim() || undefined,
          },
        }),
        http.get('/api/admin/sessions/online-users').catch(() => ({ data: { users: [] } })),
      ])

      const usersListRaw = usersRes.data.users || []
      const onlineUsers = onlineRes.data.users || []
      const onlineUserIds = new Set(onlineUsers.map((u) => u.user_id))

      usersList.value = usersListRaw.map((user) => ({
        ...user,
        has_session: onlineUserIds.has(user.id),
      }))

      userTotal.value = usersRes.data.total ?? 0
      if (usersRes.data.pdf_max_pages_global != null && usersRes.data.pdf_max_pages_global !== '') {
        usersPdfGlobalCap.value = Math.max(1, Number(usersRes.data.pdf_max_pages_global))
      }
    } catch {
      usersList.value = []
      userTotal.value = 0
    } finally {
      usersLoading.value = false
    }
  }

  function openUserEdit(row) {
    if (row.is_admin && row.username !== username.value) {
      ElMessage.warning('不能编辑其他管理员账号')
      return
    }

    userEditForm.id = row.id
    userEditForm.username = row.username
    userEditForm.email = row.email
    userEditForm.phone = row.phone || ''
    userEditForm.is_admin = !!row.is_admin
    userEditForm.is_active = !!row.is_active
    userEditForm.new_password = ''
    userEditForm.is_self = row.username === username.value
    userEditForm.is_target_other_admin = false
    userEditForm.pdf_use_default = row.pdf_max_pages == null
    userEditForm.pdf_max_pages = row.pdf_max_pages != null ? row.pdf_max_pages : 80
    userEditForm.image_output_use_default = row.image_output_mode == null
    userEditForm.image_output_mode = row.image_output_mode || 'base64'
    userEditVisible.value = true
  }

  function resetUserEditForm() {
    userEditForm.new_password = ''
    userEditForm.pdf_max_pages = 80
    userEditForm.pdf_use_default = true
    userEditForm.image_output_mode = 'base64'
    userEditForm.image_output_use_default = true
  }

  async function submitUserEdit() {
    if (userEditForm.new_password && userEditForm.new_password.length < 8) {
      ElMessage.warning('新密码至少 8 位')
      return
    }
    userSaveLoading.value = true
    try {
      const body = {
        is_admin: userEditForm.is_admin,
        is_active: userEditForm.is_active,
        pdf_max_pages: userEditForm.pdf_use_default ? null : userEditForm.pdf_max_pages,
        image_output_mode: userEditForm.image_output_use_default ? null : userEditForm.image_output_mode,
      }
      if (userEditForm.new_password) body.new_password = userEditForm.new_password
      await http.patch(`/api/admin/users/${userEditForm.id}`, body)
      ElMessage.success('已保存')
      userEditVisible.value = false
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message)
    } finally {
      userSaveLoading.value = false
    }
  }

  async function viewUserSession(row) {
    sessionUserId.value = row.id
    sessionDialogVisible.value = true
    sessionLoading.value = true
    sessionData.has_session = false
    sessionData.session = null

    try {
      const { data } = await http.get(`/api/admin/users/${row.id}/session`)
      sessionData.has_session = data.has_session
      sessionData.session = data.session || null
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '获取会话信息失败')
      sessionData.has_session = false
    } finally {
      sessionLoading.value = false
    }
  }

  async function doKickUser(userId, targetUsername) {
    kickingUser.value = true
    try {
      const { data } = await http.post(`/api/admin/users/${userId}/kick`)
      ElMessage.success(data.message || `已踢出用户 ${targetUsername}`)
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '踢出用户失败')
    } finally {
      kickingUser.value = false
    }
  }

  async function kickUserConfirm(row) {
    try {
      await ElMessageBox.confirm(
        `确定要踢出用户「${row.username}」吗？\n\n该用户的 Token 将立即失效，需要重新登录。`,
        '踢出用户',
        { type: 'warning', confirmButtonText: '确定踢出', cancelButtonText: '取消' }
      )
      await doKickUser(row.id, row.username)
    } catch {
      // ignore cancel
    }
  }

  async function confirmKickUser() {
    if (!sessionData.session) return
    try {
      await ElMessageBox.confirm(
        `确定要踢出用户「${sessionData.session.username}」吗？\n\n该用户的 Token 将立即失效，需要重新登录。`,
        '踢出用户',
        { type: 'warning', confirmButtonText: '确定踢出', cancelButtonText: '取消' }
      )
      await doKickUser(sessionUserId.value, sessionData.session.username)
      sessionDialogVisible.value = false
    } catch {
      // ignore cancel
    }
  }

  function openCreateUserDialog() {
    createUserVisible.value = true
  }

  function resetCreateUserForm() {
    createUserForm.username = ''
    createUserForm.email = ''
    createUserForm.password = ''
    createUserForm.confirmPassword = ''
    createUserForm.is_admin = false
    createUserForm.is_active = true
    createUserForm.pdf_max_pages = 80
    createUserForm.pdf_use_default = true
    createUserForm.image_output_mode = 'base64'
    createUserForm.image_output_use_default = true
    createUserDialogRef.value?.clearValidate?.()
  }

  async function submitCreateUser() {
    if (!createUserDialogRef.value) return
    try {
      await createUserDialogRef.value.validate()
    } catch {
      return
    }
    if (createUserForm.password !== createUserForm.confirmPassword) {
      ElMessage.error('两次输入密码不一致')
      return
    }

    createUserLoading.value = true
    try {
      const body = {
        username: createUserForm.username.trim(),
        email: createUserForm.email.trim().toLowerCase(),
        password: createUserForm.password,
        is_admin: createUserForm.is_admin,
        is_active: createUserForm.is_active,
        pdf_max_pages: createUserForm.pdf_use_default ? null : createUserForm.pdf_max_pages,
        image_output_mode: createUserForm.image_output_use_default ? null : createUserForm.image_output_mode,
      }

      const { data } = await http.post('/api/admin/users/create', body)
      ElMessage.success(data.message || '用户创建成功')
      createUserVisible.value = false
      await loadUsers()
    } catch (e) {
      const errorMsg = e.response?.data?.detail || e.message || '创建失败'
      ElMessage.error(errorMsg)
    } finally {
      createUserLoading.value = false
    }
  }

  async function batchUsersActive(isActive) {
    const rows = usersSelection.value
    if (!rows.length) return
    const verb = isActive ? '启用' : '禁用'
    try {
      await ElMessageBox.confirm(
        `确定将选中的 ${rows.length} 个账号批量${verb}吗？`,
        `批量${verb}`,
        { type: isActive ? 'info' : 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    usersBatchLoading.value = true
    try {
      const { data } = await http.post('/api/admin/users/batch', {
        user_ids: rows.map((r) => r.id),
        is_active: isActive,
      })
      const ok = (data.updated && data.updated.length) || 0
      const failed = data.failed || []
      if (failed.length) {
        const sample = failed
          .slice(0, 3)
          .map((f) => `#${f.id}: ${f.detail}`)
          .join('；')
        ElMessage.warning(`已${verb} ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`)
      } else {
        ElMessage.success(`已${verb} ${ok} 个账号`)
      }
      clearUsersSelection()
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '批量操作失败')
    } finally {
      usersBatchLoading.value = false
    }
  }

  async function batchUsersAdmin(isAdminFlag) {
    const rows = usersSelection.value
    if (!rows.length) return
    const verb = isAdminFlag ? '设为管理员' : '取消管理员'
    try {
      await ElMessageBox.confirm(
        `确定将选中的 ${rows.length} 个账号批量${verb}吗？`,
        `批量${verb}`,
        { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    usersBatchLoading.value = true
    try {
      const { data } = await http.post('/api/admin/users/batch', {
        user_ids: rows.map((r) => r.id),
        is_admin: isAdminFlag,
      })
      const ok = (data.updated && data.updated.length) || 0
      const failed = data.failed || []
      if (failed.length) {
        const sample = failed
          .slice(0, 3)
          .map((f) => `#${f.id}: ${f.detail}`)
          .join('；')
        ElMessage.warning(`已${verb} ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`)
      } else {
        ElMessage.success(`已${verb} ${ok} 个账号`)
      }
      clearUsersSelection()
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '批量操作失败')
    } finally {
      usersBatchLoading.value = false
    }
  }

  async function openBatchPdfDialog() {
    const rows = usersSelection.value
    if (!rows.length) return
    try {
      await ElMessageBox.confirm(
        `您即将批量设置「单个文件最大解析页数」，将作用于已勾选的 ${rows.length} 个用户（不含管理员）。请确认用户列表无误；误操作将影响用户解析配额。`,
        '操作警告',
        { type: 'warning', confirmButtonText: '已了解，继续', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    batchPdfUseDefault.value = true
    batchPdfPages.value = 80
    batchPdfDialogVisible.value = true
  }

  async function submitBatchPdf() {
    const rows = usersSelection.value
    if (!rows.length) return
    if (!batchPdfUseDefault.value && (!batchPdfPages.value || batchPdfPages.value < 1)) {
      ElMessage.warning('请填写有效的页数（≥1）或改为「与系统全局一致」')
      return
    }
    const desc = batchPdfUseDefault.value ? '与系统全局一致（清除个人上限）' : `个人上限 ${batchPdfPages.value} 页`
    try {
      await ElMessageBox.confirm(`确认为 ${rows.length} 个用户批量设置：${desc}？提交后立即生效。`, '确认提交', {
        type: 'warning',
        confirmButtonText: '确认设置',
        cancelButtonText: '取消',
      })
    } catch {
      return
    }
    usersBatchLoading.value = true
    try {
      const { data } = await http.post('/api/admin/users/batch-pdf-pages', {
        user_ids: rows.map((r) => r.id),
        pdf_max_pages: batchPdfUseDefault.value ? null : batchPdfPages.value,
      })
      const ok = (data.updated && data.updated.length) || 0
      const failed = data.failed || []
      if (failed.length) {
        const sample = failed
          .slice(0, 3)
          .map((f) => `#${f.id}: ${f.detail}`)
          .join('；')
        ElMessage.warning(`已更新 ${ok} 个；${failed.length} 个未变更${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`)
      } else {
        ElMessage.success(`已更新 ${ok} 个用户的解析页数设置`)
      }
      batchPdfDialogVisible.value = false
      clearUsersSelection()
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '批量设置失败')
    } finally {
      usersBatchLoading.value = false
    }
  }

  async function batchUsersDelete() {
    const rows = usersSelection.value
    if (!rows.length) {
      ElMessage.warning('请先勾选要删除的用户')
      return
    }
    const list = rows.map((r) => r.username)
    const nameLine = list.length <= 12 ? list.join('、') : `${list.slice(0, 12).join('、')}…（共 ${rows.length} 人）`
    try {
      await ElMessageBox.confirm(
        `将永久删除以下用户账号，并删除其全部解析任务记录（数据库与关联数据），不可恢复。\n\n${nameLine}`,
        '确认删除用户',
        {
          type: 'error',
          confirmButtonText: '我确认删除',
          cancelButtonText: '取消',
          distinguishCancelAndClose: true,
        }
      )
    } catch {
      return
    }
    usersBatchLoading.value = true
    try {
      const { data } = await http.post('/api/admin/users/batch-delete', {
        user_ids: rows.map((r) => r.id),
      })
      const ok = (data.deleted && data.deleted.length) || 0
      const failed = data.failed || []
      if (failed.length) {
        const sample = failed
          .slice(0, 3)
          .map((f) => `#${f.id}: ${f.detail}`)
          .join('；')
        ElMessage.warning(`已删除 ${ok} 个；${failed.length} 个未删除${sample ? `（${sample}${failed.length > 3 ? '…' : ''}）` : ''}`)
      } else {
        ElMessage.success(`已删除 ${ok} 个用户`)
      }
      clearUsersSelection()
      await loadUsers()
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || e.message || '批量删除失败')
    } finally {
      usersBatchLoading.value = false
    }
  }

  return {
    usersPanelRef,
    usersSelection,
    usersBatchLoading,
    batchPdfDialogVisible,
    batchPdfUseDefault,
    batchPdfPages,
    usersList,
    usersPdfGlobalCap,
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
  }
}
