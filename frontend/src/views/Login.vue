<template>
  <div>
    <header class="topbar">
      <router-link class="brand" to="/"><span class="brand-mark">📄</span> DocuLogic</router-link>
      <div class="topbar-actions">
        <router-link v-if="registrationEnabled" class="btn btn-ghost" to="/register">注册</router-link>
      </div>
    </header>
    <main class="main-wrap">
      <div class="card auth-card">
        <h1>登录</h1>
        <p class="lead">使用用户名、邮箱或手机号与密码登录</p>
        <el-alert v-if="err" :title="err" type="error" show-icon class="mb-3" :closable="false" />
        <el-form @submit.prevent="submit" name="loginForm">
          <label class="field">
            <span>用户名 / 邮箱 / 手机号</span>
            <el-input 
              v-model="form.username" 
              name="username"
              autocomplete="username" 
              placeholder="用户名、邮箱或 11 位手机号" 
            />
          </label>
          <label class="field">
            <span>密码</span>
            <el-input 
              v-model="form.password" 
              name="password"
              type="password" 
              autocomplete="current-password" 
              show-password 
            />
          </label>
          <CaptchaBox ref="capRef" :enabled="captchaLogin" />
          <div class="form-actions">
            <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%; padding: 12px">
              登录
            </el-button>
          </div>
        </el-form>
        <p class="link-muted" style="margin-top: 20px">
          <router-link to="/forgot">忘记密码</router-link>
          <span v-if="registrationEnabled"> · 没有账号？<router-link to="/register">注册</router-link></span>
        </p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/http'
import { startTokenRefresh } from '@/api/http'
import CaptchaBox from '@/components/CaptchaBox.vue'

const route = useRoute()
const router = useRouter()
const err = ref('')
const loading = ref(false)
const capRef = ref(null)
const registrationEnabled = ref(true)
const captchaLogin = ref(false)

const form = reactive({
  username: '',
  password: '',
})

async function loadPublicSettings() {
  try {
    const { data } = await http.get('/api/settings/public', {
      params: { _: Date.now() },
      headers: { 'Cache-Control': 'no-cache' },
    })
    registrationEnabled.value = data.registration_enabled !== false
    captchaLogin.value = !!data.captcha_login
  } catch {
    /* ignore */
  }
}

onMounted(() => {
  loadPublicSettings()
})

async function submit() {
  err.value = ''
  loading.value = true
  try {
    const cap = capRef.value?.getPayload?.() || {}
    await http.post('/api/auth/login', {
      username: form.username.trim(),
      password: form.password,
      captcha_id: cap.captcha_id,
      captcha_code: cap.captcha_code,
    })
    
    // 登录成功后启动 Token 自动刷新机制
    startTokenRefresh()
    console.log('[登录] Token 刷新机制已启动')
    
    const next = typeof route.query.next === 'string' ? route.query.next : '/app'
    router.replace(next || '/app')
  } catch (e) {
    err.value = e.response?.data?.detail || e.message || '登录失败'
    capRef.value?.refresh?.()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}
</style>
