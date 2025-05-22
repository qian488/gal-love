<template>
  <div class="home-container">
    <div class="hero-section">
      <div class="hero-content">
        <h1>Gal Love</h1>
        <p>发现你的下一个最爱游戏</p>
        <div style="margin-top: 32px;">
          <el-input v-model="searchQuery" placeholder="搜索游戏..." style="width: 240px; margin-right: 12px;" @keyup.enter="handleSearch" />
          <el-button type="primary" @click="handleSearch">搜索</el-button>
        </div>
      </div>
    </div>

    <div class="content-section">
      <div class="recommendation-cards">
        <el-card 
          v-for="game in featuredGames" 
          :key="game.id"
          class="game-card"
          @click="navigateToGame(game.id)"
        >
          <div class="card-content">
            <div class="card-header">
              <img :src="game.coverImage" :alt="game.title" class="game-cover" />
              <div class="game-info">
                <h2>{{ game.title }}</h2>
                <p class="game-meta">{{ game.developer }} | {{ game.releaseDate }}</p>
                <div class="game-tags">
                  <el-tag 
                    v-for="tag in game.tags" 
                    :key="tag"
                    size="small"
                    class="game-tag"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
              </div>
            </div>
            <div class="game-description">
              {{ game.description }}
            </div>
            <div class="game-rating">
              <el-rate v-model="game.rating" disabled show-score />
              <span class="rating-count">({{ game.totalRatings }}人评分)</span>
            </div>
          </div>
        </el-card>
      </div>

      <div class="section-divider">
        <h2>热门推荐</h2>
        <el-button type="primary" text @click="$router.push('/games')">
          查看更多 <el-icon><arrow-right /></el-icon>
        </el-button>
      </div>

      <div class="popular-games">
        <el-carousel :interval="4000" type="card" height="400px">
          <el-carousel-item v-for="game in popularGames" :key="game.id">
            <div class="carousel-game" @click="navigateToGame(game.id)">
              <img :src="game.coverImage" :alt="game.title" />
              <div class="carousel-content">
                <h3>{{ game.title }}</h3>
                <p>{{ game.description }}</p>
              </div>
            </div>
          </el-carousel-item>
        </el-carousel>
      </div>

      <div class="section-divider">
        <h2>最新发布</h2>
        <el-button type="primary" text @click="$router.push('/games')">
          查看更多 <el-icon><arrow-right /></el-icon>
        </el-button>
      </div>

      <div class="new-releases">
        <el-row :gutter="20">
          <el-col 
            v-for="game in newReleases" 
            :key="game.id" 
            :xs="12" 
            :sm="8" 
            :md="6"
          >
            <el-card 
              class="new-game-card"
              @click="navigateToGame(game.id)"
              :body-style="{ padding: '0px' }"
            >
              <img :src="game.coverImage" :alt="game.title" class="new-game-image"/>
              <div class="new-game-info">
                <h3>{{ game.title }}</h3>
                <div class="new-game-meta">
                  <el-rate v-model="game.rating" disabled />
                  <span>{{ game.releaseDate }}</span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, getCurrentInstance } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'

const searchQuery = ref('')

// 模拟特色游戏数据
const featuredGames = ref([
  {
    id: 1,
    title: '星空的记忆',
    developer: 'Love Game Studio',
    releaseDate: '2025-05-01',
    coverImage: 'https://via.placeholder.com/300x400',
    description: '在未来科技与浪漫交织的世界中，探索一段跨越时空的爱情故事...',
    tags: ['科幻', '恋爱', '剧情'],
    rating: 4.8,
    totalRatings: 1234
  },
  {
    id: 2,
    title: '樱花校园物语',
    developer: 'Cherry Blossom Games',
    releaseDate: '2025-04-15',
    coverImage: 'https://via.placeholder.com/300x400',
    description: '在充满青春气息的校园中，邂逅各具特色的同学，编织属于你的校园恋爱故事...',
    tags: ['校园', '日常', '恋爱'],
    rating: 4.6,
    totalRatings: 856
  }
])

// 模拟热门游戏数据
const popularGames = ref([
  {
    id: 3,
    title: '魔法少女的秘密',
    coverImage: 'https://via.placeholder.com/800x400',
    description: '在现代都市中邂逅魔法，成为守护和平的魔法少女...'
  },
  {
    id: 4,
    title: '千年之恋',
    coverImage: 'https://via.placeholder.com/800x400',
    description: '穿越千年时空，寻找命中注定的那个人...'
  },
  {
    id: 5,
    title: '未来都市恋曲',
    coverImage: 'https://via.placeholder.com/800x400',
    description: '在赛博朋克风格的未来都市中，展开一段跨越人机界限的爱情...'
  }
])

// 模拟最新发布游戏数据
const newReleases = ref([
  {
    id: 6,
    title: '梦境探险家',
    coverImage: 'https://via.placeholder.com/200x300',
    rating: 4.5,
    releaseDate: '2025-05-20'
  },
  {
    id: 7,
    title: '平行世界的你',
    coverImage: 'https://via.placeholder.com/200x300',
    rating: 4.7,
    releaseDate: '2025-05-18'
  },
  {
    id: 8,
    title: '古典音乐恋歌',
    coverImage: 'https://via.placeholder.com/200x300',
    rating: 4.6,
    releaseDate: '2025-05-15'
  },
  {
    id: 9,
    title: '人工智能爱恋',
    coverImage: 'https://via.placeholder.com/200x300',
    rating: 4.8,
    releaseDate: '2025-05-10'
  }
])

const internalInstance = getCurrentInstance()
const $router = internalInstance?.proxy?.$router

const handleSearch = () => {
  if (searchQuery.value.trim() && $router) {
    $router.push({ path: '/games', query: { search: searchQuery.value } })
  }
}

const navigateToGame = (gameId: number) => {
  if ($router) {
    $router.push(`/games/${gameId}`)
  }
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
}

.hero-section {
  height: 500px;
  background-image: url('https://via.placeholder.com/1920x500');
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  position: relative;
  margin-bottom: 40px;
}

.hero-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.hero-content {
  position: relative;
  text-align: center;
  z-index: 1;
  max-width: 600px;
  padding: 0 20px;
}

.hero-content h1 {
  font-size: 3em;
  margin-bottom: 20px;
}

.hero-content p {
  font-size: 1.2em;
  margin-bottom: 30px;
}

.search-input {
  width: 100%;
}

.content-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.recommendation-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 40px;
}

.game-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.game-card:hover {
  transform: translateY(-5px);
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.card-header {
  display: flex;
  gap: 20px;
}

.game-cover {
  width: 200px;
  height: 280px;
  object-fit: cover;
  border-radius: 8px;
}

.game-info {
  flex: 1;
}

.game-info h2 {
  margin: 0 0 10px;
  font-size: 1.5em;
}

.game-meta {
  color: #666;
  margin-bottom: 10px;
}

.game-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.game-description {
  color: #666;
  line-height: 1.6;
}

.game-rating {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rating-count {
  color: #909399;
}

.section-divider {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 40px 0 20px;
}

.section-divider h2 {
  margin: 0;
}

.carousel-game {
  height: 100%;
  cursor: pointer;
  position: relative;
}

.carousel-game img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

.carousel-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 20px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  color: white;
  border-radius: 0 0 8px 8px;
}

.carousel-content h3 {
  margin: 0 0 10px;
}

.carousel-content p {
  margin: 0;
  opacity: 0.8;
}

.new-game-card {
  cursor: pointer;
  transition: transform 0.3s;
  margin-bottom: 20px;
}

.new-game-card:hover {
  transform: translateY(-5px);
}

.new-game-image {
  width: 100%;
  height: 280px;
  object-fit: cover;
}

.new-game-info {
  padding: 15px;
}

.new-game-info h3 {
  margin: 0 0 10px;
  font-size: 1.1em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.new-game-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9em;
  color: #666;
}
</style>
