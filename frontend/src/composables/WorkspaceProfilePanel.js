import { reactive, ref } from 'vue'

/**
 * useProfileActions
 * - 用途：封装个人中心相关动作（密码修改、资料刷新）
 * - 输入参数：
 *   - http: Axios 实例
 *   - ElMessage: Element Plus 消息组件
 *   - userProfile: 父层维护的个人资料响应式对象
 * - 返回值：
 *   - 状态：pw, pwErr, pwOk, pwLoading
 *   - 动作：changePassword, refreshProfile
 */
export function useWorkspaceProfilePanel({ http, ElMessage, userProfile }) {
  const pw = reactive({ old: '', n1: '', n2: '' })
  const pwErr = ref('')
  const pwOk = ref(false)
  const pwLoading = ref(false)

  async function changePassword() {
    pwErr.value = ''
    pwOk.value = false
    if (pw.n1.length < 8) {
      pwErr.value = '新密码至少 8 位'
      return
    }
    if (pw.n1 !== pw.n2) {
      pwErr.value = '两次新密码不一致'
      return
    }
    pwLoading.value = true
    try {
      await http.post('/api/auth/change-password', { old_password: pw.old, new_password: pw.n1 })
      pwOk.value = true
      pw.old = ''
      pw.n1 = ''
      pw.n2 = ''
    } catch (e) {
      pwErr.value = e.response?.data?.detail || e.message
    } finally {
      pwLoading.value = false
    }
  }

  async function refreshProfile() {
    try {
      const { data } = await http.get('/api/auth/me')
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
      ElMessage.success('个人信息已刷新')
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '获取用户信息失败')
    }
  }

  return {
    pw,
    pwErr,
    pwOk,
    pwLoading,
    changePassword,
    refreshProfile,
  }
}
