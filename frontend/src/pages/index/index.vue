<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { createSession, sendMessage, getApiBase, setApiBase } from '@/utils/api.js'

const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const state = ref('INIT')
const sessionId = ref('')
const scrollTarget = ref('')
const apiBase = ref(getApiBase())
const showSettings = ref(false)

const ROLE_NAMES = {
  understander: '理解者', supporter: '支持者', opponent: '反方',
  realist: '现实主义者', strategist: '战略顾问'
}
const ROLE_COLORS = {
  understander: '#6ea8fe', supporter: '#57c98a', opponent: '#f2777a',
  realist: '#f0a868', strategist: '#b98cff'
}

function roleName(key) {
  return ROLE_NAMES[key] || key
}
function roleColor(key) {
  return ROLE_COLORS[key] || '#8a909a'
}
function join(arr) {
  if (Array.isArray(arr)) return arr.filter(Boolean).join('；')
  return arr || ''
}

async function ensureSession() {
  try {
    const r = await createSession()
    sessionId.value = r.session_id
    state.value = r.state
    messages.value = []
  } catch (e) {
    uni.showToast({ title: '无法连接后端，请先启动后端服务', icon: 'none' })
  }
}

function newSession() {
  ensureSession()
}

async function send() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  if (!sessionId.value) { await ensureSession() }
  inputText.value = ''
  loading.value = true
  try {
    const res = await sendMessage(sessionId.value, text)
    // 后端会把用户消息与议会响应一起作为 events 返回，直接追加即可
    messages.value.push(...(res.messages || []))
    state.value = res.state
    scrollToBottom()
  } catch (e) {
    uni.showToast({ title: '发送失败，请检查后端', icon: 'none' })
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    const list = messages.value
    if (list.length) {
      scrollTarget.value = 'm' + list[list.length - 1].id
    }
  })
}

function saveApiBase() {
  setApiBase(apiBase.value)
  uni.showToast({ title: '已保存，重启会话生效', icon: 'none' })
  showSettings.value = false
  newSession()
}

onMounted(() => {
  ensureSession()
})
</script>

<template>
  <view class="page">
    <view class="header">
      <view class="h-left">
        <text class="h-title">个人决策议会</text>
        <text class="h-state">状态：{{ state }}</text>
      </view>
      <view class="h-right">
        <text class="btn" @click="showSettings = !showSettings">设置</text>
        <text class="btn" @click="newSession">新会话</text>
      </view>
    </view>

    <view v-if="showSettings" class="settings">
      <text class="set-label">后端地址（App 打包后填真实 IP:端口，如 http://192.168.1.10:8000/api）</text>
      <input class="set-input" v-model="apiBase" placeholder="/api" />
      <text class="btn primary" @click="saveApiBase">保存并重启会话</text>
    </view>

    <view class="intro" v-if="messages.length === 0">
      把你此刻的困惑发出来。议会会先帮你补齐背景、各个角色从立场提问，再依次讨论、互相质疑，最后给出总结与行动计划。决定权始终在你。
    </view>

    <scroll-view scroll-y class="chat" :scroll-into-view="scrollTarget" scroll-with-animation>
      <view v-for="m in messages" :key="m.id" :id="'m' + m.id" class="row" :class="m.sender">
        <view v-if="m.sender === 'user'" class="bubble user">{{ typeof m.content === 'string' ? m.content : '' }}</view>

        <view v-else-if="m.metadata && m.metadata.kind === 'system' && typeof m.content === 'string'" class="sys">{{ m.content }}</view>

        <view v-else-if="m.metadata && m.metadata.kind === 'role_questions'" class="card">
          <view class="card-title">角色提问 · 请一并回复</view>
          <view v-for="(q, i) in m.content" :key="i" class="qitem">
            <view class="qhead">
              <text class="qrole" :style="{ color: roleColor(q.asked_by) }">{{ roleName(q.asked_by) }}</text>
              <text class="qimp" :class="q.importance">{{ q.importance }}</text>
            </view>
            <view class="qtext">{{ q.question }}</view>
            <view class="qreason" v-if="q.reason">为什么：{{ q.reason }}</view>
          </view>
        </view>

        <view v-else-if="m.metadata && m.metadata.kind === 'agent'" class="card agent" :style="{ borderColor: roleColor(m.content.role) }">
          <view class="card-title" :style="{ color: roleColor(m.content.role) }">
            {{ m.content.role_name }}
            <text v-if="m.content.skipped" class="skip">（本轮无新增，跳过）</text>
          </view>
          <view class="pos" v-if="!m.content.skipped">{{ m.content.position }}</view>
          <view class="reason" v-if="!m.content.skipped && m.content.reasoning">{{ m.content.reasoning }}</view>
          <view v-if="m.content.supporting_points && m.content.supporting_points.length" class="blk">支持点：{{ join(m.content.supporting_points) }}</view>
          <view v-if="m.content.concerns && m.content.concerns.length" class="blk warn">顾虑：{{ join(m.content.concerns) }}</view>
          <view v-if="m.content.counterarguments && m.content.counterarguments.length" class="blk">反驳/质疑：{{ join(m.content.counterarguments) }}</view>
          <view v-if="m.content.recommendations && m.content.recommendations.length" class="blk good">建议：{{ join(m.content.recommendations) }}</view>
        </view>

        <view v-else-if="m.metadata && m.metadata.kind === 'cross_exam'" class="card">
          <view class="card-title">集中质询</view>
          <view v-for="(p, i) in m.content" :key="i" class="bullet">• {{ p }}</view>
        </view>

        <view v-else-if="m.metadata && m.metadata.kind === 'moderator'" class="card mod">
          <view class="card-title">Moderator 总结</view>
          <view class="blk"><text class="k">真实问题：</text>{{ m.content.real_question ? (m.content.real_question.underlying || m.content.real_question.surface) : '' }}</view>
          <view class="blk"><text class="k">事实：</text>{{ join(m.content.facts) }}</view>
          <view class="blk"><text class="k">推测：</text>{{ join(m.content.speculations) }}</view>
          <view class="blk"><text class="k">分歧：</text>{{ join(m.content.disagreements) }}</view>
          <view class="blk"><text class="k">信息不足：</text>{{ join(m.content.missing_information) }}</view>
          <view class="blk"><text class="k">选项：</text><text v-for="(o, i) in (m.content.options || [])" :key="i">{{ o.name }}：{{ o.desc }}；</text></view>
          <view class="blk"><text class="k">风险：</text>{{ join(m.content.risks) }}</view>
          <view class="blk"><text class="k">下一步：</text>3天【{{ join(m.content.next_steps && m.content.next_steps.d3) }}】 7天【{{ join(m.content.next_steps && m.content.next_steps.d7) }}】 30天【{{ join(m.content.next_steps && m.content.next_steps.d30) }}】</view>
        </view>

        <view v-else-if="m.metadata && m.metadata.kind === 'action_plan'" class="card plan">
          <view class="card-title">行动计划</view>
          <view class="blk"><text class="k">3 天内：</text>{{ join(m.content.d3) }}</view>
          <view class="blk"><text class="k">7 天内：</text>{{ join(m.content.d7) }}</view>
          <view class="blk"><text class="k">30 天内：</text>{{ join(m.content.d30) }}</view>
          <view class="blk" v-if="m.content.review_prompt"><text class="k">复盘提示：</text>{{ m.content.review_prompt }}</view>
        </view>

        <view v-else-if="m.metadata && m.metadata.kind === 'clarification'" class="card clar">
          <view class="card-title">需要你澄清</view>
          <view v-for="(q, i) in m.content" :key="i" class="bullet">• {{ q }}</view>
        </view>

        <view v-else class="sys">{{ typeof m.content === 'string' ? m.content : '' }}</view>
      </view>

      <view v-if="loading" class="row system">
        <view class="sys loading">议会思考中…</view>
      </view>
    </scroll-view>

    <view class="composer">
      <input class="input" v-model="inputText" placeholder="描述你的困惑，或回答议会的问题…" @confirm="send" />
      <text class="send" @click="send">发送</text>
    </view>
  </view>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f1115;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20rpx 24rpx;
  background: #161a21;
  border-bottom: 1rpx solid #232833;
}
.h-left { display: flex; flex-direction: column; }
.h-title { font-size: 32rpx; font-weight: 600; color: #e6e8eb; }
.h-state { font-size: 22rpx; color: #8a909a; margin-top: 4rpx; }
.h-right { display: flex; gap: 16rpx; }
.btn {
  font-size: 24rpx;
  color: #cdd3db;
  padding: 8rpx 18rpx;
  border: 1rpx solid #2c333f;
  border-radius: 10rpx;
}
.btn.primary { color: #fff; background: #4f8cff; border-color: #4f8cff; }
.settings {
  background: #161a21;
  padding: 20rpx 24rpx;
  border-bottom: 1rpx solid #232833;
}
.set-label { font-size: 22rpx; color: #8a909a; display: block; margin-bottom: 12rpx; }
.set-input {
  background: #0f1115;
  color: #e6e8eb;
  border: 1rpx solid #2c333f;
  border-radius: 10rpx;
  padding: 14rpx 18rpx;
  font-size: 26rpx;
  margin-bottom: 12rpx;
}
.intro {
  margin: 20rpx 24rpx;
  padding: 20rpx;
  background: #161a21;
  border-radius: 14rpx;
  color: #aeb6c2;
  font-size: 24rpx;
  line-height: 1.6;
}
.chat {
  flex: 1;
  padding: 16rpx 24rpx;
  box-sizing: border-box;
}
.row { margin-bottom: 18rpx; display: flex; }
.row.user { justify-content: flex-end; }
.row.system { justify-content: center; }
.bubble.user {
  max-width: 78%;
  background: #4f8cff;
  color: #fff;
  padding: 18rpx 22rpx;
  border-radius: 18rpx 18rpx 4rpx 18rpx;
  font-size: 28rpx;
  line-height: 1.5;
}
.sys {
  background: #1a1d24;
  color: #aeb6c2;
  padding: 14rpx 20rpx;
  border-radius: 12rpx;
  font-size: 24rpx;
  line-height: 1.5;
  max-width: 100%;
  white-space: pre-wrap;
}
.sys.loading { text-align: center; color: #8a909a; }
.card {
  width: 100%;
  background: #1a1d24;
  border: 1rpx solid #2c333f;
  border-radius: 16rpx;
  padding: 20rpx 22rpx;
}
.card.agent { border-left-width: 8rpx; }
.card-title { font-size: 28rpx; font-weight: 600; color: #e6e8eb; margin-bottom: 14rpx; }
.card.mod { border-color: #4f8cff; }
.card.plan { border-color: #57c98a; }
.card.clar { border-color: #f0a868; }
.pos { font-size: 27rpx; color: #e6e8eb; line-height: 1.55; margin-bottom: 10rpx; }
.reason { font-size: 24rpx; color: #aeb6c2; line-height: 1.55; margin-bottom: 10rpx; }
.blk { font-size: 24rpx; color: #cdd3db; line-height: 1.6; margin-top: 8rpx; }
.blk .k { color: #8a909a; }
.blk.warn { color: #f0a868; }
.blk.good { color: #57c98a; }
.bullet { font-size: 24rpx; color: #cdd3db; line-height: 1.6; margin-top: 6rpx; }
.qitem { margin-bottom: 16rpx; padding-bottom: 14rpx; border-bottom: 1rpx solid #232833; }
.qitem:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.qhead { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.qrole { font-size: 24rpx; font-weight: 600; }
.qimp { font-size: 20rpx; padding: 2rpx 10rpx; border-radius: 8rpx; color: #fff; }
.qimp.high { background: #f2777a; }
.qimp.medium { background: #f0a868; }
.qimp.low { background: #6b7280; }
.qtext { font-size: 26rpx; color: #e6e8eb; line-height: 1.5; }
.qreason { font-size: 22rpx; color: #8a909a; margin-top: 6rpx; }
.skip { font-size: 22rpx; color: #8a909a; font-weight: 400; }
.composer {
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding: 16rpx 24rpx;
  background: #161a21;
  border-top: 1rpx solid #232833;
}
.input {
  flex: 1;
  background: #0f1115;
  color: #e6e8eb;
  border: 1rpx solid #2c333f;
  border-radius: 12rpx;
  padding: 16rpx 20rpx;
  font-size: 28rpx;
}
.send {
  background: #4f8cff;
  color: #fff;
  font-size: 28rpx;
  padding: 16rpx 30rpx;
  border-radius: 12rpx;
}
</style>
