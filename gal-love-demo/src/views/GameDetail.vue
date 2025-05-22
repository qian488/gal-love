<template>
  <div class="game-detail" v-loading="loading">
    <template v-if="game">
      <div class="game-header">
        <el-image 
          :src="game.coverImage"
          :alt="game.title"
          class="game-cover"
          fit="cover"
        />
        <div class="game-info">
          <h1 class="game-title">{{ game.title }}</h1>
          <h2 class="game-original-title" v-if="game.originalTitle">
            {{ game.originalTitle }}
          </h2>
          
          <div class="game-rating">
            <el-rate
              v-model="game.rating"
              disabled
              show-score
              text-color="#ff9900"
              class="rating-stars"
            />
            <span class="rating-count">({{ game.totalRatings }}人评分)</span>
          </div>

          <div class="game-meta">
            <p><strong>开发商：</strong>{{ game.developer }}</p>
            <p><strong>发行商：</strong>{{ game.publisher }}</p>
            <p><strong>发售日期：</strong>{{ game.releaseDate }}</p>
            <p><strong>平台：</strong>{{ game.platform.join(', ') }}</p>
          </div>

          <div class="game-tags">
            <el-tag
              v-for="tag in game.tags"
              :key="tag"
              class="game-tag"
            >
              {{ tag }}
            </el-tag>
          </div>

          <div class="game-actions" v-if="userStore.isLoggedIn">
            <el-button type="primary" @click="handleAddToLibrary">
              <el-icon><plus /></el-icon>
              添加到收藏
            </el-button>
            <el-button @click="showRatingDialog = true">
              <el-icon><star /></el-icon>
              评分
            </el-button>
          </div>
        </div>
      </div>

      <el-tabs v-model="activeTab" class="game-tabs">
        <el-tab-pane label="游戏简介" name="description">
          <div class="game-description" v-html="game.description"></div>
        </el-tab-pane>

        <el-tab-pane label="玩家评价" name="reviews">
          <div class="game-reviews">
            <div v-if="reviews.length" class="reviews-list">
              <div v-for="review in reviews" :key="review.id" class="review-item">
                <el-avatar :src="review.userAvatar" />
                <div class="review-content">
                  <div class="review-header">
                    <span class="review-username">{{ review.username }}</span>
                    <el-rate v-model="review.rating" disabled />
                    <span class="review-date">{{ review.date }}</span>
                  </div>
                  <p class="review-text">{{ review.content }}</p>
                </div>
              </div>
            </div>
            <el-empty v-else description="暂无评价" />
          </div>
        </el-tab-pane>

        <el-tab-pane label="相似推荐" name="recommendations">
          <div class="game-recommendations">
            <div class="recommendations-grid">
              <el-card
                v-for="game in recommendations"
                :key="game.id"
                class="recommendation-card"
                @click="handleGameClick(game.id)"
              >
                <img :src="game.coverImage" :alt="game.title" class="recommendation-cover" />
                <h3 class="recommendation-title">{{ game.title }}</h3>
                <el-rate v-model="game.rating" disabled />
              </el-card>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-dialog
      v-model="showRatingDialog"
      title="评分"
      width="30%"
    >
      <div class="rating-form">
        <el-rate
          v-model="userRating"
          show-score
          :max="5"
        />
        <el-input
          v-model="userReview"
          type="textarea"
          :rows="4"
          placeholder="写下你的评价（可选）"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showRatingDialog = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitRating">
            提交评分
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, getCurrentInstance } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Star } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'
import type { Game } from '../types/game'

const internalInstance = getCurrentInstance()
const router = internalInstance?.proxy?.$router
const route = internalInstance?.proxy?.$route
const userStore = useUserStore()

const loading = ref(true)
const game = ref<Game | null>(null)
const activeTab = ref('description')
const reviews = ref<any[]>([])
const recommendations = ref<any[]>([])
const showRatingDialog = ref(false)
const userRating = ref(0)
const userReview = ref('')

// 模拟加载游戏数据
const loadGameData = async () => {
  loading.value = true
  try {
    // TODO: 实现实际的API调用
    await new Promise(resolve => setTimeout(resolve, 1000))
    game.value = {
      id: Number(route?.params.id),
      title: '示例游戏',
      originalTitle: 'Sample Game',
      coverImage: 'https://via.placeholder.com/500x700',
      description: '这是一个示例游戏的详细描述，包含了游戏的背景故事、玩法特点等信息...',
      developer: '示例开发商',
      publisher: '示例发行商',
      releaseDate: '2025-01-01',
      tags: ['恋爱', '校园', '奇幻'],
      rating: 4.5,
      totalRatings: 100,
      platform: ['Windows', 'MacOS']
    }

    // 模拟评价数据
    reviews.value = Array(5).fill(null).map((_, index) => ({
      id: index + 1,
      username: `用户${index + 1}`,
      userAvatar: 'https://via.placeholder.com/40',
      rating: 4 + Math.random(),
      content: '这是一条示例评价内容，描述了玩家对游戏的感受和建议...',
      date: '2025-05-22'
    }))

    // 模拟推荐数据
    recommendations.value = Array(6).fill(null).map((_, index) => ({
      id: index + 100,
      title: `推荐游戏 ${index + 1}`,
      coverImage: 'https://via.placeholder.com/200x280',
      rating: 4 + Math.random()
    }))
  } catch (error) {
    console.error('加载游戏数据失败:', error)
    ElMessage.error('加载游戏数据失败')
  } finally {
    loading.value = false
  }
}

const handleAddToLibrary = () => {
  // TODO: 实现添加到收藏功能
  ElMessage.success('已添加到收藏')
}

const handleSubmitRating = () => {
  // TODO: 实现提交评分功能
  ElMessage.success('评分提交成功')
  showRatingDialog.value = false
  userRating.value = 0
  userReview.value = ''
}

const handleGameClick = (gameId: number) => {
  router?.push(`/games/${gameId}`)
}

onMounted(() => {
  loadGameData()
})
</script>

<style scoped>
.game-detail {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.game-header {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.game-cover {
  width: 300px;
  height: 400px;
  border-radius: 8px;
  overflow: hidden;
}

.game-info {
  flex: 1;
}

.game-title {
  margin: 0 0 10px;
  font-size: 2em;
}

.game-original-title {
  margin: 0 0 20px;
  font-size: 1.2em;
  color: #666;
}

.game-rating {
  margin-bottom: 20px;
}

.rating-stars {
  margin-right: 10px;
}

.rating-count {
  color: #909399;
}

.game-meta {
  margin-bottom: 20px;
}

.game-meta p {
  margin: 5px 0;
}

.game-tags {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.game-actions {
  display: flex;
  gap: 10px;
}

.game-tabs {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.game-description {
  line-height: 1.6;
}

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.review-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  border-bottom: 1px solid #eee;
}

.review-content {
  flex: 1;
}

.review-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.review-username {
  font-weight: bold;
}

.review-date {
  color: #909399;
}

.review-text {
  margin: 0;
  line-height: 1.5;
}

.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

.recommendation-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.recommendation-card:hover {
  transform: translateY(-5px);
}

.recommendation-cover {
  width: 100%;
  height: 250px;
  object-fit: cover;
  border-radius: 4px;
}

.recommendation-title {
  margin: 10px 0;
  font-size: 1em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rating-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
