import SkeletonFeaturePage from '../components/SkeletonFeaturePage'

export default function RequestsPage() {
  return (
    <SkeletonFeaturePage
      phase="Phase 2"
      title="Запросы"
      description="Биржа запросов для клуба: участники публикуют, что им нужно, а другие быстро подключаются и помогают."
      accent="#D4B45C"
      previews={[
        {
          eyebrow: 'Marketplace',
          title: 'Все запросы',
          text: 'Живая лента потребностей участников, отсортированная по свежести и важности.',
        },
        {
          eyebrow: 'Tags',
          title: '#маркетинг  #ОАЭ  #юрист',
          text: 'Теги и быстрые фильтры помогут быстро найти релевантные запросы по теме или рынку.',
        },
        {
          eyebrow: 'Action',
          title: 'Могу помочь',
          text: 'Один tap открывает контакт в Telegram и превращает запрос в живое знакомство.',
        },
      ]}
    />
  )
}
