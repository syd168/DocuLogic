<template>
  <div v-if="enabled" class="captcha-box">
    <span class="field-label">图形验证码</span>
    <div class="captcha-row">
      <div class="captcha-svg" v-html="svg" />
      <el-input v-model="code" placeholder="输入图中字符" maxlength="8" style="flex: 1" />
      <el-button @click="refresh">刷新</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import http from '@/api/http'

const props = defineProps({
  enabled: { type: Boolean, default: false },
})
const captchaId = ref('')
const svg = ref('')
const code = ref('')

async function refresh() {
  if (!props.enabled) return
  try {
    const { data } = await http.get('/api/captcha/new')
    captchaId.value = data.captcha_id
    svg.value = data.svg || ''
    code.value = ''
  } catch {
    svg.value = ''
  }
}

watch(
  () => props.enabled,
  (v) => {
    if (v) refresh()
    else {
      captchaId.value = ''
      svg.value = ''
      code.value = ''
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.enabled) refresh()
})

function getPayload() {
  return { captcha_id: captchaId.value, captcha_code: code.value }
}

defineExpose({ refresh, getPayload })
</script>

<style scoped>
.captcha-box {
  margin-bottom: 14px;
}
.field-label {
  display: block;
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.captcha-svg {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  height: 44px;
  background: #0c1222;
}
.captcha-svg :deep(svg) {
  display: block;
  height: 44px;
  width: auto;
}
</style>
