# Registration Completed (finishedOnboarding) Feature

## ✅ Feature Added

Переключатель "Registration Completed" добавлен в админку для управления статусом регистрации пользователей.

## Расположение

Переключатель находится в форме редактирования пользователя (`UserForm.tsx`), после переключателей:
- Notifications (строка 592-603)
- Matches (строка 605-616)
- **Registration Completed** (строка 618-629) ← НОВЫЙ

## Как увидеть переключатель

### Вариант 1: Пересобрать Docker контейнер (рекомендуется)

```bash
cd infra
docker-compose up -d --build frontend
```

### Вариант 2: Если используете dev server

```bash
cd services/frontend
npm run dev
```

### Вариант 3: Очистить кэш браузера

1. Откройте DevTools (F12)
2. Правой кнопкой мыши на кнопку обновления
3. Выберите "Empty Cache and Hard Reload"
4. Или используйте Ctrl+Shift+R (Windows) / Cmd+Shift+R (Mac)

## Проверка

1. Откройте админку
2. Перейдите в раздел "People"
3. Нажмите "Edit" на любом пользователе
4. В форме редактирования должны быть видны три переключателя:
   - ✅ Notifications
   - ✅ Matches  
   - ✅ **Registration Completed** ← должен появиться здесь

## Технические детали

### Изменения в коде:

1. **services/frontend/src/UserForm.tsx**:
   - Добавлен переключатель "Registration Completed" (строка 618-629)
   - Добавлен `finishedOnboarding` в тип `User` (строка 38)
   - Добавлен `finishedOnboarding` в инициализацию формы (строка 93)
   - Добавлен `finishedOnboarding` в отправку данных (строка 462)

2. **services/frontend/src/PeopleTable.tsx**:
   - Добавлен `finishedOnboarding` в тип `User` (строка 43)
   - Добавлен `finishedOnboarding` в тип `Person` (строка 51)
   - Добавлен `finishedOnboarding` в маппинг данных (строки 255, 303)
   - Добавлен `finishedOnboarding` в передачу в UserForm (строка 865)

3. **services/api/main.py**:
   - Добавлено поле `finishedOnboarding` в модели `User` и `UserUpdate`
   - Обновлены SQL-запросы для включения `finishedOnboarding`

4. **services/bot/db.py**:
   - Исправлено: `finishedonboarding` всегда устанавливается в `true` при обновлении профиля

5. **services/bot/scenes.py**:
   - Исправлен вызов несуществующей функции `handle_exit`

## Тесты

Все тесты проходят успешно (45/45):
- ✅ 14 тестов для `finishedOnboarding`
- ✅ 21 тест для выходов из онбординга
- ✅ 5 тестов для команды `/start`
- ✅ 5 тестов для админки

## Если переключатель не виден

1. Убедитесь, что фронтенд пересобран: `npm run build` в `services/frontend`
2. Перезапустите Docker контейнер: `docker-compose up -d --build frontend`
3. Очистите кэш браузера (Ctrl+Shift+R)
4. Проверьте консоль браузера на ошибки (F12 → Console)
5. Убедитесь, что используете правильный URL админки
