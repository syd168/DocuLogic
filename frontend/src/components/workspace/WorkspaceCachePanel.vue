<template>
  <div class="container card cache-container">
    <div class="page-header">
      <h1>
        <span class="page-icon">🗑️</span>
        缓存清除
      </h1>
    </div>
    <div class="parse-page-intro">
      <p class="parse-page-lead">
        勾选下方列表中的任务，删除其在磁盘上的解析输出目录以释放空间。生成记录仍保留，但清除后将无法再次下载该任务的文件。
      </p>
      <div class="parse-formats">
        <span class="parse-formats-label">可清理</span>
        <div class="parse-format-chips" aria-label="可清理的任务类型">
          <span class="fmt-chip">已完成</span>
          <span class="fmt-chip">已停止</span>
          <span class="fmt-chip fmt-chip-cache-fail">失败残留</span>
        </div>
      </div>
      <p class="parse-page-note muted">
        进行中的任务请先在「文档解析」中停止；若只需删记录、不删磁盘，请使用「生成记录」。
      </p>
      <details class="parse-page-details">
        <summary>详细说明</summary>
        <ul class="parse-page-details-list">
          <li>
            此处仅列出后端标记为<strong>可清除</strong>的已结束任务（成功、已停止或符合策略的失败项等）。
          </li>
          <li>
            当前版本在推理<strong>失败</strong>后通常会<strong>自动删除</strong>该任务目录；若升级服务前仍有残留，可在此勾选清除。
          </li>
        </ul>
      </details>
    </div>
    <div id="cache-toolbar">
      <el-button class="btn-ghost btn-sm" @click="$emit('refresh')">刷新列表</el-button>
      <el-button class="btn-danger-outline" :disabled="!selection.length" @click="$emit('clear')">清除选中缓存</el-button>
    </div>
    <div class="table-wrap">
      <el-table v-loading="loading" :data="rows" row-key="job_id" stripe style="width: 100%" @selection-change="$emit('selection-change', $event)">
        <el-table-column type="selection" width="48" />
        <el-table-column label="完成时间" min-width="150">
          <template #default="{ row }">
            {{ fmtTime(row.completed_at || row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="original_filename" label="文件" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" min-width="90">
          <template #default="{ row }">
            {{ statusLabel(row.status) }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
defineProps({
  loading: { type: Boolean, default: false },
  rows: { type: Array, default: () => [] },
  selection: { type: Array, default: () => [] },
  fmtTime: { type: Function, required: true },
  statusLabel: { type: Function, required: true },
})

defineEmits(['refresh', 'clear', 'selection-change'])
</script>

<style scoped>
.parse-page-intro {
  margin-bottom: 20px;
}
.parse-page-lead {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.55;
}
.parse-formats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  margin-bottom: 10px;
}
.parse-formats-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  opacity: 0.9;
}
.parse-format-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.fmt-chip {
  display: inline-block;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  background: rgba(61, 214, 245, 0.08);
  border: 1px solid rgba(61, 214, 245, 0.22);
  border-radius: 999px;
  line-height: 1.2;
}
.fmt-chip-cache-fail {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.35);
}
.parse-page-note {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
}
.parse-page-details {
  font-size: 13px;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0 14px;
  background: var(--bg-elevated);
}
.parse-page-details summary {
  cursor: pointer;
  padding: 11px 0;
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  list-style: none;
  user-select: none;
}
.parse-page-details summary::-webkit-details-marker {
  display: none;
}
.parse-page-details summary::after {
  content: '▸';
  float: right;
  opacity: 0.45;
  font-size: 12px;
  transition: transform 0.2s ease;
}
.parse-page-details[open] summary::after {
  transform: rotate(90deg);
}
.parse-page-details-list {
  margin: 0 0 14px;
  padding-left: 1.15em;
  line-height: 1.65;
}
.parse-page-details-list li + li {
  margin-top: 6px;
}

.cache-container .table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.cache-container :deep(.el-table) {
  min-width: 600px;
}

.cache-container #cache-toolbar {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  transition: all 0.3s ease;
}

.cache-container #cache-toolbar:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}
</style>
