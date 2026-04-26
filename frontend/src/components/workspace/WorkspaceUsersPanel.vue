<template>
  <div class="container card users-container">
    <div class="page-header">
      <h1>
        <span class="page-icon">👥</span>
        用户管理
      </h1>
    </div>
    <p class="lead">
      搜索用户名或邮箱；可修改普通用户的启用状态、角色与密码。表格中不可勾选管理员账号，故批量操作仅针对普通用户。批量设置单个文件解析页数上限、批量删除前均会弹出警告或确认。删除用户将同时删除其解析任务记录且不可恢复。
    </p>

    <div class="users-toolbar">
      <el-input
        :model-value="userSearchQ"
        clearable
        placeholder="用户名 / 邮箱"
        style="max-width: 280px"
        @update:model-value="$emit('update-search-q', $event)"
        @keyup.enter="$emit('search')"
      />
      <el-button type="primary" @click="$emit('search')">查询</el-button>
      <el-button class="btn-ghost btn-sm" @click="$emit('refresh')">刷新</el-button>
      <el-button type="success" @click="$emit('open-create-user')">➕ 添加用户</el-button>
      <el-button :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('batch-active', true)">
        批量启用 ({{ usersSelectionLength }})
      </el-button>
      <el-button type="warning" plain :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('batch-active', false)">
        批量禁用
      </el-button>
      <el-button type="warning" plain :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('batch-admin', true)">
        批量设为管理员
      </el-button>
      <el-button plain :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('batch-admin', false)">
        批量取消管理员
      </el-button>
      <el-button type="primary" plain :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('open-batch-pdf')">
        批量设置单个文件解析页数上限
      </el-button>
      <el-button type="danger" plain :disabled="!usersSelectionLength || usersBatchLoading" :loading="usersBatchLoading" @click="$emit('batch-delete')">
        批量删除用户
      </el-button>
    </div>

    <div class="table-wrap">
      <el-table
        ref="usersTableRefInner"
        v-loading="usersLoading"
        :data="usersList"
        row-key="id"
        stripe
        style="width: 100%"
        @selection-change="$emit('selection-change', $event)"
      >
        <el-table-column type="selection" width="48" :selectable="usersRowSelectable" :reserve-selection="true" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.phone" class="muted">{{ row.phone }}</span>
            <span v-else class="muted" style="opacity: 0.5;">未绑定</span>
          </template>
        </el-table-column>
        <el-table-column label="管理员" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'warning' : 'info'" size="small">{{ row.is_admin ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" min-width="160">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="单个文件可解析页数" min-width="160" align="center">
          <template #default="{ row }">
            <template v-if="row.is_admin">
              <span class="muted">无限制</span>
            </template>
            <template v-else>
              <span>系统限制页数（{{ userPdfEffectiveDisplay(row) }}）</span>
              <div v-if="row.pdf_max_pages != null" class="muted user-pdf-raw-hint">个人配置 {{ row.pdf_max_pages }}</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="图片输出模式" min-width="140" align="center">
          <template #default="{ row }">
            <template v-if="row.image_output_mode == null">
              <el-tag type="info" size="small">跟随系统</el-tag>
            </template>
            <template v-else-if="row.image_output_mode === 'base64'">
              <el-tag type="primary" size="small">Base64 嵌入</el-tag>
            </template>
            <template v-else-if="row.image_output_mode === 'separate'">
              <el-tag type="success" size="small">独立文件</el-tag>
            </template>
            <template v-else-if="row.image_output_mode === 'none'">
              <el-tag type="warning" size="small">不输出</el-tag>
            </template>
            <template v-else>
              <span class="muted">{{ row.image_output_mode }}</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <el-button v-if="!row.is_admin || row.username === username" link type="primary" size="small" @click="$emit('edit-user', row)">
                编辑
              </el-button>
              <el-button link type="warning" size="small" @click="$emit('view-session', row)">
                查看会话
              </el-button>
              <el-button v-if="row.id !== currentUserId && row.has_session" link type="danger" size="small" @click="$emit('kick-user', row)">
                踢出
              </el-button>
              <span v-else-if="row.id === currentUserId" class="muted" style="font-size: 12px;">不可操作</span>
              <span v-else class="muted" style="font-size: 12px;">未登录</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="users-pagination">
      <el-pagination
        :current-page="userPage"
        :page-size="userPageSize"
        :total="userTotal"
        :page-sizes="[10, 20, 50]"
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
  userSearchQ: { type: String, default: '' },
  usersSelectionLength: { type: Number, default: 0 },
  usersBatchLoading: { type: Boolean, default: false },
  usersLoading: { type: Boolean, default: false },
  usersList: { type: Array, default: () => [] },
  username: { type: String, default: '' },
  currentUserId: { type: [String, Number, null], default: null },
  userPage: { type: Number, default: 1 },
  userPageSize: { type: Number, default: 20 },
  userTotal: { type: Number, default: 0 },
  usersRowSelectable: { type: Function, required: true },
  fmtTime: { type: Function, required: true },
  userPdfEffectiveDisplay: { type: Function, required: true },
})

defineEmits([
  'update-search-q',
  'update-page',
  'update-page-size',
  'search',
  'refresh',
  'open-create-user',
  'batch-active',
  'batch-admin',
  'open-batch-pdf',
  'batch-delete',
  'selection-change',
  'edit-user',
  'view-session',
  'kick-user',
])

const usersTableRefInner = ref(null)

function clearSelection() {
  usersTableRefInner.value?.clearSelection?.()
}

defineExpose({ clearSelection })
</script>

<style scoped>
.users-toolbar {
  margin-bottom: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border);
  border-radius: 10px;
}

.users-pagination {
  margin-top: 20px;
  margin-bottom: 0;
  display: flex;
  justify-content: flex-end;
  padding: 12px 0;
}

.user-pdf-raw-hint {
  margin-top: 4px;
  font-size: 11px;
  line-height: 1.3;
}

@media (max-width: 768px) {
  .users-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .users-toolbar > * {
    width: 100%;
    max-width: none;
  }
}
</style>
