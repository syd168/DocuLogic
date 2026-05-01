<template>
  <div class="dynamic-config-container">
    <el-form :model="formData" label-width="140px" size="default" class="config-form">
      <!-- 遍历 Schema 中的字段定义 -->
      <template v-for="field in schema.fields" :key="field.key">
        <div class="config-item-card">
          <div class="item-header">
            <label class="item-label">
              <span class="label-icon">{{ getFieldIcon(field.key) }}</span>
              {{ field.label }}
            </label>
            <el-tooltip v-if="field.hint" :content="field.hint" placement="top">
              <el-icon class="hint-icon"><InfoFilled /></el-icon>
            </el-tooltip>
          </div>

          <div class="item-content">
            <!-- 文本输入框 -->
            <el-input 
              v-if="field.type === 'text' || field.type === 'password'" 
              v-model="formData[field.key]" 
              :type="field.type"
              :placeholder="field.placeholder || '请输入内容'"
              class="styled-input"
            />

            <!-- 多行文本框 -->
            <el-input 
              v-else-if="field.type === 'textarea'" 
              v-model="formData[field.key]" 
              type="textarea" 
              :rows="4"
              :placeholder="field.placeholder"
            />

            <!-- 数字输入框 -->
            <el-input-number 
              v-else-if="field.type === 'number'" 
              v-model="formData[field.key]" 
              controls-position="right"
            />

            <!-- 开关 (Boolean) -->
            <el-switch 
              v-else-if="field.type === 'boolean'" 
              v-model="formData[field.key]" 
              active-text="开启"
              inactive-text="关闭"
              inline-prompt
            />

            <!-- 下拉选择框 -->
            <el-select 
              v-else-if="field.type === 'select'" 
              v-model="formData[field.key]"
              placeholder="请选择"
              class="styled-select"
            >
              <el-option 
                v-for="opt in field.options" 
                :key="opt.value || opt" 
                :label="opt.label || opt" 
                :value="opt.value || opt" 
              />
            </el-select>

            <!-- JSON 编辑器 -->
            <el-input 
              v-else-if="field.type === 'json'" 
              v-model="jsonFields[field.key]" 
              type="textarea" 
              :rows="3"
              @blur="handleJsonBlur(field.key)"
              class="code-editor"
            />

            <!-- 嵌套对象卡片 -->
            <div v-else-if="field.type === 'object'" class="nested-object-card">
              <div class="nested-header">
                <span>{{ field.label }}</span>
              </div>
              
              <div v-for="child in (field.children || [])" :key="child.key" class="nested-field-row">
                <!-- 如果子字段是 JSON 类型（如 repos），渲染为单选按钮组 -->
                <div v-if="child.type === 'json' && typeof formData[field.key]?.[child.key] === 'object'" style="flex: 1; display: flex; align-items: center; gap: 12px;">
                  <span class="nested-label">{{ child.label }}:</span>
                  <el-radio-group v-model="selectedRepoSource[field.key + '.' + child.key]" class="repo-group">
                    <el-radio-button v-for="(repoUrl, sourceName) in formData[field.key][child.key]" :key="sourceName" :value="sourceName">
                      {{ formatSourceName(sourceName) }}
                    </el-radio-button>
                  </el-radio-group>
                  <div class="muted" style="font-size: 12px; color: #909399; white-space: nowrap; margin-left: auto;">
                    当前地址: {{ formData[field.key][child.key][selectedRepoSource[field.key + '.' + child.key]] }}
                  </div>
                </div>
                
                <!-- 普通文本子字段 -->
                <div v-else style="display: flex; align-items: center; gap: 12px; flex: 1;">
                  <span class="nested-label">{{ child.label }}:</span>
                  <el-input 
                    v-model="(formData[field.key] = formData[field.key] || {})[child.key]" 
                    size="small" 
                    class="nested-input"
                    :placeholder="child.placeholder"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  schema: { type: Object, required: true },
  modelValue: { type: Object, required: true }
})

const emit = defineEmits(['update:modelValue'])

const formData = ref({}) // 初始化为空对象
const jsonFields = ref({})
const selectedRepoSource = ref({}) // 用于存储用户选择的下载源（如 'modelscope'）

// 获取字段对应的图标
const getFieldIcon = (key) => {
  const iconMap = {
    'output_format': '📄',
    'enable_table_recognition': '📊',
    'enable_formula_recognition': '🧮',
    'enable_layout_recognition': '📐',
    'download': '📥',
    'prompt': '💬',
    'dest_dir': '📂',
    'repos': '🌐'
  }
  return iconMap[key] || '⚙️'
}

// 格式化下载源名称
const formatSourceName = (name) => {
  const map = { 'modelscope': '🇨🇳 ModelScope', 'huggingface': '🌐 HuggingFace', 'pypi': '📦 PyPI' }
  return map[name] || name
}

// 处理仓库源切换
const handleRepoChange = (parentKey, childKey, sourceName) => {
  // 这里只是记录用户的选择，实际下载时后端会根据这个 sourceName 去 repos 里找对应的 URL
  console.log(`User selected source: ${sourceName} for ${parentKey}.${childKey}`)
}

// 监听 modelValue 变化，同步到 formData
watch(() => props.modelValue, (newVal) => {
  if (newVal && typeof newVal === 'object') {
    // 浅拷贝，保持响应式
    Object.assign(formData.value, newVal)
    
    // 重新初始化嵌套对象和 JSON 字段
    props.schema.fields.forEach(field => {
      // 确保嵌套对象存在
      if (field.type === 'object' && !formData.value[field.key]) {
        formData.value[field.key] = {}
      }
      
      // 处理子字段的初始化
      if (field.children) {
        field.children.forEach(child => {
          if (child.type === 'json') {
            const fullKey = `${field.key}.${child.key}`
            const val = formData.value[field.key]?.[child.key]
            if (typeof val === 'object') {
              jsonFields.value[fullKey] = JSON.stringify(val, null, 2)
              
              // 自动选中第一个下载源作为默认值
              const keys = Object.keys(val)
              if (keys.length > 0 && !selectedRepoSource.value[fullKey]) {
                selectedRepoSource.value[fullKey] = keys[0]
              }
            }
          }
        })
      }
      
      // 初始化顶层 JSON 显示
      if ((field.type === 'json' || field.type === 'object') && typeof formData.value[field.key] === 'object') {
        jsonFields.value[field.key] = JSON.stringify(formData.value[field.key], null, 2)
      }
    })
  }
}, { immediate: true, deep: true })

// 处理嵌套 JSON 字符串转对象 (例如 download.repos)
const handleNestedJsonBlur = (parentKey, childKey) => {
  const fullKey = `${parentKey}.${childKey}`
  try {
    if (!formData.value[parentKey]) formData.value[parentKey] = {}
    formData.value[parentKey][childKey] = JSON.parse(jsonFields.value[fullKey])
  } catch (e) {
    console.warn(`Invalid JSON for nested field ${fullKey}`)
  }
}

// 处理 JSON 字符串转对象
const handleJsonBlur = (key) => {
  try {
    formData.value[key] = JSON.parse(jsonFields.value[key])
  } catch (e) {
    console.warn(`Invalid JSON for field ${key}`)
  }
}

// 监听数据变化并同步给父组件
watch(formData, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })
</script>

<style scoped>
.dynamic-config-container {
  padding: 10px 0;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-item-card {
  background: transparent;
  border: none;
  padding: 0;
  display: flex;
  align-items: center; /* 垂直居中对齐 */
  gap: 24px;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-bottom: 0; /* 去掉底部间距，实现同行 */
  min-width: 160px; /* 给标签一个固定宽度，保持对齐 */
}

.item-label {
  font-weight: 500;
  color: #606266;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap; /* 防止标签换行 */
}

.label-icon {
  font-size: 16px;
}

.hint-icon {
  color: #909399;
  cursor: help;
  font-size: 14px;
}

.item-content {
  padding-left: 0;
  flex: 1; /* 让内容区域占据剩余空间 */
}

.nested-object-card {
  background: transparent;
  border: 1px dashed #dcdfe6;
  border-radius: 4px;
  padding: 12px;
  margin-top: 8px;
}

.nested-header {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.nested-field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.nested-field-row:last-child {
  margin-bottom: 0;
}

.nested-label {
  min-width: 80px;
  text-align: right;
  color: #606266;
  font-size: 13px;
}

.nested-input {
  flex: 1;
}

.repo-selector-wrapper {
  margin-bottom: 12px;
}

.repo-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
