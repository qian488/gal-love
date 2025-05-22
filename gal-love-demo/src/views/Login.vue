<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2 class="login-title">登录</h2>
      </template>
      <el-form
        :model="loginForm"
        :rules="rules"
        ref="loginFormRef"
        label-position="top"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username"
            placeholder="请输入用户名"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        <div class="form-actions">
          <el-button type="button" @click="handleLogin" :loading="loading">
            登录
          </el-button>
          <el-button type="button" @click="router?.push('/register')">
            注册新账号
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, getCurrentInstance } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import type { FormInstance, FormRules } from 'element-plus'

const internalInstance = getCurrentInstance()
const router = internalInstance?.proxy?.$router
const route = internalInstance?.proxy?.$route

const userStore = useUserStore()
const loginFormRef = ref<FormInstance>()
const loading = ref(false)

const loginForm = ref({
  username: '',
  password: ''
})

const rules = ref<FormRules>({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, message: '用户名长度至少为3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少为6个字符', trigger: 'blur' }
  ]
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  try {
    await loginFormRef.value.validate()
    loading.value = true
    const success = await userStore.login(loginForm.value.username, loginForm.value.password)
    if (success) {
      ElMessage.success('登录成功')
      // 获取重定向地址
      const redirect = route?.query?.redirect as string
      router?.push(redirect || '/')
    }
  } catch (error: any) {
    console.error('Login error:', error)
    ElMessage.error(error.message || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 同步注册页风格 */
.login-container {
  min-height: calc(100vh - 160px);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.login-card {
  width: 100%;
  max-width: 400px;
  border-radius: 8px;
}

.login-title {
  text-align: center;
  color: #409EFF;
  margin: 0;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

:deep(.el-button) {
  width: 45%;
}
</style>
