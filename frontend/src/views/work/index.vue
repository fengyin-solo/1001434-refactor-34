<template>
  <section class="page" data-module="work">
    <header class="page-head">
      <div>
        <h2>养护施工管理</h2>
        <p class="page-desc">维护施工任务，围绕施工编号、关联计划、承接单位、开工日期做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记施工任务</button>
        <button class="btn" type="button" @click="exportRows">导出养护施工清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无养护施工数据，可先登记施工任务</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条养护施工记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { fetchJson, request } from '@/api/client'

type Row = Record<string, string | number | null>
type Summary = { label: string; value: number }

const ENDPOINT = '/api/work'
const columns = ["施工编号", "关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "监理人员", "施工状态"]
const actions = ["确认开工", "提交验收", "确认完工"]
const statuses = ["待开工", "施工中", "待验收", "已完工"]
const stats = ref<Summary[]>([])

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '施工任务登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error('养护施工动作未生效，请稍后重试')
    }
    await reload()
    await loadSummary()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护施工操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('施工任务列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '养护施工列表读取失败'
  }
}


async function loadSummary() {
  try {
    const payload = await fetchJson<{ total: number; pending: number; abnormal: number }>(
      `${ENDPOINT}/summary`,
    )
    stats.value = [
      { label: '记录总数', value: payload.total },
      { label: '待处理', value: payload.pending },
      { label: '异常量', value: payload.abnormal },
    ]
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模块汇总数据加载失败'
  }
}

onMounted(() => {
  void reload()
  void loadSummary()
})
</script>
