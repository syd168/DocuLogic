<template>
  <div>
    <header class="topbar">
      <router-link class="brand" to="/"><span class="brand-mark">📄</span> DocuLogic</router-link>
      <div class="topbar-actions">
        <router-link class="btn btn-ghost" to="/login">登录</router-link>
      </div>
    </header>
    <main class="main-wrap">
      <div v-if="!forgotEmailAllowed && !forgotPhoneAllowed" class="card auth-card">
        <h1>找回密码</h1>
        <p class="lead">管理员已关闭邮箱与手机号找回，请联系管理员。</p>
        <router-link class="btn btn-primary" to="/login">返回登录</router-link>
      </div>
      <div v-else class="card auth-card">
        <h1>找回密码</h1>
        <p class="lead">{{ forgotLead }}</p>
        <el-alert v-if="err" :title="err" type="error" show-icon class="mb-3" :closable="false" />
        <el-alert v-if="ok" :title="ok" type="success" show-icon class="mb-3" :closable="false" />
        <el-form v-if="showModeSwitch" class="forgot-mode-row" @submit.prevent>
          <el-radio-group v-model="forgotMode" size="small">
            <el-radio-button v-if="forgotEmailAllowed" value="email">邮箱</el-radio-button>
            <el-radio-button v-if="forgotPhoneAllowed" value="phone">手机号</el-radio-button>
          </el-radio-group>
        </el-form>
        <el-form @submit.prevent="resetPwd">
          <label v-if="forgotMode === 'email'" class="field">
            <span>邮箱</span>
            <el-input v-model="form.email" type="email" autocomplete="email" />
          </label>
          <label v-else class="field">
            <span>手机号</span>
            <el-input v-model="form.phone" maxlength="11" inputmode="numeric" autocomplete="tel" placeholder="11 位手机号" />
          </label>
          <CaptchaBox ref="capRef" :enabled="captchaForgot" />
          <div class="btn-row" style="margin-bottom: 14px">
            <el-button :loading="sending" @click="sendCode">发送验证码</el-button>
          </div>
          <label class="field">
            <span>验证码（6 位）</span>
            <el-input v-model="form.code" maxlength="6" inputmode="numeric" />
          </label>
          <label class="field">
            <span>新密码（至少 8 位）</span>
            <el-input v-model="form.newPassword" type="password" show-password />
          </label>
          <div class="form-actions">
            <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%; padding: 12px">
              重置密码
            </el-button>
          </div>
        </el-form>
        <p class="link-muted" style="margin-top: 20px"><router-link to="/login">返回登录</router-link></p>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import CaptchaBox from '@/components/CaptchaBox.vue'

const router = useRouter()
const err = ref('')
const ok = ref('')
const sending = ref(false)
const loading = ref(false)
const captchaForgot = ref(false)
const capRef = ref(null)
const forgotEmailAllowed = ref(true)
const forgotPhoneAllowed = ref(true)
const forgotMode = ref('email')

const showModeSwitch = computed(() => forgotEmailAllowed.value && forgotPhoneAllowed.value)

const forgotLead = computed(() =>
  forgotMode.value === 'email' ? '向注册邮箱发送验证码后设置新密码' : '向绑定手机发送短信验证码后设置新密码',
)

const form = reactive({
  email: '',
  phone: '',
  code: '',
  newPassword: '',
})

watch(forgotMode, () => {
  err.value = ''
  ok.value = ''
})

onMounted(async () => {
  try {
    const { data } = await http.get('/api/settings/public', {
      params: { _: Date.now() },
      headers: { 'Cache-Control': 'no-cache' },
    })
    captchaForgot.value = !!data.captcha_forgot
    forgotEmailAllowed.value = data.forgot_email_allowed !== false
    forgotPhoneAllowed.value = data.forgot_phone_allowed !== false
    if (forgotEmailAllowed.value && !forgotPhoneAllowed.value) forgotMode.value = 'email'
    else if (!forgotEmailAllowed.value && forgotPhoneAllowed.value) forgotMode.value = 'phone'
    else forgotMode.value = 'email'
  } catch {
    /* ignore */
  }
})

async function sendCode() {
  err.value = ''
  ok.value = ''
  if (forgotMode.value === 'email') {
    const email = form.email.trim()
    if (!email) {
      err.value = '请填写邮箱'
      return
    }
    sending.value = true
    try {
      const cap = capRef.value?.getPayload?.() || {}
      const { data } = await http.post('/api/auth/forgot-send-code', {
        email,
        captcha_id: cap.captcha_id,
        captcha_code: cap.captcha_code,
      })
      ok.value = data.email_mock ? '开发模式：请查看服务端控制台验证码' : '若邮箱已注册，将收到验证码'
    } catch (e) {
      err.value = e.response?.data?.detail || e.message
      capRef.value?.refresh?.()
    } finally {
      sending.value = false
    }
    return
  }
  const phone = form.phone.trim()
  if (!phone) {
    err.value = '请填写手机号'
    return
  }
  sending.value = true
  try {
    const cap = capRef.value?.getPayload?.() || {}
    const { data } = await http.post('/api/auth/forgot-send-code', {
      phone,
      captcha_id: cap.captcha_id,
      captcha_code: cap.captcha_code,
    })
    ok.value = data.sms_mock ? '模拟模式：请查看服务端控制台' : '若手机号已注册，将收到短信验证码'
  } catch (e) {
    err.value = e.response?.data?.detail || e.message
    capRef.value?.refresh?.()
  } finally {
    sending.value = false
  }
}

async function resetPwd() {
  err.value = ''
  ok.value = ''
  loading.value = true
  try {
    const body = {
      code: form.code.trim(),
      new_password: form.newPassword,
    }
    if (forgotMode.value === 'email') {
      body.email = form.email.trim()
    } else {
      body.phone = form.phone.trim()
    }
    await http.post('/api/auth/forgot-reset', body)
    ok.value = '密码已重置，请使用新密码登录'
    setTimeout(() => router.replace('/login'), 1500)
  } catch (e) {
    err.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}
.forgot-mode-row {
  margin-bottom: 16px;
}
</style>
