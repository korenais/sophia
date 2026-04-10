import SkeletonFeaturePage from '../components/SkeletonFeaturePage'

export default function EventsPage() {
  return (
    <SkeletonFeaturePage
      phase="Phase 2"
      title="Ивенты"
      description="Здесь появится афиша Baltic Business Club: ближайшие встречи, featured event, RSVP и список участников."
      accent="#C9A84C"
      previews={[
        {
          eyebrow: 'Featured Event',
          title: 'Baltic Business Dinner',
          text: 'Большой баннер, дата, место, спикер и быстрый CTA «Я пойду».',
        },
        {
          eyebrow: 'Calendar',
          title: 'Календарь клуба',
          text: 'Список ближайших мероприятий с фильтрами, attendee count и быстрым переходом в detail.',
        },
        {
          eyebrow: 'Community',
          title: 'Предложить тему',
          text: 'Форма для идей, спикеров и инициатив, чтобы контент строился вокруг интересов сообщества.',
        },
      ]}
    />
  )
}
