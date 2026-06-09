<template>
  <div class="home-page">
    <div class="soft-orbit orbit-one"></div>
    <div class="soft-orbit orbit-two"></div>

    <section class="hero-card">
      <div class="hero-left">
        <div class="tag-row">
          <span>AI 图文助手</span>
          <span>小红书风格</span>
          <span>本地可配置</span>
        </div>

        <h1 class="page-title">把选题变成一组能直接发的笔记</h1>
        <p class="page-subtitle">
          当前主页是原模式：输入一个主题，只生成一个完整作品；系统会把它拆成封面、内容页和收尾页，再为每一页生成图片。
        </p>

        <ComposerInput
          ref="composerRef"
          v-model="topic"
          :loading="loading"
          @generate="handleGenerate"
          @imagesChange="handleImagesChange"
        />

        <div class="page-count-control">
          <span>图文页数</span>
          <div class="page-count-options">
            <button
              v-for="count in pageCountOptions"
              :key="count"
              type="button"
              :class="{ active: pageCount === count }"
              @click="pageCount = count"
            >
              {{ count }} 页
            </button>
          </div>
        </div>

        <div v-if="auth.user" class="quota-notice">
          <span>当前可用额度</span>
          <strong>{{ quotaText }}</strong>
          <em v-if="!auth.isAdmin && auth.user.quota_limit !== null && auth.user.quota_limit !== undefined">
            本次最多消耗 {{ pageCount }} 张
          </em>
        </div>

        <div v-if="loading" class="generation-progress" role="status" aria-live="polite">
          <div class="progress-head">
            <span>{{ progressStep }}</span>
            <strong>{{ generationProgress }}%</strong>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${generationProgress}%` }"></div>
          </div>
          <p>{{ progressHint }}</p>
        </div>

        <div class="quick-topics">
          <button
            v-for="item in quickTopics"
            :key="item"
            type="button"
            @click="topic = item"
          >
            {{ item }}
          </button>
        </div>

        <div class="creator-stats">
          <div>
            <strong>3 步</strong>
            <span>完成图文结构</span>
          </div>
          <div>
            <strong>5 张</strong>
            <span>支持参考图</span>
          </div>
          <div>
            <strong>∞</strong>
            <span>草稿可复用</span>
          </div>
        </div>

        <div class="mode-switch-card">
          <div>
            <span>想批量找方向？</span>
            <strong>同一话题先生成 5 个不同作品选题</strong>
            <p>先选作品方向，再进入原来的单作品多页图文生成流程。</p>
          </div>
          <button type="button" @click="router.push('/ideas')">去生成 5 个选题</button>
        </div>
      </div>

      <div class="preview-zone">
        <div class="floating-card idea-card">
          <span>今日灵感</span>
          <strong>低成本变美计划</strong>
        </div>
        <div class="floating-card hot-card">
          <span>热词</span>
          <strong>#自律生活</strong>
        </div>

        <div class="phone-preview" aria-label="笔记预览">
          <div class="phone-top">
            <span></span>
            <strong>笔记预览</strong>
            <span></span>
          </div>
          <div class="note-cover">
            <div class="cover-badge">封面</div>
            <h2>7 天做出<br />高质感笔记</h2>
            <p>标题、正文、配图一起规划</p>
          </div>
          <div class="note-meta">
            <div class="avatar">薯</div>
            <div>
              <strong>薯光创作助手</strong>
              <span>刚刚生成</span>
            </div>
          </div>
          <div class="note-lines">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </section>

    <section class="inspiration-strip">
      <div class="strip-title">
        <span>内容灵感池</span>
        <strong>先选场景，再生成笔记</strong>
      </div>
      <div class="marquee-row">
        <div class="marquee-track">
          <span v-for="item in inspirationTags" :key="item">{{ item }}</span>
          <span v-for="item in inspirationTags" :key="`${item}-copy`">{{ item }}</span>
        </div>
      </div>
    </section>

    <section class="workflow-section">
      <div class="workflow-card">
        <div class="workflow-header">
          <span>创作流程</span>
          <strong>从选题到发布前检查</strong>
        </div>
        <div class="workflow-steps">
          <div class="workflow-step active">
            <span>1</span>
            <strong>输入主题</strong>
            <p>写一句真实需求，或者点快捷选题。</p>
          </div>
          <div class="workflow-step">
            <span>2</span>
            <strong>编辑大纲</strong>
            <p>确认封面、内容页、收尾页的表达。</p>
          </div>
          <div class="workflow-step">
            <span>3</span>
            <strong>生成图文</strong>
            <p>按页面批量生成，也可以单页重做。</p>
          </div>
        </div>
      </div>

      <div class="trend-panel">
        <div class="trend-header">
          <span>小红书选题感</span>
          <strong>本周更适合做这些</strong>
        </div>
        <button v-for="trend in trends" :key="trend.title" type="button" @click="topic = trend.title">
          <span>{{ trend.rank }}</span>
          <strong>{{ trend.title }}</strong>
          <em>{{ trend.heat }}</em>
        </button>
      </div>
    </section>

    <section class="feature-grid">
      <article class="feature-card">
        <span class="feature-icon">01</span>
        <h3>先拆结构</h3>
        <p>把一个主题拆成多页笔记，减少临时想页面的焦虑。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon">02</span>
        <h3>参考图辅助</h3>
        <p>上传图片后生成更贴近你审美的封面和内容页。</p>
      </article>
      <article class="feature-card">
        <span class="feature-icon">03</span>
        <h3>草稿可追溯</h3>
        <p>生成记录会保存到草稿，方便继续编辑和复用。</p>
      </article>
    </section>

    <div v-if="error" class="error-toast">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGeneratorStore } from '../stores/generator'
import { useAuthStore } from '../stores/auth'
import { generateOutline } from '../api'
import { useDraftAutosave } from '../composables/useDraftAutosave'
import ComposerInput from '../components/home/ComposerInput.vue'

const router = useRouter()
const store = useGeneratorStore()
const auth = useAuthStore()
const { ensureDraftSaved } = useDraftAutosave({ watchOutline: false })

const topic = ref('')
const loading = ref(false)
const error = ref('')
const composerRef = ref<InstanceType<typeof ComposerInput> | null>(null)
const uploadedImageFiles = ref<File[]>([])
const pageCount = ref(5)
const generationProgress = ref(0)
const progressStep = ref('')
const progressHint = ref('')
let progressTimer: ReturnType<typeof setInterval> | null = null

const quickTopics = [
  '通勤女生的高效早晨',
  '新手做小红书账号定位',
  '周末低预算探店路线',
  '30天自律生活记录'
]

const inspirationTags = [
  '显白穿搭',
  '低预算改造',
  '探店路线',
  '新手教程',
  '生活复盘',
  '好物清单',
  '自律打卡',
  '情绪价值'
]

const trends = [
  { rank: '01', title: '普通人如何做出稳定更新节奏', heat: '8.9w' },
  { rank: '02', title: '周末两小时低成本自我提升', heat: '6.4w' },
  { rank: '03', title: '新手账号前 10 篇笔记怎么发', heat: '5.7w' }
]

const pageCountOptions = [3, 4, 5]

const quotaText = computed(() => {
  if (!auth.user) return ''
  if (auth.isAdmin) return '不限量'
  if (auth.user.quota_limit === null || auth.user.quota_limit === undefined) return '不限量'
  return `${auth.user.quota_remaining ?? 0} 张`
})

const outlineProgressSteps = [
  { at: 8, label: '正在理解主题', hint: '先判断这条笔记适合做封面、教程还是清单。' },
  { at: 28, label: '正在拆分页面', hint: '把主题拆成封面、内容页和收尾页的节奏。' },
  { at: 52, label: '正在写每页文案', hint: '补齐每一页的标题、正文和图片方向。' },
  { at: 74, label: '正在整理草稿', hint: '准备把大纲保存到本地记录，方便继续编辑。' },
  { at: 90, label: '马上完成', hint: '最后检查页面结构，完成后会自动进入编辑页。' }
]

function startProgress(steps = outlineProgressSteps) {
  stopProgress()
  generationProgress.value = steps[0].at
  progressStep.value = steps[0].label
  progressHint.value = steps[0].hint

  progressTimer = setInterval(() => {
    const next = Math.min(generationProgress.value + Math.ceil(Math.random() * 6), 94)
    generationProgress.value = next
    const currentStep = [...steps].reverse().find(step => next >= step.at) || steps[0]
    progressStep.value = currentStep.label
    progressHint.value = currentStep.hint
  }, 700)
}

function finishProgress(label = '生成完成') {
  stopProgress()
  generationProgress.value = 100
  progressStep.value = label
  progressHint.value = '已经生成好内容，正在为你打开下一步。'
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function handleImagesChange(images: File[]) {
  uploadedImageFiles.value = images
}

async function handleGenerate() {
  if (!topic.value.trim()) return

  loading.value = true
  error.value = ''
  startProgress()

  try {
    const imageFiles = uploadedImageFiles.value
    const result = await generateOutline(
      topic.value.trim(),
      imageFiles.length > 0 ? imageFiles : undefined,
      pageCount.value
    )

    if (result.success && result.pages) {
      store.reset()
      store.setTopic(topic.value.trim())
      store.setOutline(result.outline || '', result.pages)
      await ensureDraftSaved()

      store.userImages = imageFiles.length > 0 ? imageFiles : []
      composerRef.value?.clearPreviews()
      uploadedImageFiles.value = []

      finishProgress()
      router.push('/outline')
    } else {
      error.value = result.error || '生成大纲失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    stopProgress()
    loading.value = false
  }
}

onUnmounted(() => {
  stopProgress()
})
</script>

<style scoped>
.home-page {
  position: relative;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
}

.soft-orbit {
  position: absolute;
  z-index: -1;
  width: 220px;
  height: 220px;
  border-radius: 999px;
  filter: blur(16px);
  opacity: 0.5;
  animation: floatGlow 8s ease-in-out infinite;
}

.orbit-one {
  top: 20px;
  right: 40px;
  background: rgba(255, 36, 66, 0.12);
}

.orbit-two {
  left: 0;
  top: 440px;
  background: rgba(255, 191, 87, 0.14);
  animation-delay: -3s;
}

.hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 38px;
  align-items: center;
  min-height: 560px;
  padding: 44px;
  border: 1px solid rgba(255, 36, 66, 0.08);
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 249, 250, 0.94)),
    radial-gradient(circle at 18% 20%, rgba(255, 36, 66, 0.1), transparent 28%);
  box-shadow: 0 18px 54px rgba(72, 28, 34, 0.07);
  overflow: hidden;
  animation: riseIn 0.7s ease both;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 22px;
}

.tag-row span,
.quick-topics button {
  border: 1px solid rgba(255, 36, 66, 0.18);
  border-radius: 999px;
  background: #fff;
  color: #ff2442;
  font-size: 13px;
  font-weight: 700;
}

.tag-row span {
  padding: 7px 12px;
}

.page-title {
  max-width: 640px;
  margin: 0;
  color: #1f1f1f;
  font-size: clamp(34px, 4.2vw, 58px);
  line-height: 1.12;
  font-weight: 800;
  letter-spacing: 0;
}

.page-subtitle {
  max-width: 620px;
  margin: 18px 0 24px;
  color: #6f6265;
  font-size: 16px;
  line-height: 1.8;
}

.quick-topics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.generation-progress {
  max-width: 720px;
  margin-top: 14px;
  padding: 16px;
  border: 1px solid rgba(255, 36, 66, 0.14);
  border-radius: 20px;
  background: linear-gradient(135deg, #fff8f9, #fff);
  box-shadow: 0 12px 30px rgba(255, 36, 66, 0.08);
}

.progress-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 10px;
}

.progress-head span {
  color: #2b2022;
  font-size: 14px;
  font-weight: 900;
}

.progress-head strong {
  color: #ff2442;
  font-size: 14px;
}

.progress-track {
  position: relative;
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #ffe8ec;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff2442, #ff8a6b);
  box-shadow: 0 0 18px rgba(255, 36, 66, 0.28);
  transition: width 0.45s ease;
}

.progress-fill::after {
  content: "";
  display: block;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.42), transparent);
  animation: progressShine 1.2s linear infinite;
}

.generation-progress p {
  margin: 10px 0 0;
  color: #80686d;
  font-size: 13px;
  line-height: 1.6;
}

.quick-topics button {
  padding: 9px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-topics button:hover {
  background: #ff2442;
  color: #fff;
  transform: translateY(-1px);
}

.page-count-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  max-width: 720px;
  margin-top: 14px;
  padding: 10px 12px;
  border: 1px solid #f5e1e5;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
}

.page-count-control span {
  color: #8a6e73;
  font-size: 13px;
  font-weight: 800;
}

.page-count-options {
  display: flex;
  gap: 8px;
}

.page-count-options button {
  min-height: 32px;
  padding: 0 13px;
  border: 1px solid #f0d9dd;
  border-radius: 999px;
  background: #fff;
  color: #7b666b;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.page-count-options button.active {
  border-color: #ff2442;
  background: #ff2442;
  color: #fff;
}

.quota-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  max-width: 720px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid #f5e1e5;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
}

.quota-notice span,
.quota-notice em {
  color: #8a6e73;
  font-size: 13px;
  font-style: normal;
  font-weight: 800;
}

.quota-notice strong {
  margin-left: auto;
  color: #ff2442;
  font-size: 15px;
  font-weight: 900;
}

.creator-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  max-width: 720px;
  margin-top: 18px;
}

.creator-stats div {
  padding: 14px 16px;
  border: 1px solid #f3dfe3;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.creator-stats strong,
.creator-stats span {
  display: block;
}

.creator-stats strong {
  color: #ff2442;
  font-size: 22px;
  line-height: 1;
  margin-bottom: 8px;
}

.creator-stats span {
  color: #82686d;
  font-size: 13px;
}

.mode-switch-card {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  max-width: 720px;
  margin-top: 18px;
  padding: 18px;
  border: 1px solid rgba(255, 36, 66, 0.16);
  border-radius: 20px;
  background: #fff8f9;
}

.mode-switch-card span,
.mode-switch-card strong,
.mode-switch-card p {
  display: block;
}

.mode-switch-card span {
  color: #ff2442;
  font-size: 13px;
  font-weight: 900;
  margin-bottom: 4px;
}

.mode-switch-card strong {
  color: #241d1f;
  font-size: 17px;
}

.mode-switch-card p {
  margin: 6px 0 0;
  color: #82686d;
  font-size: 14px;
}

.mode-switch-card button {
  flex: 0 0 auto;
  min-height: 44px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  background: #111;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.mode-switch-card button:hover {
  transform: translateY(-2px);
}

.preview-zone {
  position: relative;
  min-height: 460px;
  display: grid;
  place-items: center;
}

.floating-card {
  position: absolute;
  z-index: 2;
  width: 178px;
  padding: 14px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(255, 36, 66, 0.12);
  box-shadow: 0 14px 30px rgba(55, 28, 32, 0.1);
  animation: floatCard 4.6s ease-in-out infinite;
}

.floating-card span,
.floating-card strong {
  display: block;
}

.floating-card span {
  color: #ff2442;
  font-size: 12px;
  font-weight: 800;
  margin-bottom: 4px;
}

.floating-card strong {
  color: #2b2022;
  font-size: 15px;
  line-height: 1.35;
}

.idea-card {
  top: 18px;
  left: -18px;
}

.hot-card {
  right: -24px;
  bottom: 78px;
  animation-delay: -1.8s;
}

.phone-preview {
  width: 100%;
  max-width: 286px;
  justify-self: center;
  padding: 14px;
  border: 9px solid #171717;
  border-radius: 32px;
  background: #fff;
  box-shadow: 0 24px 52px rgba(30, 30, 30, 0.16);
  transform: rotate(2deg);
  animation: phoneEnter 0.8s ease 0.12s both;
}

.phone-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px 14px;
  color: #777;
  font-size: 12px;
}

.phone-top span {
  width: 42px;
  height: 4px;
  border-radius: 999px;
  background: #ececec;
}

.note-cover {
  min-height: 260px;
  padding: 20px;
  border-radius: 20px;
  background:
    radial-gradient(circle at 20% 18%, rgba(255, 255, 255, 0.35), transparent 24%),
    radial-gradient(circle at 86% 8%, rgba(255, 221, 99, 0.36), transparent 24%),
    linear-gradient(145deg, rgba(255, 36, 66, 0.96), rgba(255, 125, 104, 0.9));
  color: #fff;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  overflow: hidden;
  position: relative;
}

.note-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.28) 42%, transparent 62%);
  transform: translateX(-120%);
  animation: coverShine 3.8s ease-in-out infinite;
}

.cover-badge {
  position: relative;
  z-index: 1;
  width: max-content;
  margin-bottom: auto;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.22);
  font-size: 12px;
  font-weight: 800;
}

.note-cover h2 {
  position: relative;
  z-index: 1;
  margin: 0 0 10px;
  font-size: 29px;
  line-height: 1.08;
  letter-spacing: 0;
}

.note-cover p {
  position: relative;
  z-index: 1;
  margin: 0;
  opacity: 0.9;
}

.inspiration-strip,
.workflow-card,
.trend-panel {
  border: 1px solid #f1eeee;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 14px 38px rgba(33, 20, 20, 0.05);
}

.inspiration-strip {
  margin-top: 24px;
  padding: 22px 0;
  overflow: hidden;
}

.strip-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 0 26px 16px;
}

.strip-title span,
.workflow-header span,
.trend-header span {
  color: #ff2442;
  font-size: 13px;
  font-weight: 900;
}

.strip-title strong,
.workflow-header strong,
.trend-header strong {
  color: #252020;
  font-size: 18px;
}

.marquee-row {
  overflow: hidden;
}

.marquee-track {
  display: flex;
  gap: 12px;
  width: max-content;
  animation: marqueeMove 24s linear infinite;
}

.marquee-track span {
  padding: 10px 16px;
  border-radius: 999px;
  background: #fff3f5;
  color: #ff2442;
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
}

.workflow-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 18px;
  margin-top: 24px;
}

.workflow-card,
.trend-panel {
  padding: 24px;
}

.workflow-header,
.trend-header {
  display: grid;
  gap: 4px;
  margin-bottom: 18px;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.workflow-step {
  position: relative;
  min-height: 180px;
  padding: 18px;
  border-radius: 22px;
  background: #fff7f8;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.workflow-step:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 30px rgba(255, 36, 66, 0.12);
}

.workflow-step.active {
  background: #ff2442;
  color: #fff;
}

.workflow-step span {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  margin-bottom: 16px;
  border-radius: 50%;
  background: #fff;
  color: #ff2442;
  font-weight: 900;
}

.workflow-step strong {
  display: block;
  margin-bottom: 8px;
  font-size: 18px;
}

.workflow-step p {
  margin: 0;
  color: #856a70;
  line-height: 1.7;
}

.workflow-step.active p {
  color: rgba(255, 255, 255, 0.84);
}

.trend-panel {
  display: grid;
  align-content: start;
  gap: 10px;
}

.trend-panel button {
  display: grid;
  grid-template-columns: 42px 1fr auto;
  gap: 10px;
  align-items: center;
  width: 100%;
  padding: 14px;
  border: 1px solid #f3dfe3;
  border-radius: 18px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}

.trend-panel button:hover {
  border-color: rgba(255, 36, 66, 0.3);
  background: #fff7f8;
  transform: translateX(3px);
}

.trend-panel button span {
  color: #ff2442;
  font-weight: 900;
}

.trend-panel button strong {
  min-width: 0;
  color: #2b2022;
  font-size: 14px;
  line-height: 1.4;
}

.trend-panel button em {
  color: #a98a90;
  font-size: 12px;
  font-style: normal;
}

.note-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 14px 4px 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #ff2442;
  color: #fff;
  font-weight: 900;
}

.note-meta strong,
.note-meta span {
  display: block;
}

.note-meta strong {
  color: #222;
  font-size: 14px;
}

.note-meta span {
  color: #999;
  font-size: 12px;
}

.note-lines {
  display: grid;
  gap: 8px;
  padding: 4px;
}

.note-lines span {
  height: 9px;
  border-radius: 999px;
  background: #f1f1f1;
}

.note-lines span:nth-child(2) {
  width: 82%;
}

.note-lines span:nth-child(3) {
  width: 54%;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
}

.feature-card {
  padding: 24px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #f1eeee;
  box-shadow: 0 14px 38px rgba(33, 20, 20, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 48px rgba(255, 36, 66, 0.11);
}

.feature-icon {
  color: #ff2442;
  font-size: 28px;
  font-weight: 900;
}

.feature-card h3 {
  margin: 12px 0 8px;
  color: #222;
  font-size: 20px;
}

.feature-card p {
  margin: 0;
  color: #777;
  line-height: 1.7;
}

.error-toast {
  position: fixed;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 999px;
  background: #ff2442;
  color: #fff;
  box-shadow: 0 14px 32px rgba(255, 36, 66, 0.26);
}

@media (max-width: 980px) {
  .hero-card,
  .workflow-section {
    grid-template-columns: 1fr;
    padding: 32px;
  }

  .workflow-section {
    padding: 0;
  }

  .workflow-steps {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero-card {
    padding: 22px;
    border-radius: 24px;
  }

  .page-title {
    font-size: 40px;
  }

  .creator-stats {
    grid-template-columns: 1fr;
  }

  .quota-notice {
    align-items: flex-start;
    flex-direction: column;
  }

  .quota-notice strong {
    margin-left: 0;
  }

  .mode-switch-card {
    display: grid;
  }

  .preview-zone {
    min-height: 460px;
  }

  .floating-card {
    display: none;
  }
}

@keyframes riseIn {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes phoneEnter {
  from {
    opacity: 0;
    transform: translateY(24px) rotate(-2deg);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotate(2deg);
  }
}

@keyframes floatCard {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-12px);
  }
}

@keyframes coverShine {
  0%, 48% {
    transform: translateX(-120%);
  }
  72%, 100% {
    transform: translateX(120%);
  }
}

@keyframes marqueeMove {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(-50%);
  }
}

@keyframes floatGlow {
  0%, 100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(18px, -18px, 0) scale(1.08);
  }
}

@keyframes progressShine {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(100%);
  }
}
</style>
