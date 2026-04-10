-- Add test user: Дмитрий Соколов
-- Birthday: today's date

-- Generate a unique user_id (using timestamp-based approach)
DO $$
DECLARE
    new_user_id BIGINT;
    today_date DATE := CURRENT_DATE;
    default_vector FLOAT[] := ARRAY(SELECT 0.0 FROM generate_series(1, 3072));
BEGIN
    -- Generate user_id (use timestamp * 1000 + random to ensure uniqueness)
    new_user_id := EXTRACT(EPOCH FROM NOW())::BIGINT * 1000 + (RANDOM() * 999)::INT;
    
    -- Insert the user
    INSERT INTO users (
        user_id,
        chat_id,
        intro_name,
        intro_location,
        intro_description,
        intro_linkedin,
        intro_hobbies_drivers,
        intro_skills,
        field_of_activity,
        intro_birthday,
        state,
        finishedonboarding,
        notifications_enabled,
        matches_disabled,
        vector_description,
        created_at,
        updated_at
    ) VALUES (
        new_user_id,
        new_user_id,
        'Дмитрий Соколов',
        NULL,
        'Предприниматель и стратег, ориентированный на рост бизнеса через эффективный маркетинг и сильный бренд. Умеет находить точки роста, выстраивать коммуникацию с аудиторией и превращать идеи в коммерчески успешные проекты.',
        NULL,
        'Нетворкинг, чтение книг по маркетингу и психологии продаж, участие в бизнес-мероприятиях, анализ рекламных кейсов, спорт. Стимулы: Масштабирование бизнеса, рост узнаваемости бренда, финансовая независимость, влияние на рынок и создание устойчивых компаний',
        'Более 8 лет в предпринимательстве, запуск и продвижение собственных проектов, управление рекламными бюджетами, работа с digital-каналами и партнёрами',
        'Предпринимательство, маркетинг и реклама, развитие брендов, digital-бизнес',
        today_date,
        'ACTIVE',
        true,
        true,
        false,
        default_vector,
        NOW(),
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        state = EXCLUDED.state,
        finishedonboarding = EXCLUDED.finishedonboarding,
        updated_at = NOW();
    
    RAISE NOTICE 'Test user created/updated with user_id: %', new_user_id;
END $$;
