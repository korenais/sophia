-- Add test users for birthday greeting functionality
-- All users have birthday today (2025-12-21)

DO $$
DECLARE
    today_date DATE := CURRENT_DATE;
    default_vector FLOAT[] := ARRAY(SELECT 0.0 FROM generate_series(1, 3072));
    new_user_id BIGINT;
    base_user_id BIGINT := EXTRACT(EPOCH FROM NOW())::BIGINT * 1000;
BEGIN
    -- User #1: Businessman, sailing hobby, English name
    new_user_id := base_user_id + 1;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Alexander Petrov',
        'Moscow, Russia',
        'Successful businessman with 15+ years of experience in international trade and investment. Specializes in building strategic partnerships and expanding business operations across multiple markets. Known for innovative approaches to business development and strong leadership skills.',
        'https://linkedin.com/in/alexander-petrov',
        'Sailing, yacht racing, maritime navigation, participating in regattas, exploring coastal regions',
        'Strategic planning, international business development, investment analysis, team leadership, negotiation, market expansion',
        'International trade, investment management, business consulting, strategic partnerships',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #1: Alexander Petrov (ID: %)', new_user_id;

    -- User #2: Small private entrepreneur, transportation, Russian name
    new_user_id := base_user_id + 2;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Иван Смирнов',
        'Санкт-Петербург, Россия',
        'Частный предприниматель, владелец небольшой транспортной компании. Занимаюсь грузоперевозками по России и странам СНГ. Имею собственный автопарк из 5 грузовых автомобилей. Специализируюсь на доставке товаров для малого и среднего бизнеса.',
        NULL,
        'Рыбалка, чтение книг по логистике, автомобили, путешествия на машине',
        'Управление автопарком, логистика, планирование маршрутов, работа с клиентами, ведение переговоров, управление финансами',
        'Грузоперевозки, логистика, транспортные услуги, доставка товаров',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #2: Иван Смирнов (ID: %)', new_user_id;

    -- User #3: Large businessman, self-generated data
    new_user_id := base_user_id + 3;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Михаил Волков',
        'Москва, Россия',
        'Крупный бизнесмен, основатель и CEO холдинговой компании с активами в сфере недвижимости, энергетики и IT. Управляю портфелем из 12 компаний с общим оборотом более 500 млн долларов. Эксперт в области корпоративного управления и стратегического планирования.',
        'https://linkedin.com/in/mikhail-volkov',
        'Гольф, коллекционирование часов, благотворительность, участие в бизнес-форумах, инвестиции в стартапы',
        'Корпоративное управление, стратегическое планирование, инвестиционный анализ, управление активами, построение бизнес-структур, работа с инвесторами',
        'Холдинговое управление, недвижимость, энергетика, IT-инвестиции, корпоративное развитие',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #3: Михаил Волков (ID: %)', new_user_id;

    -- User #4: Additional user
    new_user_id := base_user_id + 4;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Елена Новикова',
        'Казань, Россия',
        'Маркетолог с опытом работы в digital-агентствах. Специализируюсь на продвижении брендов в социальных сетях и контент-маркетинге. Работала с клиентами из сферы e-commerce, fintech и образовательных технологий.',
        'https://linkedin.com/in/elena-novikova',
        'Фотография, йога, чтение бизнес-литературы, путешествия, изучение языков',
        'Digital-маркетинг, SMM, контент-стратегия, аналитика, работа с креативными командами, управление рекламными кампаниями',
        'Digital-маркетинг, SMM, контент-маркетинг, брендинг',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #4: Елена Новикова (ID: %)', new_user_id;

    -- User #5: Additional user
    new_user_id := base_user_id + 5;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Дмитрий Козлов',
        'Новосибирск, Россия',
        'IT-предприниматель, основатель стартапа в области искусственного интеллекта. Разрабатываю решения для автоматизации бизнес-процессов с использованием машинного обучения. Имею опыт работы в крупных технологических компаниях.',
        NULL,
        'Программирование, участие в хакатонах, настольные игры, велоспорт',
        'Разработка ПО, машинное обучение, управление продуктом, техническое лидерство, работа с данными',
        'IT, искусственный интеллект, машинное обучение, автоматизация бизнес-процессов',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #5: Дмитрий Козлов (ID: %)', new_user_id;

    -- User #6: Additional user
    new_user_id := base_user_id + 6;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Анна Лебедева',
        'Екатеринбург, Россия',
        'Финансовый консультант с опытом работы в банковском секторе. Помогаю частным клиентам и малому бизнесу в управлении финансами, инвестиционном планировании и оптимизации налогов. Сертифицированный финансовый планировщик.',
        'https://linkedin.com/in/anna-lebedeva',
        'Теннис, чтение финансовой литературы, кулинария, садоводство',
        'Финансовое планирование, инвестиционный анализ, налогообложение, консультирование клиентов, управление портфелями',
        'Финансовое консультирование, инвестиции, налогообложение, банковские услуги',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #6: Анна Лебедева (ID: %)', new_user_id;

    -- User #7: Additional user
    new_user_id := base_user_id + 7;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Сергей Морозов',
        'Краснодар, Россия',
        'Ресторатор, владелец сети из 3 ресторанов в Краснодарском крае. Специализируюсь на авторской кухне и создании уникальных гастрономических концепций. Участник различных кулинарных фестивалей и конкурсов.',
        NULL,
        'Кулинария, вино, путешествия с гастрономическим уклоном, фотография еды',
        'Ресторанный бизнес, управление персоналом, создание меню, маркетинг в HoReCa, управление закупками',
        'Ресторанный бизнес, гастрономия, HoReCa, кулинария',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #7: Сергей Морозов (ID: %)', new_user_id;

    -- User #8: Additional user
    new_user_id := base_user_id + 8;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Ольга Соколова',
        'Ростов-на-Дону, Россия',
        'HR-директор с опытом работы в крупных корпорациях. Специализируюсь на подборе топ-менеджмента, развитии корпоративной культуры и внедрении HR-технологий. Имею сертификаты по управлению талантами и организационному развитию.',
        'https://linkedin.com/in/olga-sokolova',
        'Психология, чтение книг по управлению, йога, волонтерство',
        'Подбор персонала, управление талантами, организационное развитие, обучение и развитие, HR-аналитика',
        'HR, управление персоналом, рекрутинг, организационное развитие',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #8: Ольга Соколова (ID: %)', new_user_id;

    -- User #9: Additional user
    new_user_id := base_user_id + 9;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Павел Орлов',
        'Воронеж, Россия',
        'Архитектор и дизайнер интерьеров. Работаю над проектами жилых и коммерческих помещений. Участвую в международных конкурсах и выставках. Специализируюсь на современном минимализме и эко-дизайне.',
        NULL,
        'Рисование, фотография архитектуры, путешествия, изучение современных материалов',
        'Архитектурное проектирование, дизайн интерьеров, 3D-визуализация, работа с клиентами, управление проектами',
        'Архитектура, дизайн интерьеров, проектирование, строительство',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #9: Павел Орлов (ID: %)', new_user_id;

    -- User #10: Same text as user #11
    new_user_id := base_user_id + 10;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Алексей Федоров',
        'Самара, Россия',
        'Профессиональный консультант по управлению проектами с опытом работы в различных отраслях. Специализируюсь на внедрении методологий Agile и Scrum в крупных организациях. Помогаю командам повышать эффективность и достигать поставленных целей.',
        NULL,
        'Шахматы, чтение бизнес-литературы, бег, участие в марафонах',
        'Управление проектами, Agile, Scrum, фасилитация, работа с командами, стратегическое планирование',
        'Консалтинг, управление проектами, Agile-трансформация, организационное развитие',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #10: Алексей Федоров (ID: %)', new_user_id;

    -- User #11: Same text as user #10
    new_user_id := base_user_id + 11;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Владимир Иванов',
        'Нижний Новгород, Россия',
        'Профессиональный консультант по управлению проектами с опытом работы в различных отраслях. Специализируюсь на внедрении методологий Agile и Scrum в крупных организациях. Помогаю командам повышать эффективность и достигать поставленных целей.',
        NULL,
        'Шахматы, чтение бизнес-литературы, бег, участие в марафонах',
        'Управление проектами, Agile, Scrum, фасилитация, работа с командами, стратегическое планирование',
        'Консалтинг, управление проектами, Agile-трансформация, организационное развитие',
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_description = EXCLUDED.intro_description,
        intro_hobbies_drivers = EXCLUDED.intro_hobbies_drivers,
        intro_skills = EXCLUDED.intro_skills,
        field_of_activity = EXCLUDED.field_of_activity,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #11: Владимир Иванов (ID: %)', new_user_id;

    -- User #12: Swedish name only
    new_user_id := base_user_id + 12;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'Erik Andersson',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #12: Erik Andersson (ID: %)', new_user_id;

    -- User #13: Arabic name in Arabic
    new_user_id := base_user_id + 13;
    INSERT INTO users (
        user_id, chat_id, intro_name, intro_location, intro_description,
        intro_linkedin, intro_hobbies_drivers, intro_skills, field_of_activity,
        intro_birthday, state, finishedonboarding, notifications_enabled,
        matches_disabled, vector_description, created_at, updated_at
    ) VALUES (
        new_user_id, new_user_id,
        'محمد أحمد',
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        NULL,
        today_date,
        'ACTIVE', true, true, false, default_vector, NOW(), NOW()
    ) ON CONFLICT (user_id) DO UPDATE SET
        intro_name = EXCLUDED.intro_name,
        intro_birthday = EXCLUDED.intro_birthday,
        updated_at = NOW();
    RAISE NOTICE 'Created user #13: محمد أحمد (ID: %)', new_user_id;

    RAISE NOTICE 'All test users created successfully!';
END $$;

