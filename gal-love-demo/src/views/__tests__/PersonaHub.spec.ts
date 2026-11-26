import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { providersMock, pushMock, errorMock } = vi.hoisted(() => ({
  providersMock: vi.fn(),
  pushMock: vi.fn(),
  errorMock: vi.fn(),
}))

vi.mock('../../api', () => ({
  api: { personaProviders: providersMock },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}))

vi.mock('element-plus', () => ({
  ElMessage: { error: errorMock },
}))

import PersonaHub from '../PersonaHub.vue'

const providers = [
  {
    key: 'bigfive',
    title: '大五人格',
    subtitle: '认真测一测',
    kind: 'questionnaire',
    group: 'serious',
    estimated_minutes: 5,
    question_count: 20,
    completed: false,
    labels: [],
  },
  {
    key: 'pairwise',
    title: '作品二选一',
    subtitle: '逐对比较作品',
    kind: 'pairwise',
    group: 'play',
    estimated_minutes: 3,
    question_count: 0,
    completed: true,
    code: 'INTP',
    labels: ['理性'],
  },
]

function mountHub() {
  return mount(PersonaHub, {
    global: {
      stubs: {
        'el-skeleton': true,
        'el-icon': true,
        'el-empty': true,
      },
    },
  })
}

describe('PersonaHub', () => {
  beforeEach(() => {
    providersMock.mockReset()
    pushMock.mockReset()
    errorMock.mockReset()
  })

  it('渲染标题与按分组归类的 provider', async () => {
    providersMock.mockResolvedValue({ items: providers, sources: [] })

    const wrapper = mountHub()
    await flushPromises()

    expect(providersMock).toHaveBeenCalledTimes(1)
    expect(wrapper.find('h1').text()).toBe('画像测试')
    expect(wrapper.findAll('h2').map((heading) => heading.text())).toEqual(['玩法', '认真'])
    expect(wrapper.findAll('.provider-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('大五人格')
    expect(wrapper.text()).toContain('作品二选一')
    expect(wrapper.text()).toContain('INTP')
  })

  it('点击卡片跳转到对应画像路径', async () => {
    providersMock.mockResolvedValue({ items: providers, sources: [] })

    const wrapper = mountHub()
    await flushPromises()

    const cards = wrapper.findAll('.provider-card')
    await cards[0].trigger('click')
    expect(pushMock).toHaveBeenLastCalledWith('/persona/pairwise')

    await cards[1].trigger('click')
    expect(pushMock).toHaveBeenLastCalledWith('/persona/bigfive')
    expect(pushMock).toHaveBeenCalledTimes(2)
  })
})
