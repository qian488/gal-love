import axios from 'axios'
import type { 
  ApiResponse, 
  LoginResponse, 
  UserInfo, 
  RegisterData,
  UpdateProfileData,
  Game,
  GameListResponse,
  GameListParams 
} from '../types/api'

// 创建axios实例
const api = axios.create({
  baseURL: '/api',  // 使用相对路径，让vite的代理来处理
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true // 允许跨域携带cookie
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },  (error) => {
    console.error('API Error:', error);
    let message = '网络错误，请检查您的网络连接';
    
    if (error.response) {
      // 优先使用后端返回的错误信息
      const responseData = error.response.data;
      message = responseData?.message || responseData?.error || responseData || message;
      
      switch (error.response.status) {
        case 401:
          // 未授权，清除token并跳转到登录页
          localStorage.removeItem('token');
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          message = '登录已过期，请重新登录';
          break;
        case 403:
          message = '权限不足，请重新登录';
          break;
        case 404:
          message = '请求的资源不存在';
          break;
        case 400:
          // 处理验证错误
          if (responseData?.errors) {
            message = Object.values(responseData.errors).join(', ');
          }
          break;
      }
    } else if (error.request) {
      message = '服务器无响应，请稍后重试';
    }
    
    return Promise.reject(new Error(message));
  }
)

// 用户相关接口
export const userApi = {
  // 用户登录
  login: (data: { username: string; password: string }): Promise<ApiResponse<LoginResponse>> => {
    return api.post('/auth/login', data)
  },
  
  // 用户注册
  register: (data: RegisterData): Promise<ApiResponse<void>> => {
    return api.post('/auth/register', data)
  },
  
  // 获取用户信息
  getUserInfo: (): Promise<ApiResponse<UserInfo>> => {
    return api.get('/user/profile')
  },
  
  // 更新用户信息
  updateProfile: (data: UpdateProfileData): Promise<ApiResponse<UserInfo>> => {
    return api.put('/user/profile', data)
  }
}

// 游戏相关接口
export const gameApi = {
  // 获取游戏列表
  getGames: (params?: GameListParams): Promise<ApiResponse<GameListResponse>> => {
    return api.get('/games', { params })
  },
  
  // 获取游戏详情
  getGameDetail: (id: string): Promise<ApiResponse<Game>> => {
    return api.get(`/games/${id}`)
  },
  
  // 获取推荐游戏
  getRecommendations: (): Promise<ApiResponse<Game[]>> => {
    return api.get('/games/recommendations')
  },
  
  // 添加游戏评分
  rateGame: (gameId: string, rating: number): Promise<ApiResponse<void>> => {
    return api.post(`/games/${gameId}/rate`, { rating })
  },
  
  // 添加游戏评论
  addComment: (gameId: string, content: string): Promise<ApiResponse<void>> => {
    return api.post(`/games/${gameId}/comments`, { content })
  }
}

export default api
