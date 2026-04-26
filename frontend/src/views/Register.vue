<template>
  <div>
    <header class="topbar">
      <router-link class="brand" to="/"><span class="brand-mark">📄</span> DocuLogic</router-link>
      <div class="topbar-actions">
        <router-link class="btn btn-ghost" to="/login">登录</router-link>
      </div>
    </header>
    <main class="main-wrap">
      <div v-if="!registrationEnabled" class="card auth-card">
        <h1>注册已关闭</h1>
        <p class="lead">管理员已关闭新用户注册。</p>
        <router-link class="btn btn-primary" to="/login">返回登录</router-link>
      </div>
      <div v-else-if="!registerEmailAllowed && !registerPhoneAllowed" class="card auth-card">
        <h1>注册已关闭</h1>
        <p class="lead">管理员已关闭邮箱与手机号注册入口。</p>
        <router-link class="btn btn-primary" to="/login">返回登录</router-link>
      </div>
      <div v-else class="card auth-card">
        <h1>注册</h1>
        <p class="lead">{{ registerLead }}</p>
        <el-alert v-if="err" :title="err" type="error" show-icon class="mb-3" :closable="false" />
        <div v-if="ok" class="supported-types" style="border-color: rgba(61, 214, 245, 0.3); color: var(--accent)">
          {{ ok }}
        </div>
        <el-form v-if="showModeSwitch" class="reg-mode-row" @submit.prevent>
          <el-radio-group v-model="registerMode" size="small">
            <el-radio-button v-if="registerEmailAllowed" value="email">邮箱注册</el-radio-button>
            <el-radio-button v-if="registerPhoneAllowed" value="phone">手机号注册</el-radio-button>
          </el-radio-group>
        </el-form>
        <el-form @submit.prevent="submit">
          <template v-if="registerMode === 'email' && registerEmailAllowed">
            <label class="field">
              <span>邮箱</span>
              <div class="code-row">
                <el-input v-model="form.email" type="email" autocomplete="email" />
                <el-button
                  v-if="registerRequiresEmailCode"
                  type="default"
                  :loading="sending"
                  @click="sendCode"
                >
                  获取验证码
                </el-button>
              </div>
            </label>
            <CaptchaBox v-if="captchaRegister && registerRequiresEmailCode" ref="capSendRef" :enabled="true" />
            <label v-if="registerRequiresEmailCode" class="field">
              <span>邮箱验证码（6 位）</span>
              <el-input v-model="form.code" maxlength="6" inputmode="numeric" />
            </label>
          </template>

          <template v-else-if="registerMode === 'phone' && registerPhoneAllowed">
            <label class="field">
              <span>手机号</span>
              <div class="code-row">
                <el-input v-model="form.phone" maxlength="11" inputmode="numeric" autocomplete="tel" placeholder="11 位手机号" />
                <el-button
                  v-if="registerRequiresPhoneCode"
                  type="default"
                  :loading="sending"
                  @click="sendCode"
                >
                  获取验证码
                </el-button>
              </div>
            </label>
            <CaptchaBox v-if="captchaRegister && registerRequiresPhoneCode" ref="capSendRef" :enabled="true" />
            <label v-if="registerRequiresPhoneCode" class="field">
              <span>短信验证码（6 位）</span>
              <el-input v-model="form.code" maxlength="6" inputmode="numeric" />
            </label>
          </template>

          <label class="field">
            <span>用户名（3–32 位，字母数字下划线）</span>
            <el-input v-model="form.username" autocomplete="username" />
          </label>
          <label class="field">
            <span>密码</span>
            <el-input v-model="form.password" type="password" autocomplete="new-password" show-password />
          </label>
          <CaptchaBox v-if="showCaptchaOnSubmit" ref="capSubmitRef" :enabled="true" />
          <div class="form-actions">
            <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%; padding: 12px">
              注册并登录
            </el-button>
          </div>
        </el-form>
        <p class="link-muted" style="margin-top: 20px">已有账号？<router-link to="/login">登录</router-link></p>
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
const loading = ref(false)
const sending = ref(false)
const registrationEnabled = ref(true)
const captchaRegister = ref(false)
const registerRequiresEmailCode = ref(false)
const registerRequiresPhoneCode = ref(false)
const registerEmailAllowed = ref(true)
const registerPhoneAllowed = ref(true)
const registerMode = ref('email')

const capSendRef = ref(null)
const capSubmitRef = ref(null)

const showModeSwitch = computed(() => registerEmailAllowed.value && registerPhoneAllowed.value)

const showCaptchaOnSubmit = computed(() => {
  if (!captchaRegister.value) return false
  if (registerMode.value === 'email') {
    return registerEmailAllowed.value && !registerRequiresEmailCode.value
  }
  return registerPhoneAllowed.value && !registerRequiresPhoneCode.value
})

const registerLead = computed(() => {
  if (registerMode.value === 'phone') {
    return registerRequiresPhoneCode.value
      ? '手机验证码 + 用户名 + 密码（至少 8 位）'
      : '手机号 + 用户名 + 密码（至少 8 位），无需短信验证码'
  }
  return registerRequiresEmailCode.value
    ? '邮箱验证码 + 用户名 + 密码（至少 8 位）'
    : '邮箱 + 用户名 + 密码（至少 8 位），无需邮箱验证码'
})

const form = reactive({
  email: '',
  phone: '',
  code: '',
  username: '',
  password: '',
})

watch(registerMode, () => {
  form.code = ''
  err.value = ''
  ok.value = ''
})

onMounted(async () => {
  try {
    const { data } = await http.get('/api/settings/public', {
      params: { _: Date.now() },
      headers: { 'Cache-Control': 'no-cache' },
    })
    registrationEnabled.value = data.registration_enabled !== false
    captchaRegister.value = !!data.captcha_register
    registerEmailAllowed.value = data.register_email_allowed !== false
    registerPhoneAllowed.value = data.register_phone_allowed !== false
    if (typeof data.register_requires_email_code === 'boolean') {
      registerRequiresEmailCode.value = data.register_requires_email_code
    }
    if (typeof data.register_requires_phone_code === 'boolean') {
      registerRequiresPhoneCode.value = data.register_requires_phone_code
    }
    if (registerEmailAllowed.value && !registerPhoneAllowed.value) {
      registerMode.value = 'email'
    } else if (!registerEmailAllowed.value && registerPhoneAllowed.value) {
      registerMode.value = 'phone'
    } else {
      registerMode.value = 'email'
    }
  } catch {
    /* ignore */
  }
})

async function sendCode() {
  err.value = ''
  ok.value = ''
  if (registerMode.value === 'email') {
    if (!registerRequiresEmailCode.value) return
    const email = form.email.trim()
    if (!email) {
      err.value = '请先填写邮箱'
      return
    }
    sending.value = true
    try {
      const cap = capSendRef.value?.getPayload?.() || {}
      const { data } = await http.post('/api/auth/send-code', {
        email,
        captcha_id: cap.captcha_id,
        captcha_code: cap.captcha_code,
      })
      ok.value = data.email_mock
        ? '验证码已请求（开发模式：请查看服务端控制台日志中的验证码）'
        : '验证码已发送到邮箱，请查收'
    } catch (e) {
      setErr(e)
      capSendRef.value?.refresh?.()
    } finally {
      sending.value = false
    }
    return
  }

  if (!registerRequiresPhoneCode.value) return
  const phone = form.phone.trim()
  if (!phone) {
    err.value = '请先填写手机号'
    return
  }
  sending.value = true
  try {
    const cap = capSendRef.value?.getPayload?.() || {}
    const { data } = await http.post('/api/auth/send-code', {
      phone,
      captcha_id: cap.captcha_id,
      captcha_code: cap.captcha_code,
    })
    ok.value = data.sms_mock
      ? '验证码已请求（模拟模式：请查看服务端控制台日志）'
      : '验证码已发送，请查收短信'
  } catch (e) {
    setErr(e)
    capSendRef.value?.refresh?.()
  } finally {
    sending.value = false
  }
}

function setErr(e) {
  const detail = e.response?.data?.detail
  err.value =
    typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map((x) => x.msg || x).join('；')
        : JSON.stringify(detail || e.message)
}

async function submit() {
  err.value = ''
  ok.value = ''
  loading.value = true
  try {
    const payload = {
      username: form.username.trim(),
      password: form.password,
    }
    if (registerMode.value === 'email') {
      payload.email = form.email.trim()
      if (registerRequiresEmailCode.value) {
        payload.code = form.code.trim()
      } else if (captchaRegister.value) {
        const cap = capSubmitRef.value?.getPayload?.() || {}
        payload.captcha_id = cap.captcha_id
        payload.captcha_code = cap.captcha_code
      }
    } else {
      payload.phone = form.phone.trim()
      if (registerRequiresPhoneCode.value) {
        payload.code = form.code.trim()
      } else if (captchaRegister.value) {
        const cap = capSubmitRef.value?.getPayload?.() || {}
        payload.captcha_id = cap.captcha_id
        payload.captcha_code = cap.captcha_code
      }
    }
    await http.post('/api/auth/register', payload)
    router.replace('/app')
  } catch (e) {
    setErr(e)
    capSubmitRef.value?.refresh?.()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mb-3 {
  margin-bottom: 12px;
}
.reg-mode-row {
  margin-bottom: 16px;
}
</style>
