import SkeletonFeaturePage from '../components/SkeletonFeaturePage'

export default function ServicesPage() {
  return (
    <SkeletonFeaturePage
      phase="Phase 3"
      title="Сервисы"
      description="Партнерские предложения и библиотека знаний клуба. Здесь появятся бонусы, промокоды и curated content."
      accent="#E3C96A"
      previews={[
        {
          eyebrow: 'Partners',
          title: 'Предложения клуба',
          text: 'Карточки партнеров с офферами, скидками и быстрым получением промокода.',
        },
        {
          eyebrow: 'Knowledge',
          title: 'Знания',
          text: 'Подборка видео, разборов и материалов, которые усиливают ценность участия в клубе.',
        },
        {
          eyebrow: 'Monetization',
          title: 'Club Coins',
          text: 'Позже здесь можно будет использовать earned coins для активации специальных офферов.',
        },
      ]}
    />
  )
}
