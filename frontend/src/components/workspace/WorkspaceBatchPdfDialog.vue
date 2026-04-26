<template>
  <el-dialog
    :model-value="modelValue"
    title="批量设置单个文件最大解析页数"
    width="480px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      class="mb-3"
      title="将写入选中用户的个人上限；「与系统全局一致」表示清除个人覆盖，实际配额仍受系统全局上限约束。"
    />
    <el-form label-position="top">
      <el-form-item label="与系统全局一致（清除个人上限）">
        <el-switch :model-value="useDefault" @update:model-value="$emit('update:useDefault', $event)" />
      </el-form-item>
      <el-form-item v-if="!useDefault" label="个人上限（页）">
        <el-input-number :model-value="pages" :min="1" :max="10000" controls-position="right" @update:model-value="$emit('update:pages', $event)" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="$emit('submit')">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  useDefault: { type: Boolean, default: true },
  pages: { type: Number, default: 1 },
  loading: { type: Boolean, default: false },
})

defineEmits(['update:modelValue', 'update:useDefault', 'update:pages', 'submit'])
</script>
