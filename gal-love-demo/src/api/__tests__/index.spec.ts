import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getMock, postMock, createMock } = vi.hoisted(() => {
  const get = vi.fn()
  const post = vi.fn()
  const create = vi.fn(() => ({
    get,
    post,
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: { response: { use: vi.fn() } },
  }))
  return { getMock: get, postMock: post, createMock: create }
})

vi.mock('axios', () => ({
  default: { create: createMock },
}))

import { api } from '../index'

describe('api 封装', () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
  })

  it('recommendations 传入 query 参数并命中 /recommendations', async () => {
    getMock.mockResolvedValue({ data: { items: [], algorithm_version: 'content-v1' } })

    await api.recommendations({ limit: 12, profile_source: 'quiz', save: false })

    expect(getMock).toHaveBeenCalledTimes(1)
    expect(getMock).toHaveBeenCalledWith('/recommendations', {
      params: { limit: 12, profile_source: 'quiz', save: false },
    })
    expect(getMock.mock.calls[0][1].params.profile_source).toBe('quiz')
  })

  it('personaProviders 命中 /persona/providers', async () => {
    getMock.mockResolvedValue({ data: { items: [], sources: [] } })

    await api.personaProviders()

    expect(getMock).toHaveBeenCalledWith('/persona/providers', { params: undefined })
  })

  it('savePersona 以 POST /persona/{key} 提交 { answers }', async () => {
    postMock.mockResolvedValue({ data: { key: 'bigfive' } })

    await api.savePersona('bigfive', { bf_1: 'x' })

    expect(postMock).toHaveBeenCalledTimes(1)
    expect(postMock).toHaveBeenCalledWith('/persona/bigfive', {
      answers: { bf_1: 'x' },
    })
  })
})
