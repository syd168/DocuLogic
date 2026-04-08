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
 * - 自动跳转到登录页，保留原页面路径作为 next 参数
 * - 其他错误直接抛出，由调用方处理
 */
http.interceptors.response.use(
  response => response,  // 成功响应直接返回
  async error => {
    const originalRequest = error.config
    
    // 处理 401 未授权错误
    if (error.response && error.response.status === 401) {
      // 如果不是已经在登录页面，则跳转到登录页
      if (!window.location.pathname.includes('/login')) {
        // 保留当前路径，登录后可以返回
        window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname)
      }
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
  
  // 每 30 分钟检查一次
  refreshTimer = setInterval(async () => {
    try {
      await refreshToken()
    } catch (err) {
      console.error('[定期Token刷新] 异常:', err)
    }
  }, 30 * 60 * 1000)  // 30 分钟
  
  console.log('[Token刷新] 已启动定期刷新机制（每30分钟）')
}

export function stopTokenRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
    console.log('[Token刷新] 已停止')
  }
}

export default http
