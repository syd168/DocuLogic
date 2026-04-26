<template>
  <el-dialog
    :model-value="modelValue"
    title="用户会话信息"
    width="600px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div v-if="sessionLoading" class="text-center py-4">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p class="mt-2">加载中...</p>
    </div>
    <div v-else-if="!sessionData.has_session" class="text-center py-4">
      <el-icon :size="48" color="#909399"><CircleClose /></el-icon>
      <p class="mt-2 muted">该用户当前没有活跃会话</p>
    </div>
    <div v-else>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">
          {{ sessionData.session.username }}
        </el-descriptions-item>
        <el-descriptions-item label="登录 IP">
          {{ sessionData.session.ip_address || '未知' }}
        </el-descriptions-item>
        <el-descriptions-item label="浏览器">
          <span style="font-size: 12px; word-break: break-all;">
            {{ sessionData.session.user_agent || '未知' }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="登录时间">
          {{ fmtTime(sessionData.session.login_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="最后活跃">
          {{ fmtTime(sessionData.session.last_active) }}
        </el-descriptions-item>
      </el-descriptions>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        class="mt-3"
        title="提示：踢出用户后，该用户的 Token 将立即失效，需要重新登录。"
      />
    </div>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">关闭</el-button>
      <el-button
        v-if="sessionData.has_session && sessionUserId !== currentUserId"
        type="danger"
        :loading="kickingUser"
        @click="$emit('kick-user')"
      >
        踢出该用户
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { Loading, CircleClose } from '@element-plus/icons-vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  sessionLoading: { type: Boolean, default: false },
  sessionData: { type: Object, required: true },
  sessionUserId: { type: [Number, String, null], default: null },
  currentUserId: { type: [Number, String, null], default: null },
  kickingUser: { type: Boolean, default: false },
  fmtTime: { type: Function, required: true },
})

defineEmits(['update:modelValue', 'kick-user'])
</script>
