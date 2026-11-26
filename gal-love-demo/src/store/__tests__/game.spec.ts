import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { settingsMock, saveSettingsMock, errorMock } = vi.hoisted(() => ({
  settingsMock: vi.fn(),
  saveSettingsMock: vi.fn(),
  errorMock: vi.fn(),
}))

vi.mock('../../api', () => ({
  api: {
    settings: settingsMock,
    saveSettings: saveSettingsMock,
  },
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: errorMock },
}))

import { useCatalogStore } from '../game'

const remoteSettings = {
  include_nsfw: true,
  min_year: 2010,
  max_length_minutes: 600,
  platform: 'win',
  language: 'ja',
  diversity: 0.3,
  quiz_merge_home: false,
  home_profile_sources: ['quiz', 'bigfive'],
}

describe('catalog store 设置', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    settingsMock.mockReset()
    saveSettingsMock.mockReset()
    errorMock.mockReset()
  })

  it('fetchSettings 把后端字段完整写入 state', async () => {
    settingsMock.mockResolvedValue(remoteSettings)
    const store = useCatalogStore()

    await store.fetchSettings()

    expect(settingsMock).toHaveBeenCalledTimes(1)
    expect(store.settings).toEqual(remoteSettings)
    expect(store.settings.quiz_merge_home).toBe(false)
    expect(store.settings.home_profile_sources).toEqual(['quiz', 'bigfive'])
  })

  it('saveSettings 透传 patch 并用响应更新 state', async () => {
    const patch = { home_profile_sources: ['bigfive'], quiz_merge_home: true }
    const merged = { ...remoteSettings, ...patch }
    saveSettingsMock.mockResolvedValue(merged)
    const store = useCatalogStore()

    const returned = await store.saveSettings(patch)

    expect(saveSettingsMock).toHaveBeenCalledWith(patch)
    expect(returned).toEqual(merged)
    expect(store.settings.home_profile_sources).toEqual(['bigfive'])
    expect(store.settings.quiz_merge_home).toBe(true)
  })
})
