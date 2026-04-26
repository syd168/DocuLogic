<template>
  <el-dialog
    :model-value="modelValue"
    title="编辑用户"
    width="520px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="$emit('closed')"
  >
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input :model-value="form.username" disabled />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input :model-value="form.email" disabled />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input :model-value="form.phone || '未绑定'" disabled />
      </el-form-item>
      <el-form-item label="管理员">
        <el-switch v-model="form.is_admin" :disabled="form.is_self" />
      </el-form-item>
      <el-form-item label="账号启用">
        <el-switch v-model="form.is_active" :disabled="form.is_self" />
      </el-form-item>
      <el-form-item label="新密码（留空则不修改）">
        <el-input
          v-model="form.new_password"
          type="password"
          show-password
          autocomplete="new-password"
          placeholder="至少 8 位"
        />
      </el-form-item>
      <el-form-item label="单个文件最大解析页数">
        <div class="user-pdf-limit-row">
          <el-checkbox v-model="form.pdf_use_default">与系统全局一致</el-checkbox>
        </div>
        <el-input-number
          v-show="!form.pdf_use_default"
          v-model="form.pdf_max_pages"
          :min="1"
          :max="10000"
          :disabled="form.pdf_use_default"
          controls-position="right"
          style="width: 100%"
        />
        <p v-show="!form.pdf_use_default" class="muted user-pdf-limit-note">
          实际生效为 min(系统全局上限, 此处值)。管理员账号解析不受个人配额限制。
        </p>
      </el-form-item>
      <el-form-item label="图片输出模式">
        <div class="user-pdf-limit-row">
          <el-checkbox v-model="form.image_output_use_default">跟随系统设置</el-checkbox>
        </div>
        <el-select
          v-show="!form.image_output_use_default"
          v-model="form.image_output_mode"
          :disabled="form.image_output_use_default"
          style="width: 100%; margin-top: 8px"
        >
          <el-option label="Base64 嵌入" value="base64" />
          <el-option label="独立文件" value="separate" />
          <el-option label="不输出" value="none" />
        </el-select>
        <p v-show="!form.image_output_use_default" class="muted user-pdf-limit-note">
          留空则使用系统全局配置。仅当选择「独立文件」时，需配合「可下载图片」权限。
        </p>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="$emit('submit')">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  form: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:modelValue', 'closed', 'submit'])
</script>

<style scoped>
.user-pdf-limit-row {
  margin-bottom: 8px;
}

.user-pdf-limit-note {
  margin: 8px 0 0;
  font-size: 12px;
}
</style>
