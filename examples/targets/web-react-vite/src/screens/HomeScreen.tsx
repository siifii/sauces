import { useTranslation } from 'react-i18next'
import { Button } from '../components/Button/Button'
import { Card } from '../components/Card/Card'
import { TextField } from '../components/TextField/TextField'
import styles from './HomeScreen.module.css'

export type HomeViewProps = { name: string; openOrders: number; onViewOrders?: () => void }

export function HomeView({ name, openOrders, onViewOrders }: HomeViewProps) {
  const { t } = useTranslation()
  return (
    <main className={styles.screen}>
      <h1 className={styles.title}>{t('home.title')}</h1>
      <p>{t('home.greeting', { name })}</p>
      <TextField label={t('home.searchLabel')} type="search" />
      <Card
        title={t('home.ordersTitle')}
        action={<Button onClick={onViewOrders}>{t('home.viewOrders')}</Button>}
      >
        {t('home.ordersBody', { count: openOrders })}
      </Card>
    </main>
  )
}
