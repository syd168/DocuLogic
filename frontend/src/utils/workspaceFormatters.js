export function dl(jobId, type) {
  return `/download/${jobId}/${type}`
}

export function fmtTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').replace('Z', '')
}

export function statusLabel(status) {
  const map = { processing: '进行中', completed: '已完成', stopped: '已停止', failed: '失败' }
  return map[status] || status
}
