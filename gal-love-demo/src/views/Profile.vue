<template>
  <div class="profile-container" v-loading="loading">
    <div class="profile-header">
      <el-card class="user-info-card">
        <div class="user-info">
          <el-avatar :size="100" :src="userInfo.avatar" />
          <div class="user-details">
            <h2>{{ userInfo.username }}</h2>
            <p>{{ userInfo.email }}</p>
            <el-button type="primary" @click="showEditDialog = true">
              编辑资料
            </el-button>
          </div>
        </div>

        <div class="user-stats">
          <div class="stat-item">
            <h3>{{ userStats.gamesCollected }}</h3>
            <p>收藏游戏</p>
          </div>
          <div class="stat-item">
            <h3>{{ userStats.reviewsWritten }}</h3>
            <p>游戏评价</p>
          </div>
          <div class="stat-item">
            <h3>{{ userStats.totalPlayTime }}h</h3>
            <p>总游戏时长</p>
          </div>
        </div>
      </el-card>
    </div>

    <div class="profile-content">
      <el-tabs v-model="activeTab" class="profile-tabs">
        <el-tab-pane label="我的收藏" name="collections">
          <div class="games-grid">
            <el-empty v-if="!collections.length" description="暂无收藏的游戏" />
            <el-card
              v-for="game in collections"
              :key="game.id"
              class="game-card"
              @click="handleGameClick(game.id)"
            >
              <img :src="game.coverImage" :alt="game.title" class="game-cover" />
              <div class="game-info">
                <h3>{{ game.title }}</h3>
                <div class="game-meta">
                  <el-rate v-model="game.rating" disabled />
                  <span class="collection-date">
                    收藏于 {{ game.collectedAt }}
                  </span>
                </div>
                <el-button
                  type="danger"
                  size="small"
                  @click.stop="handleRemoveCollection(game.id)"
                >
                  取消收藏
                </el-button>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="我的评价" name="reviews">
          <div class="reviews-list">
            <el-empty v-if="!reviews.length" description="暂无游戏评价" />
            <el-card
              v-for="review in reviews"
              :key="review.id"
              class="review-card"
            >
              <div class="review-header">
                <img
                  :src="review.gameCover"
                  :alt="review.gameTitle"
                  class="review-game-cover"
                  @click="handleGameClick(review.gameId)"
                />
                <div class="review-info">
                  <h3 @click="handleGameClick(review.gameId)">
                    {{ review.gameTitle }}
                  </h3>
                  <el-rate v-model="review.rating" disabled />
                  <span class="review-date">
                    评价于 {{ review.createdAt }}
                  </span>
                </div>
              </div>
              <div class="review-content">
                {{ review.content }}
              </div>
              <div class="review-actions">
                <el-button
                  type="primary"
                  size="small"
                  @click="handleEditReview(review)"
                >
                  编辑评价
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  @click="handleDeleteReview(review.id)"
                >
                  删除评价
                </el-button>
              </div>
            </el-card>
          </div>
        </el-tab-pane>

        <el-tab-pane label="推荐游戏" name="recommendations">
          <div class="recommendations-grid">
            <el-empty v-if="!recommendations.length" description="暂无推荐游戏" />
            <el-card
              v-for="game in recommendations"
              :key="game.id"
              class="game-card"
              @click="handleGameClick(game.id)"
            >
              <img :src="game.coverImage" :alt="game.title" class="game-cover" />
              <div class="game-info">
                <h3>{{ game.title }}</h3>
                <el-rate v-model="game.rating" disabled />
                <p class="recommendation-reason">
                  {{ game.recommendReason }}
                </p>
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑个人资料对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑个人资料"
      width="30%"
    >
      <el-form
        :model="editForm"
        :rules="editRules"
        ref="editFormRef"
        label-width="80px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" />
        </el-form-item>
        <el-form-item label="头像">
          <el-upload
            class="avatar-uploader"
            action="/api/upload"
            :show-file-list="false"
            :on-success="handleAvatarSuccess"
          >
            <img v-if="editForm.avatar" :src="editForm.avatar" class="avatar" />
            <el-icon v-else class="avatar-uploader-icon"><plus /></el-icon>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="handleUpdateProfile">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑评价对话框 -->
    <el-dialog
      v-model="showReviewDialog"
      title="编辑评价"
      width="40%"
    >
      <div class="edit-review-form">
        <h3>{{ currentReview?.gameTitle }}</h3>
        <el-rate
          v-model="editReviewForm.rating"
          show-score
        />
        <el-input
          v-model="editReviewForm.content"
          type="textarea"
          :rows="4"
          placeholder="写下你的评价"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showReviewDialog = false">取消</el-button>
          <el-button type="primary" @click="handleSaveReview">
            保存
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, getCurrentInstance } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useUserStore } from '../store/user'
import type { FormInstance, FormRules } from 'element-plus'

const internalInstance = getCurrentInstance()
const router = internalInstance?.proxy?.$router
const userStore = useUserStore()
const loading = ref(false)
const activeTab = ref('collections')
const showEditDialog = ref(false)
const showReviewDialog = ref(false)
const editFormRef = ref<FormInstance>()

// 用户基本信息
const userInfo = ref({
  username: '示例用户',
  email: 'example@email.com',
  avatar: 'https://via.placeholder.com/100'
})

// 用户统计数据
const userStats = ref({
  gamesCollected: 12,
  reviewsWritten: 5,
  totalPlayTime: 100
})

// 收藏的游戏列表
const collections = ref<any[]>([])

// 游戏评价列表
const reviews = ref<any[]>([])

// 推荐游戏列表
const recommendations = ref<any[]>([])

// 编辑表单
const editForm = ref({
  username: '',
  avatar: ''
})

const editRules = ref<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度至少为3个字符', trigger: 'blur' }
  ]
})

// 当前编辑的评价
const currentReview = ref(null)
const editReviewForm = ref({
  rating: 0,
  content: ''
})

// 初始化数据
const initializeData = async () => {
  loading.value = true
  try {
    // 获取用户信息
    const userData = userStore.userInfo;
    if (!userData) {
      await userStore.initUserState();
    }
    // 使用实际的用户数据
    userInfo.value = {
      username: userStore.userInfo?.username || '',
      email: userStore.userInfo?.email || '',
      avatar: userStore.userInfo?.avatar || 'https://via.placeholder.com/100'
    };
    // 初始化用户统计数据
    userStats.value = {
      gamesCollected: 0,
      reviewsWritten: 0,
      totalPlayTime: 0
    };
    // 初始化空列表
    collections.value = [];
    reviews.value = [{
      id: 1,
      gameId: 1,
      gameTitle: '示例游戏',
      gameCover: 'https://via.placeholder.com/100x140',
      rating: 4.5,
      content: '这是一条示例评价内容，描述了对游戏的感受...',
      createdAt: '2025-05-22'
    }];
    // 模拟推荐游戏数据
    recommendations.value = Array(6).fill(null).map((_, index) => ({
      id: index + 100,
      title: `推荐游戏 ${index + 1}`,
      coverImage: 'https://via.placeholder.com/200x280',
      rating: 4 + Math.random(),
      recommendReason: '根据你喜欢的xxx游戏推荐'
    }));
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

// 处理游戏点击
const handleGameClick = (gameId: number) => {
  router?.push(`/games/${gameId}`)
}

// 处理取消收藏
const handleRemoveCollection = async (gameId: number) => {
  try {
    await ElMessageBox.confirm('确定要取消收藏这个游戏吗？', '提示', {
      type: 'warning'
    })
    // TODO: 实现实际的取消收藏API调用
    collections.value = collections.value.filter(game => game.id !== gameId)
    ElMessage.success('已取消收藏')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消收藏失败:', error)
      ElMessage.error('取消收藏失败')
    }
  }
}

// 处理头像上传成功
const handleAvatarSuccess = (response: any) => {
  editForm.value.avatar = response.url
}

// 处理更新个人资料
const handleUpdateProfile = async () => {
  if (!editFormRef.value) return

  try {
    await editFormRef.value.validate()
    // TODO: 实现实际的更新个人资料API调用
    Object.assign(userInfo.value, editForm.value)
    showEditDialog.value = false
    ElMessage.success('个人资料更新成功')
  } catch (error) {
    console.error('更新个人资料失败:', error)
    ElMessage.error('更新个人资料失败')
  }
}

// 处理编辑评价
const handleEditReview = (review: any) => {
  currentReview.value = review
  editReviewForm.value = {
    rating: review.rating,
    content: review.content
  }
  showReviewDialog.value = true
}

// 处理保存评价
const handleSaveReview = async () => {
  try {
    // TODO: 实现实际的更新评价API调用
    const index = reviews.value.findIndex(r => r.id === currentReview.value?.id)
    if (index !== -1) {
      reviews.value[index] = {
        ...reviews.value[index],
        ...editReviewForm.value
      }
    }
    showReviewDialog.value = false
    ElMessage.success('评价更新成功')
  } catch (error) {
    console.error('更新评价失败:', error)
    ElMessage.error('更新评价失败')
  }
}

// 处理删除评价
const handleDeleteReview = async (reviewId: number) => {
  try {
    await ElMessageBox.confirm('确定要删除这条评价吗？', '提示', {
      type: 'warning'
    })
    // TODO: 实现实际的删除评价API调用
    reviews.value = reviews.value.filter(review => review.id !== reviewId)
    ElMessage.success('评价已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除评价失败:', error)
      ElMessage.error('删除评价失败')
    }
  }
}

// 组件挂载时初始化数据
onMounted(() => {
  initializeData()
  // 初始化编辑表单
  editForm.value = {
    username: userInfo.value.username,
    avatar: userInfo.value.avatar
  }
})
</script>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.profile-header {
  margin-bottom: 30px;
}

.user-info-card {
  background: #fff;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 30px;
  margin-bottom: 30px;
}

.user-details {
  flex: 1;
}

.user-details h2 {
  margin: 0 0 10px;
}

.user-details p {
  margin: 0 0 20px;
  color: #666;
}

.user-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  text-align: center;
}

.stat-item h3 {
  margin: 0;
  font-size: 1.5em;
  color: #409EFF;
}

.stat-item p {
  margin: 5px 0 0;
  color: #666;
}

.profile-content {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
}

.profile-tabs {
  padding: 20px;
}

.games-grid,
.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.game-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.game-card:hover {
  transform: translateY(-5px);
}

.game-cover {
  width: 100%;
  height: 280px;
  object-fit: cover;
  border-radius: 4px;
}

.game-info {
  margin-top: 10px;
}

.game-info h3 {
  margin: 0 0 10px;
  font-size: 1.1em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-meta {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 10px;
}

.collection-date {
  font-size: 0.9em;
  color: #909399;
}

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.review-card {
  margin-bottom: 20px;
}

.review-header {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.review-game-cover {
  width: 100px;
  height: 140px;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
}

.review-info {
  flex: 1;
}

.review-info h3 {
  margin: 0 0 10px;
  cursor: pointer;
}

.review-info h3:hover {
  color: #409EFF;
}

.review-date {
  font-size: 0.9em;
  color: #909399;
}

.review-content {
  margin: 15px 0;
  line-height: 1.6;
}

.review-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.recommendation-reason {
  margin: 10px 0 0;
  font-size: 0.9em;
  color: #666;
}

.avatar-uploader {
  display: flex;
  justify-content: center;
}

.avatar {
  width: 100px;
  height: 100px;
  border-radius: 50%;
}

.avatar-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 100px;
  height: 100px;
  line-height: 100px;
  text-align: center;
  border: 1px dashed #d9d9d9;
  border-radius: 50%;
}

.edit-review-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.edit-review-form h3 {
  margin: 0;
}
</style>
