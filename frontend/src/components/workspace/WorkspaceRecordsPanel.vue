<template>
  <div class="container card records-container">
    <div class="page-header">
      <h1>
        <span class="page-icon">📋</span>
        生成记录
      </h1>
    </div>
    <p class="lead">
      {{
        isAdmin
          ? '管理员可查询、删除全部用户的任务。'
          : '仅可查询、删除当前账号自己的任务。'
      }}
      进行中的任务需先停止再删除；删除将移除记录与磁盘输出目录。缓存已清除的条目无法下载。
      <span class="muted" style="display: inline-block; margin-top: 8px; font-size: 0.9em;">💡 提示：在小屏幕上可左右滑动表格查看所有字段。</span>
    </p>
    <div class="records-toolbar">
      <el-date-picker
        :model-value="recordsDateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="max-width: 320px"
        @update:model-value="$emit('update-date-range', $event)"
      />
      <el-input
        :model-value="recordsFilename"
        clearable
        placeholder="文件名包含"
        style="max-width: 200px"
        @update:model-value="$emit('update-filename', $event)"
        @keyup.enter="$emit('search')"
      />
      <el-button type="primary" @click="$emit('search')">查询</el-button>
      <el-button class="btn-ghost btn-sm" @click="$emit('refresh')">刷新</el-button>
      <el-button v-if="isAdmin" type="warning" plain :loading="recoveringStaleJobs" @click="$emit('recover-stale')">
        🔄 恢复僵尸任务
      </el-button>
      <el-button
        type="success"
        plain
        :disabled="!recordsSelectionLength || batchDownloading"
        :loading="batchDownloading"
        @click="$emit('batch-download')"
      >
        📦 批量下载 ({{ recordsSelectionLength }})
      </el-button>
      <el-button type="danger" plain :disabled="!recordsSelectionLength || batchDeleting" :loading="batchDeleting" @click="$emit('batch-delete')">
        批量删除 ({{ recordsSelectionLength }})
      </el-button>
    </div>
    <div class="table-wrap">
      <el-table
        ref="recordsTableRefInner"
        v-loading="recordsLoading"
        :data="records"
        row-key="job_id"
        stripe
        style="width: 100%"
        @selection-change="$emit('selection-change', $event)"
      >
        <el-table-column type="selection" width="48" :selectable="recordsRowSelectable" :reserve-selection="true" />
        <el-table-column v-if="isAdmin" prop="username" label="用户" min-width="100" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" min-width="150">
          <template #default="{ row }">
            {{ fmtTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="original_filename" label="文件" min-width="200" show-overflow-tooltip />
        <el-table-column label="单个文件解析页数" min-width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.pages_parsed != null">{{ row.pages_parsed }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="90">
          <template #default="{ row }">
            {{ statusLabel(row.status) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="280" fixed="right" align="right" header-align="right" class-name="records-actions-col">
          <template #default="{ row }">
            <div class="records-actions-cell">
              <template v-if="row.can_download">
                <a class="table-link" :href="dl(row.job_id, 'visualization')" target="_blank" rel="noopener">可视化</a>
                <a class="table-link" :href="dl(row.job_id, 'raw')" target="_blank" rel="noopener">raw</a>
                <a class="table-link" :href="dl(row.job_id, 'markdown')" target="_blank" rel="noopener">md</a>
              </template>
              <span v-else-if="row.cache_cleared" class="muted">缓存已清除</span>
              <span v-else-if="row.status === 'processing'" class="muted">进行中</span>
              <span v-else class="muted">无文件</span>
              <el-button
                v-if="row.status !== 'processing'"
                link
                type="danger"
                :loading="deletingJobId === row.job_id"
                class="records-actions-del"
                @click="$emit('delete-one', row)"
              >
                删除
              </el-button>
              <span v-else class="muted records-actions-del-hint">先停止后可删</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <div class="records-pagination">
      <el-pagination
        :current-page="recordsPage"
        :page-size="recordsPageSize"
        :total="recordsTotal"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @update:current-page="$emit('update-page', $event)"
        @update:page-size="$emit('update-page-size', $event)"
        @current-change="$emit('refresh')"
        @size-change="$emit('refresh')"
      />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  isAdmin: { type: Boolean, default: false },
  recoveringStaleJobs: { type: Boolean, default: false },
  batchDownloading: { type: Boolean, default: false },
  batchDeleting: { type: Boolean, default: false },
  recordsSelectionLength: { type: Number, default: 0 },
  recordsLoading: { type: Boolean, default: false },
  records: { type: Array, default: () => [] },
  recordsDateRange: { type: Array, default: () => [] },
  recordsFilename: { type: String, default: '' },
  recordsPage: { type: Number, default: 1 },
  recordsPageSize: { type: Number, default: 20 },
  recordsTotal: { type: Number, default: 0 },
  deletingJobId: { type: [String, Number, null], default: null },
  recordsRowSelectable: { type: Function, required: true },
  fmtTime: { type: Function, required: true },
  statusLabel: { type: Function, required: true },
  dl: { type: Function, required: true },
})

defineEmits([
  'update-date-range',
  'update-filename',
  'update-page',
  'update-page-size',
  'selection-change',
  'search',
  'refresh',
  'recover-stale',
  'batch-download',
  'batch-delete',
  'delete-one',
])

const recordsTableRefInner = ref(null)

function clearSelection() {
  recordsTableRefInner.value?.clearSelection?.()
}

defineExpose({ clearSelection })
</script>

<style scoped>
.records-container .table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.records-container :deep(.el-table) {
  min-width: 900px;
}

.records-actions-cell {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.records-actions-del,
.records-actions-del-hint {
  margin-left: 4px;
}

.records-toolbar,
.records-pagination {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
  transition: all 0.3s ease;
}

.records-toolbar:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
}

.records-pagination {
  margin-top: 20px;
  margin-bottom: 0;
  justify-content: flex-end;
  padding: 12px 0;
  background: transparent;
  border: none;
  box-shadow: none;
}

@media (max-width: 768px) {
  .records-container :deep(.el-table) {
    min-width: 800px;
  }

  .records-actions-cell {
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
  }

  .records-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .records-toolbar > * {
    width: 100%;
    max-width: none;
  }
}
</style>
