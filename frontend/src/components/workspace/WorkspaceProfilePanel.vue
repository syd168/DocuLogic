<template>
  <div class="container card profile-container">
    <div class="page-header">
      <h1>
        <span class="page-icon">👤</span>
        个人中心
      </h1>
    </div>

    <div class="profile-section">
      <h3 class="profile-section-title">📋 基本信息</h3>
      <el-descriptions :column="1" border size="default" class="profile-info">
        <el-descriptions-item label="用户名">
          <strong>{{ userProfile.username }}</strong>
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ userProfile.email || '—' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          {{ userProfile.phone || '未绑定' }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">
          {{ fmtTime(userProfile.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="账号状态">
          <el-tag :type="userProfile.is_active ? 'success' : 'danger'" size="small">
            {{ userProfile.is_active ? '正常' : '已禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="角色权限">
          <el-tag :type="userProfile.is_admin ? 'warning' : 'info'" size="small">
            {{ userProfile.is_admin ? '管理员' : '普通用户' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="profile-section">
      <h3 class="profile-section-title">📊 使用配额</h3>
      <el-descriptions :column="1" border size="default" class="profile-quota">
        <el-descriptions-item label="单个文件最大解析页数">
          <template v-if="userProfile.is_admin">
            <el-tag type="success" size="small">无限制</el-tag>
            <span class="muted" style="margin-left: 8px;">（管理员特权）</span>
          </template>
          <template v-else>
            <strong style="font-size: 1.1em; color: var(--accent);">{{ userProfile.pdf_max_pages_effective }}</strong>
            <span class="muted" style="margin-left: 8px;">页</span>
            <div v-if="!userProfile.pdf_use_default" class="quota-detail muted">
              个人设置：{{ userProfile.pdf_max_pages_personal }} 页 | 系统全局：{{ userProfile.pdf_max_pages_global }} 页
            </div>
            <div v-else class="quota-detail muted">
              使用系统全局默认值：{{ userProfile.pdf_max_pages_global }} 页
            </div>
          </template>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="profile-section">
      <h3 class="profile-section-title">⚙️ 输出配置</h3>
      <el-descriptions :column="1" border size="default" class="profile-config">
        <el-descriptions-item label="图片下载权限">
          <el-tag :type="userProfile.can_download_images ? 'success' : 'info'" size="small">
            {{ userProfile.can_download_images ? '允许' : '禁止' }}
          </el-tag>
          <span class="muted" style="margin-left: 8px;">（仅当输出模式为 separate 时生效）</span>
        </el-descriptions-item>
        <el-descriptions-item label="图片输出模式">
          <template v-if="userProfile.image_output_use_default">
            <el-tag type="info" size="small">跟随系统设置</el-tag>
            <span class="muted" style="margin-left: 8px;">当前系统默认为 base64 嵌入模式</span>
          </template>
          <template v-else>
            <el-tag type="primary" size="small">{{ userProfile.image_output_mode }}</el-tag>
            <div class="quota-detail muted">
              <span v-if="userProfile.image_output_mode === 'base64'">图片以 Base64 编码嵌入 Markdown</span>
              <span v-else-if="userProfile.image_output_mode === 'separate'">图片保存为独立文件</span>
              <span v-else-if="userProfile.image_output_mode === 'none'">不输出图片</span>
            </div>
          </template>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="profile-section">
      <h3 class="profile-section-title">🔧 快捷操作</h3>
      <div class="profile-actions">
        <el-button @click="$emit('navigate', 'records')">查看生成记录</el-button>
        <el-button @click="$emit('navigate', 'cache')">清理缓存</el-button>
        <el-button type="primary" plain @click="$emit('refresh-profile')">🔄 刷新信息</el-button>
      </div>
    </div>

    <div class="profile-section">
      <h3 class="profile-section-title">🔑 密码修改</h3>
      <el-alert v-if="pwErr" :title="pwErr" type="error" :closable="false" style="margin-bottom: 12px" />
      <el-alert v-if="pwOk" title="密码已更新" type="success" :closable="false" style="margin-bottom: 12px" />
      <el-form label-width="120px" size="default">
        <el-form-item label="当前密码">
          <el-input v-model="pw.old" type="password" show-password placeholder="请输入当前密码" style="max-width: 400px" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pw.n1" type="password" show-password placeholder="至少 8 位字符" style="max-width: 400px" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pw.n2" type="password" show-password placeholder="再次输入新密码" style="max-width: 400px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="pwLoading" @click="$emit('change-password')">保存新密码</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
defineProps({
  userProfile: { type: Object, required: true },
  fmtTime: { type: Function, required: true },
  pwErr: { type: String, default: '' },
  pwOk: { type: Boolean, default: false },
  pw: { type: Object, required: true },
  pwLoading: { type: Boolean, default: false },
})

defineEmits(['navigate', 'refresh-profile', 'change-password'])
</script>

<style scoped>
.profile-container {
  max-width: 900px;
  margin: 0 auto;
}

.profile-section {
  margin-bottom: 32px;
  animation: fadeInUp 0.6s ease-out;
}

.profile-section:last-child {
  margin-bottom: 0;
}

.profile-section-title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(99, 102, 241, 0.15);
  display: flex;
  align-items: center;
  gap: 8px;
}

.profile-info :deep(.el-descriptions__label),
.profile-quota :deep(.el-descriptions__label),
.profile-config :deep(.el-descriptions__label) {
  font-weight: 600;
  color: var(--text-muted);
  width: 140px;
}

.profile-info :deep(.el-descriptions__content),
.profile-quota :deep(.el-descriptions__content),
.profile-config :deep(.el-descriptions__content) {
  color: var(--text);
  font-weight: 500;
}

.quota-detail {
  margin-top: 8px;
  font-size: 0.9em;
  line-height: 1.6;
}

.profile-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.profile-actions .el-button {
  min-width: 120px;
  transition: all 0.3s ease;
}

.profile-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
}
</style>
