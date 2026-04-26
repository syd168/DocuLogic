<template>
  <el-dialog
    :model-value="modelValue"
    title="添加新用户"
    width="520px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @closed="$emit('closed')"
  >
    <el-form ref="formRef" :model="form" label-position="top" :rules="rules">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="3-50 个字符" autocomplete="username" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" placeholder="example@domain.com" autocomplete="email" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="至少 8 位" />
      </el-form-item>
      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input v-model="form.confirmPassword" type="password" show-password autocomplete="new-password" placeholder="再次输入密码" />
      </el-form-item>
      <el-form-item label="管理员">
        <el-switch v-model="form.is_admin" />
        <span class="muted create-user-admin-hint">管理员不受单个文件页数限制</span>
      </el-form-item>
      <el-form-item label="账号启用">
        <el-switch v-model="form.is_active" />
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
          实际生效为 min(系统全局上限, 此处值)。
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
          留空则使用系统全局配置。
        </p>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="$emit('submit')">创建</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  form: { type: Object, required: true },
  rules: { type: Object, required: true },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:modelValue', 'closed', 'submit'])

const formRef = ref(null)

async function validate() {
  if (!formRef.value) return
  return formRef.value.validate()
}

function clearValidate() {
  formRef.value?.clearValidate?.()
}

defineExpose({ validate, clearValidate })
</script>

<style scoped>
.create-user-admin-hint {
  margin-left: 8px;
  font-size: 12px;
}

.user-pdf-limit-row {
  margin-bottom: 8px;
}

.user-pdf-limit-note {
  margin: 8px 0 0;
  font-size: 12px;
}
</style>
