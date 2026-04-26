/**
 * HTTP 客户端配置
 * 
 * 基于 Axios 封装，提供：
 * - 统一的 baseURL 配置
 * - Cookie 认证支持（withCredentials）
 * - 120秒超时设置
 * - 401 未授权自动跳转登录页
 * - Token 自动刷新机制
 */
import axios from 'axios'

// API 基础路径，从环境变量读取
const baseURL = import.meta.env.VITE_API_BASE || ''

/**
 * 创建 Axios 实例
 * 
 * 配置说明：
 * - baseURL: API 服务器地址
 * - withCredentials: 允许携带 Cookie（用于 JWT 认证）
 * - timeout: 请求超时时间（120秒，适应长时间解析任务）
 */
const http = axios.create({
  baseURL,
  withCredentials: true,  // 允许跨域请求携带 Cookie
  timeout: 120000,  // 120 秒超时
})

// Token 刷新状态标记，防止并发刷新
let isRefreshing = false
let refreshSubscribers = []

/**
 * 将等待的请求添加到队列
 */
function addRefreshSubscriber(callback) {
  refreshSubscribers.push(callback)
}

/**
 * 执行所有等待的请求
 */
function onRefreshed() {
  refreshSubscribers.forEach(callback => callback())
  refreshSubscribers = []
}

/**
 * 刷新 Token
 * 
 * 调用后端 /api/auth/refresh-token 接口
 * 如果 token 剩余时间 < 60分钟，则自动续期
 */
async function refreshToken() {
  try {
    const response = await axios.post(
      `${baseURL}/api/auth/refresh-token`,
      {},
      { withCredentials: true }
    )
    console.log('[Token刷新]', response.data.message)
    return true
  } catch (error) {
    console.error('[Token刷新失败]', error.message)
    return false
  }
}

/**
 * 响应拦截器
 * 
 * 功能：
 * - 检测 401 未授权错误
 * - 区分 Token 过期和被踢下线
 * - 显示友好提示后跳转到登录页
 */
http.interceptors.response.use(
  response => response,  // 成功响应直接返回
  async error => {
    const originalRequest = error.config
    
    // 处理 401 未授权错误
    if (error.response && error.response.status === 401) {
      // 检查当前页面是否需要认证
      const needsAuth = [
        '/app',
        '/workspace',
      ].some(path => window.location.pathname.startsWith(path))
      
      // 只有在需要认证的页面才跳转
      if (needsAuth && !window.location.pathname.includes('/login')) {
        // 尝试从错误信息中判断是否是被踢下线
        const errorMsg = error.response?.data?.detail || ''
        console.log('[401错误] 错误信息:', errorMsg)
        
        // 检测是否被踢下线（单点登录冲突或 Token 被撤销）
        const isKickedOut = (
          errorMsg.includes('其他终端') ||
          errorMsg.includes('已被撤销') ||
          errorMsg.includes('single_login') ||
          errorMsg.includes('blacklist')
        )
        
        console.log('[401错误] 是否被踢下线:', isKickedOut)
        
        // 保存跳转前的路径
        const nextPath = encodeURIComponent(window.location.pathname)
        
        if (isKickedOut) {
          // 被踢下线，显示提示（使用 confirm 让用户有机会点击确定）
          const confirmed = confirm(
            '⚠️ 账号安全提示\n\n' +
            '您的账号已在其他设备登录，当前会话已被强制下线。\n\n' +
            '如非本人操作，请立即修改密码！'
          )
          
          // 无论用户是否点击确定，都跳转到登录页
          window.location.href = '/login?next=' + nextPath
          return Promise.reject(error)
        }
        
        // 普通 401（Token 过期等），直接跳转
        window.location.href = '/login?next=' + nextPath
      }
      // 否则静默失败，由调用方处理（如 Landing 页面的 /api/auth/me）
    }
    
    return Promise.reject(error)  // 抛出错误，供调用方捕获
  }
)

/**
 * 定期刷新 Token
 * 
 * 每 30 分钟检查一次，如果 token 即将过期则自动刷新
 * 这样可以保证用户在活跃使用时不会突然被登出
 */
let refreshTimer = null

export function startTokenRefresh() {
  // 清除旧的定时器
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }

  // 启动后先立即尝试一次，防止页面刚恢复时 token 已接近过期
  refreshToken().catch(() => {})

  // 改为更短周期（5 分钟）检查，覆盖默认 10 分钟登录超时场景
  refreshTimer = setInterval(async () => {
    try {
      await refreshToken()
    } catch (err) {
      console.error('[定期Token刷新] 异常:', err)
    }
  }, 5 * 60 * 1000)  // 5 分钟

  console.log('[Token刷新] 已启动定期刷新机制（每5分钟）')
}

export function stopTokenRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
    console.log('[Token刷新] 已停止')
  }
}

export default http
