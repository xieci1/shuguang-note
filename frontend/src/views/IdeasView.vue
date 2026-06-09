<template>
  <div class="ideas-page">
    <section class="ideas-hero">
      <div class="ideas-copy">
        <span class="ideas-kicker">批量作品模式</span>
        <h1>同一个话题，先做 5 个选题方向</h1>
        <p>不急着生图。先把一个大话题拆成不同作品角度，再挑最有感觉的方案继续生成完整图文。</p>
        <div class="mode-notes">
          <span>5 个独立作品</span>
          <span>不同人群切入</span>
          <span>可继续生成多页图文</span>
        </div>
      </div>

      <div class="ideas-preview">
        <div v-for="(item, idx) in previewCards" :key="item" class="preview-card" :style="{ '--delay': `${idx * 0.12}s` }">
          <span>0{{ idx + 1 }}</span>
          <strong>{{ item }}</strong>
        </div>
      </div>
    </section>

    <section class="ideas-input-card">
      <div class="input-head">
        <div>
          <span>输入大话题</span>
          <strong>先找 5 个可做成作品的角度</strong>
        </div>
        <button type="button" class="ghost-btn" @click="router.push('/')">返回主页</button>
      </div>
      <div class="input-box">
        <textarea
          v-model="topic"
          placeholder="例如：新手如何做小红书账号、通勤女生自我提升、低预算变美..."
          :disabled="loading"
        ></textarea>
        <button type="button" @click="handleGenerateIdeas" :disabled="!topic.trim() || loading">
          {{ loading ? '生成中...' : '生成 5 个方向' }}
        </button>
      </div>

      <div v-if="loading" class="ideas-progress" role="status" aria-live="polite">
        <div class="progress-head">
          <span>{{ progressStep }}</span>
          <strong>{{ generationProgress }}%</strong>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${generationProgress}%` }"></div>
        </div>
        <p>{{ progressHint }}</p>
      </div>
    </section>

    <div v-if="error" class="ideas-error">{{ error }}</div>

    <section v-if="ideas.length > 0" class="ideas-grid">
      <article v-for="(idea, idx) in ideas" :key="`${idea.title}-${idx}`" class="idea-card">
        <div class="idea-rank">方案 {{ idx + 1 }}</div>
        <h2>{{ idea.title }}</h2>
        <dl>
          <div>
            <dt>切入角度</dt>
            <dd>{{ idea.angle || '围绕用户痛点展开' }}</dd>
          </div>
          <div>
            <dt>目标人群</dt>
            <dd>{{ idea.audience || '小红书内容创作者' }}</dd>
          </div>
          <div>
            <dt>封面钩子</dt>
            <dd>{{ idea.hook || idea.title }}</dd>
          </div>
        </dl>
        <button type="button" @click="useIdea(idea)">用这个方案生成完整图文</button>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { generateTopicIdeas, generateOutline, type TopicIdea } from '../api'
import { useGeneratorStore } from '../stores/generator'
import { useDraftAutosave } from '../composables/useDraftAutosave'

const router = useRouter()
const store = useGeneratorStore()
const { ensureDraftSaved } = useDraftAutosave({ watchOutline: false })

const topic = ref('')
const ideas = ref<TopicIdea[]>([])
const loading = ref(false)
const error = ref('')
const generationProgress = ref(0)
const progressStep = ref('')
const progressHint = ref('')
let progressTimer: ReturnType<typeof setInterval> | null = null

const previewCards = [
  '痛点教程',
  '清单种草',
  '避坑经验',
  '成长记录',
  '场景攻略'
]

const ideaProgressSteps = [
  { at: 10, label: '正在分析大话题', hint: '先找出这个话题里可拆分的人群、场景和痛点。' },
  { at: 30, label: '正在拆 5 个方向', hint: '每个方向都会尽量保持独立，不只是换一个标题。' },
  { at: 56, label: '正在补封面钩子', hint: '给每个选题补上适合小红书的开头和卖点。' },
  { at: 78, label: '正在整理方案卡片', hint: '把切入角度、目标人群和提示词整理成可继续生成的方案。' },
  { at: 91, label: '马上完成', hint: '最后检查数量和格式，完成后会展示 5 个可选作品。' }
]

const outlineProgressSteps = [
  { at: 8, label: '正在读取所选方案', hint: '把这个选题转成完整作品的创作要求。' },
  { at: 30, label: '正在生成多页大纲', hint: '继续走原模式：一个选题生成一个完整图文作品。' },
  { at: 58, label: '正在细化每页内容', hint: '补齐封面、内容页和收尾页的文案与画面方向。' },
  { at: 82, label: '正在保存草稿', hint: '生成成功后会自动跳到大纲编辑页。' },
  { at: 92, label: '马上进入编辑', hint: '正在准备下一步页面。' }
]

function startProgress(steps = ideaProgressSteps) {
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
  progressHint.value = '已经生成完成，正在更新页面。'
}

function stopProgress() {
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

async function handleGenerateIdeas() {
  if (!topic.value.trim()) return

  loading.value = true
  error.value = ''
  ideas.value = []
  startProgress(ideaProgressSteps)

  try {
    const result = await generateTopicIdeas(topic.value.trim(), 5)
    if (result.success && result.ideas?.length) {
      finishProgress('5 个方向已生成')
      ideas.value = result.ideas
    } else {
      error.value = result.error || '生成选题方案失败'
    }
  } catch (err: any) {
    error.value = err.message || '网络错误，请重试'
  } finally {
    stopProgress()
    loading.value = false
  }
}

async function useIdea(idea: TopicIdea) {
  loading.value = true
  error.value = ''
  startProgress(outlineProgressSteps)

  try {
    const selectedPrompt = idea.prompt || idea.title
    const result = await generateOutline(selectedPrompt)

    if (result.success && result.pages) {
      store.reset()
      store.setTopic(selectedPrompt)
      store.setOutline(result.outline || '', result.pages)
      await ensureDraftSaved()

      finishProgress('完整图文已生成')
      router.push('/outline')
    } else {
      error.value = result.error || '生成完整大纲失败'
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
.ideas-page {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
}

.ideas-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 34px;
  align-items: center;
  padding: 38px;
  border-radius: 28px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(255, 248, 249, 0.96)),
    radial-gradient(circle at 12% 12%, rgba(255, 36, 66, 0.1), transparent 26%);
  border: 1px solid rgba(255, 36, 66, 0.1);
  box-shadow: 0 18px 54px rgba(72, 28, 34, 0.07);
}

.ideas-kicker {
  display: inline-flex;
  margin-bottom: 14px;
  padding: 6px 12px;
  border-radius: 999px;
  background: #fff0f2;
  color: #ff2442;
  font-size: 13px;
  font-weight: 800;
}

.ideas-hero h1 {
  max-width: 680px;
  margin: 0;
  color: #222;
  font-size: clamp(32px, 4.5vw, 54px);
  line-height: 1.14;
  font-weight: 800;
  letter-spacing: 0;
}

.ideas-hero p {
  max-width: 620px;
  margin: 16px 0 0;
  color: #706367;
  font-size: 16px;
  line-height: 1.8;
}

.mode-notes {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.mode-notes span {
  padding: 8px 12px;
  border: 1px solid #f2dce0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.76);
  color: #8a6e73;
  font-size: 13px;
  font-weight: 700;
}

.ideas-preview {
  display: grid;
  gap: 12px;
}

.preview-card {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 60px;
  padding: 14px 16px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid #f1eeee;
  box-shadow: 0 12px 28px rgba(33, 20, 20, 0.05);
  animation: cardFloat 3.6s ease-in-out infinite;
  animation-delay: var(--delay);
}

.preview-card:nth-child(even) {
  transform: translateX(18px);
}

.preview-card span {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff0f2;
  color: #ff2442;
  font-size: 12px;
  font-weight: 900;
}

.preview-card strong {
  color: #2b2022;
  font-size: 15px;
}

.ghost-btn,
.ideas-input-card button,
.idea-card button {
  border: none;
  border-radius: 999px;
  background: #ff2442;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.ghost-btn {
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid #f2dce0;
  background: #fff;
  color: #ff2442;
}

.ideas-input-card {
  display: grid;
  gap: 16px;
  margin-top: 20px;
  padding: 20px;
  border-radius: 24px;
  background: #fff;
  border: 1px solid #f1eeee;
  box-shadow: 0 14px 34px rgba(33, 20, 20, 0.045);
}

.input-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.input-head span,
.input-head strong {
  display: block;
}

.input-head span {
  color: #ff2442;
  font-size: 13px;
  font-weight: 900;
}

.input-head strong {
  color: #2b2022;
  font-size: 18px;
}

.input-box {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px;
  align-items: end;
}

.ideas-input-card textarea {
  width: 100%;
  min-height: 112px;
  resize: vertical;
  border: none;
  outline: none;
  border-radius: 20px;
  background: #fff8f9;
  padding: 18px;
  color: #222;
  font: inherit;
  line-height: 1.7;
}

.ideas-input-card button {
  min-height: 48px;
  padding: 0 24px;
}

.ideas-progress {
  padding: 16px;
  border: 1px solid rgba(255, 36, 66, 0.14);
  border-radius: 20px;
  background: linear-gradient(135deg, #fff8f9, #fff);
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

.ideas-progress p {
  margin: 10px 0 0;
  color: #80686d;
  font-size: 13px;
  line-height: 1.6;
}

.ideas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin-top: 22px;
}

.idea-card {
  display: flex;
  flex-direction: column;
  min-height: 390px;
  padding: 22px;
  border-radius: 22px;
  background: #fff;
  border: 1px solid #f1eeee;
  box-shadow: 0 14px 38px rgba(33, 20, 20, 0.05);
}

.idea-rank {
  color: #ff2442;
  font-size: 13px;
  font-weight: 900;
}

.idea-card h2 {
  margin: 10px 0 16px;
  color: #222;
  font-size: 20px;
  line-height: 1.38;
  font-weight: 800;
}

.idea-card dl {
  display: grid;
  gap: 12px;
  margin: 0 0 18px;
}

.idea-card dt {
  color: #ff2442;
  font-size: 12px;
  font-weight: 900;
}

.idea-card dd {
  margin: 4px 0 0;
  color: #6f5b5f;
  line-height: 1.65;
}

.idea-card button {
  margin-top: auto;
  min-height: 44px;
}

.ideas-error {
  margin-top: 16px;
  padding: 14px 16px;
  border-radius: 18px;
  background: #fff0f2;
  color: #d91c36;
  font-weight: 700;
}

@media (max-width: 760px) {
  .ideas-hero {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .input-box {
    grid-template-columns: 1fr;
  }
}

@keyframes cardFloat {
  0%, 100% {
    translate: 0 0;
  }
  50% {
    translate: 0 -5px;
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
