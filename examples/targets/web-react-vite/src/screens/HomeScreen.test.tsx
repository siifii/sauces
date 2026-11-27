import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import i18n from '../i18n'
import { HomeView } from './HomeScreen'

describe('HomeView', () => {
  afterEach(cleanup)

  it('renders in English', async () => {
    await i18n.changeLanguage('en')
    render(<HomeView name="Alex" openOrders={2} />)
    expect(screen.getByRole('heading', { level: 1, name: 'Your account' })).toBeTruthy()
    expect(screen.getByText('You have 2 open orders.')).toBeTruthy()
  })

  it('renders right-to-left in Arabic', async () => {
    await i18n.changeLanguage('ar')
    render(<HomeView name="Alex" openOrders={2} />)
    expect(document.documentElement.dir).toBe('rtl')
    expect(screen.getByLabelText('البحث في الطلبات')).toBeTruthy()
  })
})
