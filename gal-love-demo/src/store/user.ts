import { defineStore } from 'pinia'
import { ref } from 'vue'
import { userApi } from '../api'
import { ElMessage } from 'element-plus'
import type { UserInfo } from '../types/api'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref<UserInfo | null>(null)
  const isLoggedIn = ref(false)
  const loading = ref(false)

  // 初始化用户状态
  async function initUserState() {
    const token = localStorage.getItem('token')
    if (token) {
      try {
        const { data } = await userApi.getUserInfo()
        setUserInfo(data)
      } catch (error) {
        clearUserInfo()
      }
    }
  }

  // 设置用户信息
  function setUserInfo(user: UserInfo) {
    userInfo.value = user
    isLoggedIn.value = true
  }

  // 清除用户信息
  function clearUserInfo() {
    userInfo.value = null
    isLoggedIn.value = false
    localStorage.removeItem('token')
  }
  // 用户登录
  async function login(username: string, password: string) {
    loading.value = true
    try {
      const response = await userApi.login({ username, password })
      if (response.code === 0 && response.data) {
        localStorage.setItem('token', response.data.token)
        setUserInfo(response.data.user)
        return true
      } else {
        throw new Error(response.message || '登录失败')
      }
    } catch (error: any) {
      console.error('Login error:', error)
      throw error
    } finally {
      loading.value = false
    }
  }
  // 用户注册
  async function register(data: { username: string; email: string; password: string }) {
    loading.value = true
    try {
      const response = await userApi.register(data)
      if (response.code === 0) {
        return true
      } else {
        throw new Error(response.message || '注册失败')
      }
    } catch (error: any) {
      console.error('Registration error:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 更新用户信息
  async function updateProfile(data: Partial<UserInfo>) {
    loading.value = true
    try {
      const { data: updatedUser } = await userApi.updateProfile(data)
      setUserInfo(updatedUser)
      ElMessage.success('个人信息更新成功')
      return true
    } catch (error: any) {
      ElMessage.error(error.message || '更新失败')
      return false
    } finally {
      loading.value = false
    }
  }

  // 退出登录
  function logout() {
    clearUserInfo()
    ElMessage.success('已退出登录')
  }

  return {
    userInfo,
    isLoggedIn,
    loading,
    initUserState,
    login,
    register,
    updateProfile,
    logout
  }
})
