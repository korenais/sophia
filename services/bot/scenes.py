from __future__ import annotations

from typing import Dict, Any, Optional
import os
import base64
import httpx
import logging
from aiogram import F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
from db import get_pool, set_user_onboarding_data, upsert_user_state, get_user_info
from vectorization import vectorize_description
from validators import InputValidator, ValidationError
import asyncio

# Load environment variables early to ensure BOT_LANGUAGE is available
load_dotenv()

# Get environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
logger = logging.getLogger(__name__)


class OnboardingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_location = State()
    waiting_for_description = State()
    waiting_for_linkedin = State()
    waiting_for_hobbies_drivers = State()
    waiting_for_skills = State()
    waiting_for_field_of_activity = State()
    waiting_for_birthday = State()
    waiting_for_photo = State()
    profile_confirmation = State()
    partial_onboarding_confirmation = State()


class ProfileStates(StatesGroup):
    viewing_profile = State()
    editing_profile = State()
    # Edit mode states - these return to edit menu after updating field
    editing_name = State()
    editing_location = State()
    editing_description = State()
    editing_linkedin = State()
    editing_hobbies_drivers = State()
    editing_skills = State()
    editing_field_of_activity = State()
    editing_birthday = State()
    editing_photo = State()

class MyMatchesStates(StatesGroup):
    viewing_matches = State()

class BrowseStates(StatesGroup):
    browsing_users = State()


class OnboardingData:
    def __init__(self):
        self.name: Optional[str] = None
        self.location: Optional[str] = None
        self.description: Optional[str] = None
        self.linkedin: Optional[str] = None
        self.hobbies_drivers: Optional[str] = None
        self.skills: Optional[str] = None
        self.field_of_activity: Optional[str] = None
        self.birthday: Optional[str] = None
        self.photo_id: Optional[str] = None
        self.location_latlong: Optional[str] = None


# Bot messages (English)
BOT_MESSAGES_EN = {
    "MISSING_FIELD": "MISSING",
    "MONTHS": [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ],
    "MONTHS_SHORT": [
        "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ],
    "WEEKDAYS": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "ONBOARDING": {
        "NAME": {
            "PROMPT": "How should I call you?",
            "INVALID": "Пожалуйста, отправьте ваше имя."
        },
        "LOCATION": {
            "PROMPT": "Where are you from?\n\nYou can:\n• Type your city/country (e.g., Moscow, Russia)\n• Share your location (if available)\n• Type \"skip\" if you don't want to specify location",
            "INVALID": "Пожалуйста, отправьте ваше местоположение.",
            "SHARE_LOCATION": "Share my current location",
            "DONT_SHARE": "Skip"
        },
        "DESCRIPTION": {
            "PROMPT": "Tell me about yourself, this will help me find you the best match!",
            "INVALID": "Пожалуйста, отправьте корректное описание."
        },
        "LINKEDIN": {
            "PROMPT": "Add your LinkedIn (or send 'Not available')",
            "INVALID": "Please provide a valid LinkedIn URL or 'Not available'."
        },
        "HOBBIES_DRIVERS": {
            "PROMPT": "What are your hobbies and what drives you?",
            "INVALID": "Пожалуйста, расскажите о ваших хобби и что вас мотивирует."
        },
        "SKILLS": {
            "PROMPT": "What are your skills (in business and beyond)?",
            "INVALID": "Пожалуйста, расскажите о ваших навыках."
        },
        "FIELD_OF_ACTIVITY": {
            "PROMPT": "What is your field of activity/profession? (or send 'Not specified')",
            "INVALID": "Please provide your field of activity or 'Not specified'."
        },
        "BIRTHDAY": {
            "PROMPT": "When is your birthday? Please send in format YYYY-MM-DD (e.g., 1990-05-15)",
            "INVALID": "Пожалуйста, отправьте ваш день рождения в формате YYYY-MM-DD (например, 1990-05-15).",
            "SELECT_YEAR": "Select your birth year first:",
            "SELECT_YEAR_AGAIN": "Select your birth year:",
            "SELECT_MONTH": "Select your birth month:",
            "SELECT_DAY": "Select your birth day:",
            "SKIP": "Skip",
            "SKIPPED": "⏭️ Birthday skipped.",
            "BACK_TO_YEAR": "◀️ Back",
            "BACK_TO_MONTH": "◀️ Back",
            "YEAR_SELECTED": "Year: {year}",
            "BIRTHDAY_SELECTED": "✅ Birthday selected: {birthday_text}",
            "BIRTHDAY_CLEARED": "🗑️ Birthday cleared."
        },
        "PHOTO": {
            "PROMPT": "Now send your photo that other users will see.",
            "INVALID": "Пожалуйста, отправьте фото."
        },
        "PROFILE": {
            "CONFIRM": "Profile saved successfully!",
            "ERROR": "Ошибка сохранения профиля. Пожалуйста, попробуйте еще раз.",
            "YES": "Yes",
            "CONTINUE_EDITING": "Continue editing",
            "SEND_PROFILE": "Your profile:",
            "ASK_ANY_CHANGES": "What would you like to change?\n\nOr type:\n• \"no\" if no changes needed\n• \"exit\" to finish",
            "ASK_CONFIRM_PROFILE": "Is this information correct?\n\nYou can type:\n• \"yes\" to confirm and save\n• \"edit\" to continue editing",
            "SEND_FINAL_PROFILE": "Your final profile:",
            "SEND_CURRENT_PROFILE": "Your current profile:",
            "ASK_DETAILED_CHANGES": "What would you like to change?",
            "NO_CHANGES_NEEDED": "Profile editing completed. No changes needed.",
            "EDIT_LOCATION": "Location",
            "EDIT_NAME": "Name",
            "EDIT_DESCRIPTION": "Description",
            "EDIT_LINKEDIN": "LinkedIn Profile",
            "EDIT_HOBBIES_DRIVERS": "Hobbies & Drivers",
            "EDIT_SKILLS": "Skills",
            "EDIT_FIELD_OF_ACTIVITY": "Field of Activity",
            "EDIT_BIRTHDAY": "Birthday",
            "EDIT_PHOTO": "Photo",
            "START_OVER": "Start Over",
            "FIELDS": {
                "NAME": "Name:",
                "LOCATION": "Location:",
                "DESCRIPTION": "Description:",
                "LINKEDIN": "LinkedIn:",
                "HOBBIES_DRIVERS": "Hobbies & Drivers:",
                "SKILLS": "Skills:",
                "FIELD_OF_ACTIVITY": "Field of Activity:",
                "BIRTHDAY": "Birthday:",
                "PHOTO": "Photo:",
                "PHOTO_SET": "Set",
                "PHOTO_NOT_SET": "Not set"
            },
            "PROFILE_SAVED": "Profile saved successfully!",
            "INVALID_EDIT_PROFILE_KB": "Пожалуйста, выберите поле для редактирования или нажмите Отмена.",
            "EDITING_CANCELLED": "Profile editing completed.",
            "EDITING_CANCELLED_WITH_CHANGES": "Profile editing completed. Changes saved.",
            "EDITING_CANCELLED_NO_CHANGES": "Profile editing completed. No changes made.",
            "NO_CHANGES": "В ваш профиль не внесено изменений."
        }
    },
    "BIRTHDAY": {
        "GREETING": "Happy Birthday, {name}!\n\nWishing you an amazing year ahead filled with great connections and opportunities!",
        "CELEBRATION": "It's your special day!"
    },
    "KEYBOARD": {
        "YES": "Yes",
        "NO": "No",
        "CANCEL": "Cancel"
    },
    "CANCEL": {
        "ACTION_CANCELLED": "Current action cancelled. You can now use any command.",
        "NO_ACTION": "No active action to cancel."
    },
    "COMMANDS": {
        "BOT_UP": "Bot is up. Send /help for commands.",
        "NO_MATCHABLE_USERS": "No matchable users found yet.",
        "COMPLETE_ONBOARDING": "Пожалуйста, сначала завершите регистрацию с помощью /start.",
        "NO_MATCHES": "No matches yet. Try updating your profile description.",
        "TOP_MATCHES": "Top matches:",
        "NO_USERS_BROWSE": "No users available to browse yet.",
        "SOME_USERS": "Some users:",
        "NO_PENDING_MATCHES": "No pending matches found for you.",
        "ENTER_VALID_MEETING_ID": "Пожалуйста, введите корректный номер ID встречи.",
        "INVALID_MEETING_ID": "Неверный ID встречи. Пожалуйста, попробуйте еще раз.",
        "BIRTHDAY_CHECKING": "🎂 Checking for birthdays today...",
        "BIRTHDAY_COMPLETED": "✅ Birthday check completed!",
        "BIRTHDAY_ERROR": "❌ Error checking birthdays:",
        "SCHEDULER_STATUS": "📊 Scheduler Status:",
        "RUNNING": "Running:",
        "YES": "Yes",
        "NO": "No",
        "JOBS": "Jobs:",
        "LAST_RUN": "Last run:",
        "NEXT_RUN": "Next run:",
        "INTERVAL": "Interval:",
        "ERROR": "Error:",
        "BROWSE_NO_USERS": "No users available to browse yet.",
        "BROWSE_SOME_USERS": "Some users:",
        "NO_PENDING_MATCHES": "No pending matches found for you.",
        "ENTER_VALID_MEETING_ID": "Пожалуйста, введите корректный номер ID встречи.",
        "INVALID_MEETING_ID": "Неверный ID встречи. Пожалуйста, попробуйте еще раз.",
        "SCHEDULER_RUNNING": "Running:",
        "SCHEDULER_JOBS": "Jobs:",
        "SCHEDULER_YES": "Yes",
        "SCHEDULER_NO": "No",
        "FEEDBACK_DESCRIBE_ISSUE": "Please describe the issue you encountered. Include details like:",
        "FEEDBACK_DESCRIBE_IDEA": "We'd love to hear your ideas! Please describe:",
        "FEEDBACK_THANK_ISSUE": "Thank you for reporting this issue! We'll look into it and work on a fix.",
        "FEEDBACK_THANK_IDEA": "Thank you for your suggestion! We'll consider it for future updates.",
        "USER": "User",
        "FEEDBACK_WHAT_TRYING": "What you were trying to do",
        "FEEDBACK_WHAT_HAPPENED": "What happened instead",
        "FEEDBACK_ERROR_MESSAGES": "Any error messages you saw",
        "FEEDBACK_HELPS_IMPROVE": "Your feedback helps us improve the bot!",
        "FEEDBACK_FEATURE_DETAILS": "What feature you'd like to see",
        "FEEDBACK_HOW_HELP": "How it would help you",
        "FEEDBACK_SPECIFIC_DETAILS": "Any specific details about how it should work",
        "FEEDBACK_HELP_MAKE_BETTER": "Thank you for helping us make the bot better!",
        "FEEDBACK_REPORT_ISSUE": "Report an Issue",
        "FEEDBACK_SUGGEST_FEATURE": "Suggest a Feature",
        "SIMILARITY": "similarity",
        "THANKS_NO_USERNAME": "Specify who to thank: @username",
        "THANKS_NOT_A_USER": "❌ @{username} is a {chat_type}, not a user. Cannot send thanks to a {chat_type}. Please use @username of a real user or select a user from Telegram mention menu (@ button).",
        "THANKS_SELF_THANK": "You can't thank yourself.",
        "THANKS_GIVEN": "Thanks given!",
        "THANKS_NO_THANKS": "No thanks given yet.",
        "THANKS_TOP_TITLE": "Top {n} most thanked users:",
        "THANKS_STATS_TITLE": "Thanks statistics:",
        "THANKS_NOW_HAS": "now has",
        "THANKS_WORD": "thanks",
        "HELP_TITLE": "Available Commands:",
        "HELP_TIP": "Tip: You can also use the menu button (☰) to see all available commands!",
        "HELP_SUPPORT": "Support: Use /report_an_issue or /suggest_a_feature to contact us."
    },
        "MATCH_NOTIFICATIONS": {
            "NEW_MATCH_TITLE": "🤝 <b>New Business Connection</b>",
            "MATCHED_WITH": "We've matched you with {name}",
            "ABOUT_THEM": "<b>Profile Overview:</b>",
            "LOCATION": "📍 <b>Location:</b> {location}",
            "DESCRIPTION": "💼 <b>About:</b> {description}",
            "LINKEDIN": "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>",
            "PROFILE_LINK": '👤 <b>View Full Profile:</b> <a href="{profile_url}">Open Profile</a>',
            "NEXT_STEPS": "<b>Next Steps:</b>",
            "STEP_1": "💬 Contact via Telegram",
            "STEP_2": "☕ Schedule a meeting",
            "STEP_3": "🤝 Explore collaboration opportunities",
            "TELEGRAM_CONTACT": "💬 <b>Telegram:</b> <a href=\"https://t.me/{telegram_link}\">@{telegram_link}</a>",
            "VIEW_MATCHES_LATER": "📋 <i>View all connections: /my_matches</i>",
            "SUCCESS_MESSAGE": "Best of luck with your networking! 🚀"
        }
}

# Bot messages (Russian)
BOT_MESSAGES_RU = {
    "MISSING_FIELD": "Не указан",
    "MONTHS": [
        "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
        "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
    ],
    "MONTHS_SHORT": [
        "", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
        "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
    ],
    "WEEKDAYS": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    "ONBOARDING": {
        "NAME": {"PROMPT": "Пожалуйста, укажите ваше полное имя, фамилию (на латинице), как в документах.", "INVALID": "Пожалуйста, отправьте ваше имя."},
        "LOCATION": {
            "PROMPT": "Укажите, где вы находитесь сейчас или где живёте большую часть времени.",
            "INVALID": "Пожалуйста, отправьте вашу локацию.",
            "SHARE_LOCATION": "Поделиться текущей локацией",
            "DONT_SHARE": "Пропустить"
        },
        "DESCRIPTION": {
            "PROMPT": "Расскажите о себе (2–3 предложения)\nЭто короткое описание увидят другие резиденты клуба, когда будут знакомиться с вами через Random Coffee или в базе участников.\nНапишите пару строк о себе — кто вы, чем занимаетесь, чем увлекаетесь. Можно упомянуть бизнес, профессию, интересы или семью.",
            "INVALID": "Пожалуйста, отправьте корректное описание."
        },
        "LINKEDIN": {"PROMPT": "Добавьте ссылку на ваш LinkedIn или основную соцсеть или отправьте 'Не указан'.", "INVALID": "Пожалуйста, отправьте корректную ссылку на LinkedIn или 'Не указан'."},
        "HOBBIES_DRIVERS": {"PROMPT": "Расскажите немного о том, что вам интересно за пределами работы — спорт, путешествия, искусство, семья, развитие, благотворительность, что угодно.\nТакже добавьте пару слов о том, что вас вдохновляет или даёт энергию — это поможет подобрать людей с похожими ценностями.", "INVALID": "Пожалуйста, расскажите о ваших хобби и мотивации."},
        "SKILLS": {"PROMPT": "Укажите ключевые навыки, которые вас характеризуют — как профессиональные, так и личные.\nЭто поможет другим резидентам понять, в чём вы сильны и с какими вопросами можно к вам обратиться.", "INVALID": "Пожалуйста, расскажите о ваших навыках."},
        "FIELD_OF_ACTIVITY": {"PROMPT": "Какая у вас сфера деятельности/профессия? (или отправьте 'Не указано')", "INVALID": "Пожалуйста, укажите вашу сферу деятельности или 'Не указано'."},
        "BIRTHDAY": {
            "PROMPT": "Когда у вас день рождения? Отправьте в формате ГГГГ-ММ-ДД (например, 1990-05-15)", 
            "INVALID": "Пожалуйста, отправьте день рождения в формате ГГГГ-ММ-ДД (например, 1990-05-15).",
            "SELECT_YEAR": "Сначала выберите год рождения:",
            "SELECT_YEAR_AGAIN": "Выберите год рождения:",
            "SELECT_MONTH": "Выберите месяц рождения:",
            "SELECT_DAY": "Выберите день рождения:",
            "SKIP": "Пропустить",
            "SKIPPED": "⏭️ День рождения пропущен.",
            "BACK_TO_YEAR": "◀️ Назад",
            "BACK_TO_MONTH": "◀️ Назад",
            "YEAR_SELECTED": "Год: {year}",
            "BIRTHDAY_SELECTED": "✅ День рождения выбран: {birthday_text}",
            "BIRTHDAY_CLEARED": "🗑️ День рождения удален."
        },
        "PHOTO": {"PROMPT": "Теперь отправьте вашу фотографию.", "INVALID": "Пожалуйста, отправьте фотографию."},
        "PROFILE": {
            "CONFIRM": "Профиль успешно сохранен!",
            "ERROR": "Ошибка при сохранении профиля. Попробуйте еще раз.",
            "YES": "Да",
            "CONTINUE_EDITING": "Продолжить редактирование",
            "SEND_PROFILE": "Ваш профиль:",
            "ASK_ANY_CHANGES": "Что хотите изменить?\n\nИли напишите:\n• \"нет\" если не нужно ничего менять\n• \"выход\" чтобы завершить",
            "ASK_CONFIRM_PROFILE": "Вся информация верна?\n\nВы можете написать:\n• \"да\" чтобы подтвердить и сохранить\n• \"редактировать\" чтобы продолжить редактирование",
            "SEND_FINAL_PROFILE": "Ваш финальный профиль:",
            "SEND_CURRENT_PROFILE": "Ваш текущий профиль:",
            "ASK_DETAILED_CHANGES": "Что хотите изменить?",
            "NO_CHANGES_NEEDED": "Редактирование профиля завершено. Изменения не требуются.",
            "EDIT_LOCATION": "Местоположение",
            "EDIT_NAME": "Имя",
            "EDIT_DESCRIPTION": "Описание",
            "EDIT_LINKEDIN": "Профиль LinkedIn",
            "EDIT_HOBBIES_DRIVERS": "Хобби и мотивация",
            "EDIT_SKILLS": "Навыки",
            "EDIT_FIELD_OF_ACTIVITY": "Сфера деятельности",
            "EDIT_BIRTHDAY": "День рождения",
            "EDIT_PHOTO": "Фото",
            "START_OVER": "Начать всё заново",
            "FIELDS": {
                "NAME": "Имя:",
                "LOCATION": "Местоположение:",
                "DESCRIPTION": "Описание:",
                "LINKEDIN": "LinkedIn:",
                "HOBBIES_DRIVERS": "Хобби и мотивация:",
                "SKILLS": "Навыки:",
                "FIELD_OF_ACTIVITY": "Сфера деятельности:",
                "BIRTHDAY": "День рождения:",
                "PHOTO": "Фото:",
                "PHOTO_SET": "Установлено",
                "PHOTO_NOT_SET": "Не установлено"
            },
            "PROFILE_SAVED": "Профиль успешно сохранен!",
            "INVALID_EDIT_PROFILE_KB": "Выберите поле для редактирования или Отмена.",
            "EDITING_CANCELLED": "Редактирование профиля завершено.",
            "EDITING_CANCELLED_WITH_CHANGES": "Редактирование профиля завершено. Изменения сохранены.",
            "EDITING_CANCELLED_NO_CHANGES": "Редактирование профиля завершено. Изменения не внесены.",
            "NO_CHANGES": "Изменения в профиль не внесены."
        }
    },
    "BIRTHDAY": {
        "GREETING": "С Днём Рождения, {name}!\n\nЖелаем вам успешного года, плодотворных встреч и новых деловых возможностей в рамках Baltic Business Club!",
        "CELEBRATION": "🎂 Сегодня день рождения у участника Клуба!"
    },
    "KEYBOARD": {"YES": "Да", "NO": "Нет", "CANCEL": "Отмена"},
    "CANCEL": {
        "ACTION_CANCELLED": "Текущее действие отменено. Теперь вы можете использовать любую команду.",
        "NO_ACTION": "Нет активного действия для отмены."
    },
    "COMMANDS": {
        "BOT_UP": "Бот запущен. Отправьте /help для списка команд.",
        "NO_MATCHABLE_USERS": "Пока нет пользователей для сопоставления.",
        "COMPLETE_ONBOARDING": "Пожалуйста, завершите регистрацию с помощью /start.",
        "NO_MATCHES": "Пока нет совпадений. Попробуйте обновить описание профиля.",
        "TOP_MATCHES": "Лучшие совпадения:",
        "NO_USERS_BROWSE": "Пока нет пользователей для просмотра.",
        "SOME_USERS": "Некоторые пользователи:",
        "NO_PENDING_MATCHES": "У вас нет ожидающих подтверждения совпадений.",
        "ENTER_VALID_MEETING_ID": "Пожалуйста, введите корректный ID встречи.",
        "INVALID_MEETING_ID": "Неверный ID встречи. Попробуйте еще раз.",
        "BIRTHDAY_CHECKING": "🎂 Проверяем дни рождения на сегодня...",
        "BIRTHDAY_COMPLETED": "✅ Проверка дней рождения завершена!",
        "BIRTHDAY_ERROR": "❌ Ошибка при проверке дней рождения:",
        "SCHEDULER_STATUS": "📊 Статус планировщика:",
        "RUNNING": "Работает:",
        "YES": "Да",
        "NO": "Нет",
        "JOBS": "Задачи:",
        "LAST_RUN": "Последний запуск:",
        "NEXT_RUN": "Следующий запуск:",
        "INTERVAL": "Интервал:",
        "ERROR": "Ошибка:",
        "BROWSE_NO_USERS": "Пока нет пользователей для просмотра.",
        "BROWSE_SOME_USERS": "Некоторые пользователи:",
        "NO_PENDING_MATCHES": "У вас нет ожидающих подтверждения совпадений.",
        "ENTER_VALID_MEETING_ID": "Пожалуйста, введите корректный ID встречи.",
        "INVALID_MEETING_ID": "Неверный ID встречи. Попробуйте еще раз.",
        "SCHEDULER_RUNNING": "Работает:",
        "SCHEDULER_JOBS": "Задачи:",
        "SCHEDULER_YES": "Да",
        "SCHEDULER_NO": "Нет",
        "FEEDBACK_DESCRIBE_ISSUE": "Пожалуйста, опишите проблему, с которой вы столкнулись. Включите детали, такие как:",
        "FEEDBACK_DESCRIBE_IDEA": "Мы будем рады услышать ваши идеи! Пожалуйста, опишите:",
        "FEEDBACK_THANK_ISSUE": "Спасибо за сообщение об этой проблеме! Мы изучим её и работаем над исправлением.",
        "FEEDBACK_THANK_IDEA": "Спасибо за ваше предложение! Мы рассмотрим его для будущих обновлений.",
        "USER": "Пользователь",
        "FEEDBACK_WHAT_TRYING": "Что вы пытались сделать",
        "FEEDBACK_WHAT_HAPPENED": "Что произошло вместо этого",
        "FEEDBACK_ERROR_MESSAGES": "Любые сообщения об ошибках, которые вы видели",
        "FEEDBACK_HELPS_IMPROVE": "Ваш отзыв помогает нам улучшить бота!",
        "FEEDBACK_FEATURE_DETAILS": "Какую функцию вы хотели бы видеть",
        "FEEDBACK_HOW_HELP": "Как это поможет вам",
        "FEEDBACK_SPECIFIC_DETAILS": "Любые конкретные детали о том, как это должно работать",
        "FEEDBACK_HELP_MAKE_BETTER": "Спасибо за помощь в улучшении бота!",
        "FEEDBACK_REPORT_ISSUE": "Сообщить о проблеме",
        "FEEDBACK_SUGGEST_FEATURE": "Предложить функцию",
        "SIMILARITY": "схожесть",
        "THANKS_NO_USERNAME": "Укажи, кому благодарность: @username",
        "THANKS_NOT_A_USER": "❌ @{username} — это {chat_type}, а не пользователь. Невозможно отправить благодарность {chat_type_dative}. Используйте @username реального пользователя или выберите пользователя из меню упоминаний Telegram (кнопка @).",
        "THANKS_SELF_THANK": "Ты не можешь поблагодарить сам себя.",
        "THANKS_GIVEN": "Благодарность отправлена!",
        "THANKS_NO_THANKS": "Пока нет благодарностей.",
        "THANKS_TOP_TITLE": "Топ {n} самых благодарных пользователей:",
        "THANKS_STATS_TITLE": "Статистика благодарностей:",
        "THANKS_NOW_HAS": "теперь имеет",
        "THANKS_WORD": "благодарностей",
        "HELP_TITLE": "Доступные команды:",
        "HELP_TIP": "Совет: Вы также можете использовать кнопку меню (☰) для просмотра всех доступных команд!",
        "HELP_SUPPORT": "Поддержка: Используйте /report_an_issue или /suggest_a_feature для связи с нами."
    },
        "MATCH_NOTIFICATIONS": {
            "NEW_MATCH_TITLE": "🤝 <b>Новое бизнес-знакомство</b>",
            "MATCHED_WITH": "Мы подобрали для вас контакт: {name}",
            "ABOUT_THEM": "<b>Краткая информация:</b>",
            "LOCATION": "📍 <b>Местоположение:</b> {location}",
            "DESCRIPTION": "💼 <b>О себе:</b> {description}",
            "LINKEDIN": "🔗 <b>LinkedIn:</b> <a href=\"{linkedin_url}\">{linkedin}</a>",
            "PROFILE_LINK": '👤 <b>Полный профиль:</b> <a href="{profile_url}">Открыть профиль</a>',
            "NEXT_STEPS": "<b>Следующие шаги:</b>",
            "STEP_1": "💬 Связаться в Telegram",
            "STEP_2": "☕ Назначить встречу",
            "STEP_3": "🤝 Обсудить возможности сотрудничества",
            "TELEGRAM_CONTACT": "💬 <b>Telegram:</b> <a href=\"https://t.me/{telegram_link}\">@{telegram_link}</a>",
            "VIEW_MATCHES_LATER": "📋 <i>Все контакты: /my_matches</i>",
            "SUCCESS_MESSAGE": "Успешного нетворкинга! 🚀"
        }
}

def get_messages() -> Dict[str, Any]:
    lang = os.getenv("BOT_LANGUAGE", "ru").lower()
    return BOT_MESSAGES_RU if lang == "ru" else BOT_MESSAGES_EN

# Initialize with default language, but allow runtime changes
BOT_MESSAGES = get_messages()

def get_messages_dynamic(user_id: int = None) -> Dict[str, Any]:
    """Get messages with bot language setting from environment variable"""
    # Always use bot language from environment variable, ignore user language
    return get_messages()


def validate_image_size_and_format(image_data: bytes) -> tuple[bool, str]:
    """Validate image size and format"""
    try:
        import io
        from PIL import Image
        
        # Check file size (5MB limit)
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > 5:
            return False, f"Изображение слишком большое ({size_mb:.1f}MB). Максимальный размер: 5MB"
        
        # Check image format
        with Image.open(io.BytesIO(image_data)) as img:
            format_name = img.format
            if format_name not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                return False, f"Неподдерживаемый формат изображения: {format_name}. Используйте JPEG, PNG, GIF или WebP"
            
            # Check dimensions (optional limit)
            width, height = img.size
            if width > 4096 or height > 4096:
                return False, f"Изображение слишком большое ({width}x{height}). Максимальный размер: 4096x4096"
            
            return True, f"✅ Изображение принято: {format_name}, {size_mb:.1f}MB, {width}x{height}"
    except ImportError:
        # If PIL is not available, just check size
        size_mb = len(image_data) / (1024 * 1024)
        if size_mb > 5:
            return False, f"Изображение слишком большое ({size_mb:.1f}MB). Максимальный размер: 5MB"
        return True, f"✅ Изображение принято: {size_mb:.1f}MB"
    except Exception as e:
        return False, f"Ошибка обработки изображения: {str(e)}"


def format_birthday(birthday_value, user_id: int = None) -> str:
    """Format birthday in simple format: ЧИСЛО МЕСЯЦ ГОД (e.g., 1 Января 1991)"""
    if not birthday_value:
        return ""
    
    try:
        from datetime import datetime
        
        # Parse birthday - could be string or date object
        if isinstance(birthday_value, str):
            birthday_date = datetime.strptime(birthday_value, "%Y-%m-%d").date()
        elif hasattr(birthday_value, 'year'):
            birthday_date = birthday_value
        else:
            return str(birthday_value)
        
        # Get month names from language settings
        messages = get_messages_dynamic(user_id)
        month_names = messages.get("MONTHS", [
            "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
            "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
        ])
        
        return f"{birthday_date.day} {month_names[birthday_date.month]} {birthday_date.year}"
            
    except Exception as e:
        print(f"Error formatting birthday: {e}")
        return str(birthday_value)


def build_profile_text(user_info: Dict[str, Any], user_id: int = None, is_own_profile: bool = False) -> str:
    """
    Build profile text in the format shown in the screenshot.
    Returns formatted profile information with missing field indicators.
    
    Args:
        user_info: User information dictionary
        user_id: Current user ID for language detection
        is_own_profile: If True, don't include Telegram link (no green contact card)
    """
    messages = get_messages_dynamic(user_id)
    missing_text = messages["MISSING_FIELD"]
    
    # Start with Telegram link at the top if available (blue text like t.me/aburnins)
    # Only include link for other users' profiles, not own profile
    profile_text = ""
    telegram_link = user_info.get('user_telegram_link')
    if telegram_link and not is_own_profile:
        # Format like the example: t.me/username with blue color
        profile_text += f"<a href='https://t.me/{telegram_link}' style='color: #0088cc;'>t.me/{telegram_link}</a>\n"
    
    # Build profile text - only show photo field if photo is missing
    if not user_info.get('intro_image'):
        profile_text += f"<b>Фото:</b> {missing_text}\n"
    
    # Helper function to get translated value with field-specific translations
    def get_translated_value(value, field_name=None):
        if not value or value in ['Not specified', 'No description', 'No name', 'No location', 'No skills', 'No hobbies', 'No field of activity']:
            if field_name == 'hobbies':
                return "Не указаны"
            elif field_name == 'skills':
                return "Не указаны"
            elif field_name == 'field_of_activity':
                return "Не указано"
            else:
                return missing_text
        return value
    
    profile_text += f"<b>Имя Фамилия:</b> {get_translated_value(user_info.get('intro_name'))}\n"
    profile_text += f"<b>Сфера деятельности:</b> {get_translated_value(user_info.get('field_of_activity'), 'field_of_activity')}\n"
    profile_text += f"<b>Местоположение:</b> {get_translated_value(user_info.get('intro_location'))}\n"
    profile_text += f"<b>Профиль LinkedIn:</b> {get_translated_value(user_info.get('intro_linkedin'))}\n"
    profile_text += f"<b>Описание:</b> {get_translated_value(user_info.get('intro_description'))}\n"
    profile_text += f"<b>Хобби и мотивация:</b> {get_translated_value(user_info.get('intro_hobbies_drivers'), 'hobbies')}\n"
    profile_text += f"<b>Навыки:</b> {get_translated_value(user_info.get('intro_skills'), 'skills')}\n"
    
    # Format birthday according to user's language
    birthday_formatted = format_birthday(user_info.get('intro_birthday'), user_id)
    if birthday_formatted:
        profile_text += f"<b>День рождения:</b> {birthday_formatted}"
    else:
        profile_text += f"<b>День рождения:</b> {missing_text}"
    
    # Show notification status for own profile only
    if is_own_profile:
        notifications_enabled = user_info.get('notifications_enabled', True)
        if not notifications_enabled:
            profile_text += f"\n\n⚠️ <i>Уведомления отключены</i>"

    return profile_text


def get_location_keyboard(chat_type: str = "private") -> ReplyKeyboardMarkup:
    messages = get_messages()
    # Only request location in private chats (Telegram restriction)
    request_location = chat_type == "private"
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=messages["ONBOARDING"]["LOCATION"]["SHARE_LOCATION"], request_location=request_location)],
            [KeyboardButton(text=messages["ONBOARDING"]["LOCATION"]["DONT_SHARE"])],
            [KeyboardButton(text="Выход")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_profile_confirmation_keyboard() -> ReplyKeyboardMarkup:
    messages = get_messages()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=messages["KEYBOARD"]["YES"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["CONTINUE_EDITING"])]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_edit_profile_keyboard() -> ReplyKeyboardMarkup:
    messages = get_messages()
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_LOCATION"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_NAME"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_DESCRIPTION"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_LINKEDIN"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_HOBBIES_DRIVERS"]), KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_SKILLS"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_FIELD_OF_ACTIVITY"]), KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_BIRTHDAY"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["EDIT_PHOTO"])],
            [KeyboardButton(text=messages["ONBOARDING"]["PROFILE"]["START_OVER"])],
            [KeyboardButton(text="Выход")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_save_exit_keyboard() -> ReplyKeyboardMarkup:
    """Get save/exit keyboard for onboarding"""
    messages = get_messages()
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сохранить"), KeyboardButton(text="Save")],
            [KeyboardButton(text="Выход"), KeyboardButton(text="Exit")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


def get_exit_keyboard() -> ReplyKeyboardMarkup:
    """Get exit keyboard for other commands"""
    # Use bot's default language (Russian)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Выход")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard


async def start_onboarding(message: Message, state: FSMContext, db_pool):
    """Start the onboarding flow"""
    print(f"DEBUG: start_onboarding called for user {message.from_user.id}")
    # Check if user has partial data
    user_id = message.from_user.id
    user_info = await get_user_info(db_pool, user_id)
    print(f"DEBUG: user_info: {user_info}")
    
    # Check if user has all required fields (including new ones)
    required_fields = ['intro_name', 'intro_location', 'intro_description', 'intro_linkedin', 
                      'intro_hobbies_drivers', 'intro_skills', 'field_of_activity', 'intro_birthday', 'intro_image']
    has_all_fields = user_info and all(user_info.get(field) for field in required_fields)
    print(f"DEBUG: has_all_fields: {has_all_fields}")
    print(f"DEBUG: user_info exists: {user_info is not None}")
    
    if user_info and not has_all_fields:
        print("DEBUG: Going to partial onboarding confirmation")
        # User has partial data, show confirmation
        await state.set_state(OnboardingStates.partial_onboarding_confirmation)
        await show_partial_onboarding_confirmation(message, state, user_info)
    else:
        # Start fresh onboarding
        await state.set_state(OnboardingStates.waiting_for_name)
        messages = get_messages()
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["NAME"]["PROMPT"], reply_markup=keyboard)

async def show_partial_onboarding_confirmation(message: Message, state: FSMContext, user_info: dict):
    """Show partial onboarding confirmation"""
    confirmation_text = "<b>Welcome back!</b>\n\n"
    confirmation_text += "I found some information you previously entered:\n\n"
    
    if user_info.get('intro_name'):
        confirmation_text += f"✅ Name: {user_info['intro_name']}\n"
    if user_info.get('intro_location'):
        confirmation_text += f"✅ Location: {user_info['intro_location']}\n"
    if user_info.get('intro_description'):
        confirmation_text += f"✅ Description: {user_info['intro_description'][:50]}...\n"
    if user_info.get('intro_linkedin'):
        confirmation_text += f"✅ LinkedIn: {user_info['intro_linkedin']}\n"
    if user_info.get('intro_hobbies_drivers'):
        confirmation_text += f"✅ Hobbies & Drivers: {user_info['intro_hobbies_drivers'][:50]}...\n"
    if user_info.get('intro_skills'):
        confirmation_text += f"✅ Skills: {user_info['intro_skills'][:50]}...\n"
    if user_info.get('field_of_activity'):
        confirmation_text += f"✅ Field of Activity: {user_info['field_of_activity'][:50]}...\n"
    if user_info.get('intro_birthday'):
        confirmation_text += f"✅ Birthday: {user_info['intro_birthday']}\n"
    
    confirmation_text += "\nWould you like to:\n"
    confirmation_text += "1. Continue with existing information\n"
    confirmation_text += "2. Start over with fresh information\n"
    confirmation_text += "3. Edit specific fields"
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Continue with existing")],
            [KeyboardButton(text="Start over")],
            [KeyboardButton(text="Edit specific fields")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    keyboard = get_exit_keyboard()
    await message.answer(confirmation_text, reply_markup=keyboard)

async def handle_partial_onboarding_confirmation(message: Message, state: FSMContext, db_pool):
    """Handle partial onboarding confirmation response"""
    response = message.text.strip().lower()
    
    if "continue" in response:
        # Load existing data and continue from where they left off
        user_id = message.from_user.id
        user_info = await get_user_info(db_pool, user_id)
        
        # Determine what's missing and continue from there
        if not user_info.get('intro_name'):
            await state.set_state(OnboardingStates.waiting_for_name)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["NAME"]["PROMPT"])
        elif not user_info.get('intro_location'):
            await state.set_state(OnboardingStates.waiting_for_location)
            keyboard = get_location_keyboard(message.chat.type)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["PROMPT"], reply_markup=keyboard)
        elif not user_info.get('intro_description'):
            await state.set_state(OnboardingStates.waiting_for_description)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["DESCRIPTION"]["PROMPT"])
        elif not user_info.get('intro_linkedin'):
            await state.set_state(OnboardingStates.waiting_for_linkedin)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LINKEDIN"]["PROMPT"])
        elif not user_info.get('intro_hobbies_drivers'):
            await state.set_state(OnboardingStates.waiting_for_hobbies_drivers)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["HOBBIES_DRIVERS"]["PROMPT"])
        elif not user_info.get('intro_skills'):
            await state.set_state(OnboardingStates.waiting_for_skills)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["SKILLS"]["PROMPT"])
        elif not user_info.get('field_of_activity'):
            await state.set_state(OnboardingStates.waiting_for_field_of_activity)
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["FIELD_OF_ACTIVITY"]["PROMPT"])
        elif not user_info.get('intro_birthday'):
            await state.set_state(OnboardingStates.waiting_for_birthday)
            await show_birthday_calendar(message)
        elif not user_info.get('intro_image'):
            await state.set_state(OnboardingStates.waiting_for_photo)
            keyboard = get_exit_keyboard()
            await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["PHOTO"]["PROMPT"], reply_markup=keyboard)
        else:
            # All fields are complete, show profile confirmation
            await state.set_state(OnboardingStates.profile_confirmation)
            profile_text = build_profile_details(user_info)
            keyboard = get_profile_confirmation_keyboard()
            await message.answer(profile_text, reply_markup=keyboard)
    
    elif "start over" in response:
        # Clear existing data and start fresh
        await state.clear()
        await state.set_state(OnboardingStates.waiting_for_name)
        await message.answer("Starting fresh! " + get_messages_dynamic(message.from_user.id)["ONBOARDING"]["NAME"]["PROMPT"])
    
    elif "edit" in response:
        # Show edit options
        await show_edit_options(message, state, db_pool)
    
    else:
        await message.answer("Пожалуйста, выберите один из вариантов выше.")

async def show_edit_options(message: Message, state: FSMContext, db_pool):
    """Show edit options for partial onboarding"""
    user_id = message.from_user.id
    user_info = await get_user_info(db_pool, user_id)
    
    edit_text = "📝 <b>What would you like to edit?</b>\n\n"
    
    keyboard_buttons = []
    if user_info.get('intro_name'):
        keyboard_buttons.append([KeyboardButton(text="Edit Name")])
    if user_info.get('intro_location'):
        keyboard_buttons.append([KeyboardButton(text="Edit Location")])
    if user_info.get('intro_description'):
        keyboard_buttons.append([KeyboardButton(text="Edit Description")])
    if user_info.get('intro_linkedin'):
        keyboard_buttons.append([KeyboardButton(text="Edit LinkedIn")])
    if user_info.get('intro_image'):
        keyboard_buttons.append([KeyboardButton(text="Edit Photo")])
    
    keyboard_buttons.append([KeyboardButton(text="Continue to Profile Review")])
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(edit_text, reply_markup=keyboard)
    await state.set_state("waiting_for_edit_choice")


async def handle_name(message: Message, state: FSMContext, db_pool):
    """Handle name input"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["NAME"]["INVALID"])
        return
    
    name = message.text.strip()
    
    # Validate name
    is_valid, error_message = InputValidator.validate_name(name)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное имя:")
        return
    
    # Sanitize input
    name = InputValidator.sanitize_input(name)
    
    await state.update_data(name=name)
    await state.set_state(OnboardingStates.waiting_for_location)
    
    keyboard = get_location_keyboard(message.chat.type)
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["PROMPT"], reply_markup=keyboard)


async def handle_location(message: Message, state: FSMContext, db_pool):
    """Handle location input"""
    print(f"DEBUG: handle_location called for user {message.from_user.id}")
    print(f"DEBUG: Message has location: {message.location is not None}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    location_text = None
    
    if message.location:
        # Use improved geocoding function
        lat = message.location.latitude
        lon = message.location.longitude
        print(f"DEBUG: Got location: lat={lat}, lon={lon}")
        location_text = await geocode_location(lat, lon)
        print(f"DEBUG: Geocoded location: '{location_text}'")
    elif message.text and message.text.lower() not in [get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["DONT_SHARE"].lower(), "пропустить", "skip"]:
        location_text = message.text.strip()
        
        # Validate text location
        is_valid, error_message = InputValidator.validate_location(location_text)
        if not is_valid:
            await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное местоположение:")
            return
        
        # Sanitize input
        location_text = InputValidator.sanitize_input(location_text)

        # Normalize and enrich via geocoding if API is available
        api_key = os.getenv("GEOCODING_API_KEY")
        if api_key:
            try:
                import httpx
                params = {"address": location_text, "key": api_key}
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    data = resp.json()
                    if data.get("results"):
                        # Use the first result's formatted address for normalization
                        location_text = data["results"][0]["formatted_address"]
            except Exception:
                # Keep original text if geocoding fails
                pass
    elif message.text == get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["DONT_SHARE"]:
        # User doesn't want to share location - set empty location
        location_text = ""
    
    # location_text can be None (no input), empty string (don't share), or actual location
    # Only show error if user provided invalid input (None means no input at all)
    if location_text is None:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["INVALID"])
        return
    
    print(f"DEBUG: Location processed: '{location_text}', transitioning to waiting_for_description state")
    await state.update_data(location=location_text)
    await state.set_state(OnboardingStates.waiting_for_description)
    keyboard = get_exit_keyboard()
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["DESCRIPTION"]["PROMPT"], reply_markup=keyboard)
    print(f"DEBUG: Description prompt sent")


async def handle_description(message: Message, state: FSMContext, db_pool):
    """Handle description input"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["DESCRIPTION"]["INVALID"])
        return
    
    description = message.text.strip()
    
    # Validate description
    is_valid, error_message = InputValidator.validate_description(description)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное описание:")
        return
    
    # Sanitize input
    description = InputValidator.sanitize_input(description)
    
    await state.update_data(description=description)
    await state.set_state(OnboardingStates.waiting_for_linkedin)
    
    keyboard = get_exit_keyboard()
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LINKEDIN"]["PROMPT"], reply_markup=keyboard)


async def handle_linkedin(message: Message, state: FSMContext, db_pool):
    """Handle LinkedIn input"""
    print(f"DEBUG: LinkedIn handler called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        # Allow empty LinkedIn - set to empty string
        linkedin_url = ""
    else:
        linkedin_url = message.text.strip()
    
    # Validate LinkedIn URL (now allows empty values and "Не указан" alternatives)
    is_valid, error_message = InputValidator.validate_linkedin_url(linkedin_url)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректный URL профиля LinkedIn или 'Не указан':")
        return
    
    # Sanitize input
    linkedin_url = InputValidator.sanitize_input(linkedin_url)
    
    print(f"DEBUG: LinkedIn URL validated: {linkedin_url}")
    print(f"DEBUG: Transitioning to waiting_for_hobbies_drivers state")
    
    await state.update_data(linkedin=linkedin_url)
    await state.set_state(OnboardingStates.waiting_for_hobbies_drivers)
    
    keyboard = get_exit_keyboard()
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["HOBBIES_DRIVERS"]["PROMPT"], reply_markup=keyboard)


async def handle_hobbies_drivers(message: Message, state: FSMContext, db_pool):
    """Handle hobbies and drivers input"""
    print(f"DEBUG: Hobbies handler called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["HOBBIES_DRIVERS"]["INVALID"])
        return
    
    hobbies_drivers = message.text.strip()
    
    # Sanitize input
    hobbies_drivers = InputValidator.sanitize_input(hobbies_drivers)
    
    print(f"DEBUG: Hobbies validated: {hobbies_drivers}")
    print(f"DEBUG: Transitioning to waiting_for_skills state")
    
    await state.update_data(hobbies_drivers=hobbies_drivers)
    await state.set_state(OnboardingStates.waiting_for_skills)
    
    # Debug: Check current state
    current_state = await state.get_state()
    print(f"DEBUG: Current state after transition: {current_state}")
    
    keyboard = get_exit_keyboard()
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["SKILLS"]["PROMPT"], reply_markup=keyboard)


async def handle_field_of_activity(message: Message, state: FSMContext, db_pool):
    """Handle field of activity input"""
    print(f"DEBUG: Field of activity handler called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["FIELD_OF_ACTIVITY"]["INVALID"])
        return
    
    field_of_activity = message.text.strip()
    
    # Sanitize input
    field_of_activity = InputValidator.sanitize_input(field_of_activity)
    
    print(f"DEBUG: Field of activity validated: {field_of_activity}")
    print(f"DEBUG: Transitioning to waiting_for_birthday state")
    
    await state.update_data(field_of_activity=field_of_activity)
    await state.set_state(OnboardingStates.waiting_for_birthday)
    
    # Debug: Check current state
    current_state = await state.get_state()
    print(f"DEBUG: Current state after transition: {current_state}")
    
    # Show birthday calendar instead of text prompt
    await show_birthday_calendar(message, is_edit_mode=False)


async def handle_skills(message: Message, state: FSMContext, db_pool):
    """Handle skills input"""
    print(f"DEBUG: Skills handler called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["SKILLS"]["INVALID"])
        return
    
    skills = message.text.strip()
    
    # Sanitize input
    skills = InputValidator.sanitize_input(skills)
    
    print(f"DEBUG: Skills validated: {skills}")
    print(f"DEBUG: Transitioning to waiting_for_field_of_activity state")
    
    await state.update_data(skills=skills)
    await state.set_state(OnboardingStates.waiting_for_field_of_activity)
    
    # Debug: Check current state
    current_state = await state.get_state()
    print(f"DEBUG: Current state after transition: {current_state}")
    
    keyboard = get_exit_keyboard()
    await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["FIELD_OF_ACTIVITY"]["PROMPT"], reply_markup=keyboard)


async def show_birthday_calendar(message: Message, is_edit_mode: bool = False):
    """Show birthday calendar picker starting with year selection"""
    keyboard = create_birthday_calendar(step="year", user_id=message.from_user.id, is_edit_mode=is_edit_mode)
    
    messages = get_messages_dynamic(message.from_user.id)
    await message.answer(
        messages["ONBOARDING"]["BIRTHDAY"]["PROMPT"] + "\n\n" + 
        messages["ONBOARDING"]["BIRTHDAY"]["SELECT_YEAR"],
        reply_markup=keyboard
    )


async def handle_birthday(message: Message, state: FSMContext, db_pool):
    """Handle birthday input - show calendar picker or process text input"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from datetime import datetime, timedelta
    import re
    
    print(f"DEBUG: Birthday handler called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    if message.text:
        # User sent text input
        birthday_text = message.text.strip()
        
        # Validate birthday format (YYYY-MM-DD)
        birthday_pattern = r'^\d{4}-\d{2}-\d{2}$'
        if re.match(birthday_pattern, birthday_text):
            # Validate date
            try:
                date_obj = datetime.strptime(birthday_text, '%Y-%m-%d')
                if date_obj > datetime.now():
                    await message.answer("❌ День рождения не может быть в будущем. Пожалуйста, введите корректную дату.")
                    return
                # Check if we're in edit mode or onboarding
                current_state = await state.get_state()
                if current_state and current_state.startswith("ProfileStates:editing_birthday"):
                    # In edit mode: save and return to edit menu without advancing onboarding
                    from openai import AsyncOpenAI
                    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
                    await auto_save_single_field(message, state, db_pool, "birthday", birthday_text, openai_client)
                    messages_local = get_messages_dynamic(message.from_user.id)
                    keyboard = get_edit_profile_keyboard()
                    formatted_bday = format_birthday(birthday_text, message.from_user.id)
                    await message.answer(f"✅ Дата рождения обновлена: {formatted_bday}", reply_markup=keyboard)
                    await state.set_state(ProfileStates.editing_profile)
                    return
                else:
                    # Onboarding flow: proceed to photo step
                    await state.update_data(birthday=birthday_text)
                    await state.set_state(OnboardingStates.waiting_for_photo)
                    keyboard = get_exit_keyboard()
                    await message.answer(f"✅ Birthday set: {birthday_text}\n\n" + get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["PHOTO"]["PROMPT"], reply_markup=keyboard)
                    return
            except ValueError:
                pass
        
        # If we get here, the format was invalid
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["BIRTHDAY"]["INVALID"])
        return
    
    # Create calendar keyboard
    keyboard = create_birthday_calendar(user_id=message.from_user.id, is_edit_mode=False)
    
    messages = get_messages_dynamic(message.from_user.id)
    await message.answer(
        messages["ONBOARDING"]["BIRTHDAY"]["PROMPT"] + "\n\n" + 
        messages["ONBOARDING"]["BIRTHDAY"]["SELECT_YEAR"],
        reply_markup=keyboard
    )


def create_birthday_calendar(year: int = None, month: int = None, step: str = "year", user_id: int = None, is_edit_mode: bool = False) -> InlineKeyboardMarkup:
    """Create a calendar keyboard for birthday selection with year/month/day steps"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from datetime import datetime
    import calendar
    
    # Get translations
    messages = get_messages_dynamic(user_id)
    
    if year is None:
        year = datetime.now().year - 25  # Default to 25 years ago
    if month is None:
        month = datetime.now().month
    
    keyboard = []
    
    if step == "year":
        # Year selection - show years in groups of 10
        current_year = datetime.now().year
        start_year = max(1950, year - 5)  # Show 10 years around selected year
        end_year = min(current_year, start_year + 9)
        
        # Navigation buttons - always show them
        nav_row = []
        if start_year > 1950:
            nav_row.append(InlineKeyboardButton(text="◀️◀️", callback_data=f"birthday_year_prev_{start_year}"))
        else:
            nav_row.append(InlineKeyboardButton(text="◀️◀️", callback_data="birthday_ignore"))
        
        nav_row.append(InlineKeyboardButton(text=f"{start_year}-{end_year}", callback_data="birthday_ignore"))
        
        if end_year < current_year:
            nav_row.append(InlineKeyboardButton(text="▶️▶️", callback_data=f"birthday_year_next_{end_year}"))
        else:
            nav_row.append(InlineKeyboardButton(text="▶️▶️", callback_data="birthday_ignore"))
        
        keyboard.append(nav_row)
        
        # Year buttons (2 rows of 5)
        years_row1 = []
        years_row2 = []
        for i, y in enumerate(range(start_year, end_year + 1)):
            if i < 5:
                years_row1.append(InlineKeyboardButton(text=str(y), callback_data=f"birthday_year_select_{y}"))
            else:
                years_row2.append(InlineKeyboardButton(text=str(y), callback_data=f"birthday_year_select_{y}"))
        
        if years_row1:
            keyboard.append(years_row1)
        if years_row2:
            keyboard.append(years_row2)
            
    elif step == "month":
        # Month selection
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["YEAR_SELECTED"].format(year=year), callback_data="birthday_ignore")])
        
        # Month buttons (3 rows of 4) - use translations
        month_names_short = messages.get("MONTHS_SHORT", [
            "", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
            "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
        ])
        months = [
            (month_names_short[1], 1), (month_names_short[2], 2), (month_names_short[3], 3), (month_names_short[4], 4),
            (month_names_short[5], 5), (month_names_short[6], 6), (month_names_short[7], 7), (month_names_short[8], 8),
            (month_names_short[9], 9), (month_names_short[10], 10), (month_names_short[11], 11), (month_names_short[12], 12)
        ]
        
        for i in range(0, len(months), 4):
            row = []
            for j in range(4):
                if i + j < len(months):
                    month_name, month_num = months[i + j]
                    row.append(InlineKeyboardButton(text=month_name, callback_data=f"birthday_month_select_{year}_{month_num}"))
            keyboard.append(row)
            
    elif step == "day":
        # Day selection
        month_names = messages.get("MONTHS", [
            "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
            "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря"
        ])
        keyboard.append([InlineKeyboardButton(text=f"{month_names[month]} {year}", callback_data="birthday_ignore")])
        
        cal = calendar.monthcalendar(year, month)
        
        # Days of week - use translations
        weekdays = messages.get("WEEKDAYS", ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"])
        keyboard.append([InlineKeyboardButton(text=day, callback_data="birthday_ignore") for day in weekdays])
        
        # Calendar days
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(text=" ", callback_data="birthday_ignore"))
                else:
                    # Check if date is in the future (not valid for birthday)
                    try:
                        date_obj = datetime(year, month, day)
                        if date_obj > datetime.now():
                            row.append(InlineKeyboardButton(text=" ", callback_data="birthday_ignore"))
                        else:
                            row.append(InlineKeyboardButton(
                                text=str(day), 
                                callback_data=f"birthday_select_{year}_{month:02d}_{day:02d}"
                            ))
                    except ValueError:
                        row.append(InlineKeyboardButton(text=" ", callback_data="birthday_ignore"))
            keyboard.append(row)
    
    # Add navigation and skip buttons
    if step == "year":
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["SKIP"], callback_data="birthday_skip")])
    elif step == "month":
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["BACK_TO_YEAR"], callback_data=f"birthday_back_year_{year}")])
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["SKIP"], callback_data="birthday_skip")])
    elif step == "day":
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["BACK_TO_MONTH"], callback_data=f"birthday_back_month_{year}_{month}")])
        keyboard.append([InlineKeyboardButton(text=messages["ONBOARDING"]["BIRTHDAY"]["SKIP"], callback_data="birthday_skip")])
        
        # Add "Clear Birthday" option only when in edit mode
        if is_edit_mode:
            keyboard.append([InlineKeyboardButton(text="🗑️ Удалить дату рождения", callback_data="birthday_clear")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def handle_birthday_callback(callback_query, state: FSMContext, db_pool):
    """Handle birthday calendar callback queries"""
    from aiogram.types import CallbackQuery
    from datetime import datetime
    
    print(f"DEBUG: Birthday callback handler called for user {callback_query.from_user.id}")
    print(f"DEBUG: Callback data: '{callback_query.data}'")
    
    data = callback_query.data
    
    if data.startswith("birthday_year_select_"):
        # User selected a year
        year = int(data.split("_")[3])
        messages = get_messages_dynamic(callback_query.from_user.id)
        current_state = await state.get_state()
        is_edit_mode = current_state and current_state.startswith("ProfileStates:editing_birthday")
        keyboard = create_birthday_calendar(year=year, step="month", user_id=callback_query.from_user.id, is_edit_mode=is_edit_mode)
        await callback_query.message.edit_text(
            f"{messages['ONBOARDING']['BIRTHDAY']['YEAR_SELECTED'].format(year=year)}\n\n{messages['ONBOARDING']['BIRTHDAY']['SELECT_MONTH']}",
            reply_markup=keyboard
        )
        
    elif data.startswith("birthday_month_select_"):
        # User selected a month
        parts = data.split("_")
        year = int(parts[3])
        month = int(parts[4])
        messages = get_messages_dynamic(callback_query.from_user.id)
        current_state = await state.get_state()
        is_edit_mode = current_state and current_state.startswith("ProfileStates:editing_birthday")
        keyboard = create_birthday_calendar(year=year, month=month, step="day", user_id=callback_query.from_user.id, is_edit_mode=is_edit_mode)
        await callback_query.message.edit_text(
            messages["ONBOARDING"]["BIRTHDAY"]["SELECT_DAY"],
            reply_markup=keyboard
        )
        
    elif data.startswith("birthday_select_"):
        # User selected a date
        parts = data.split("_")
        year = int(parts[2])
        month = int(parts[3])
        day = int(parts[4])
        
        birthday_text = f"{year}-{month:02d}-{day:02d}"
        # Check current state to distinguish edit vs onboarding
        current_state = await state.get_state()
        if current_state and current_state.startswith("ProfileStates:editing_birthday"):
            # Save directly using the correct user id (callbacks' message.from_user is the bot)
            user_id = callback_query.from_user.id
            from datetime import datetime as _dt
            try:
                birthday_date = _dt.strptime(birthday_text, "%Y-%m-%d").date()
            except ValueError:
                birthday_date = None
            async with db_pool.acquire() as conn:
                if birthday_date:
                    await conn.execute(
                        "UPDATE public.users SET intro_birthday = $1, updated_at = now() WHERE user_id = $2",
                        birthday_date, user_id
                    )
                else:
                    await conn.execute(
                        "UPDATE public.users SET intro_birthday = $1, updated_at = now() WHERE user_id = $2",
                        birthday_text, user_id
                    )
            # Show confirmation and refreshed profile
            formatted_bday = format_birthday(birthday_text, user_id)
            await callback_query.message.edit_text(f"✅ Дата рождения обновлена: {formatted_bday}")
            
            # Check if birthday is today and send greeting immediately
            try:
                from scheduler import get_scheduler_bot_and_pool
                from birthday_greetings import check_birthday_for_user
                bot, pool = get_scheduler_bot_and_pool()
                # Run in background to avoid blocking
                asyncio.create_task(check_birthday_for_user(bot, pool, user_id))
            except Exception as e:
                logger.warning(f"Could not check birthday immediately for user {user_id}: {e}")
            # Mark that changes were made in this editing session
            await state.update_data(changes_made=True)
            messages_local = get_messages_dynamic(user_id)
            # Send updated profile text
            user_info = await get_user_info(db_pool, user_id)
            profile_text = build_profile_text(user_info, user_id, is_own_profile=True)
            await callback_query.message.answer(profile_text)
            # Show edit menu
            keyboard = get_edit_profile_keyboard()
            await callback_query.message.answer(messages_local["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
            await state.set_state(ProfileStates.editing_profile)
        else:
            # Onboarding behavior
            await state.update_data(birthday=birthday_text)
            await state.set_state(OnboardingStates.waiting_for_photo)
            # Send birthday selected confirmation
            await callback_query.message.edit_text(
                get_messages_dynamic(callback_query.from_user.id)['ONBOARDING']['BIRTHDAY']['BIRTHDAY_SELECTED'].format(birthday_text=birthday_text)
            )
            
            # Send photo prompt as separate message
            await callback_query.message.answer(
                get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["PHOTO"]["PROMPT"]
            )
        
    elif data.startswith("birthday_year_prev_"):
        # Navigate to previous year range
        start_year = int(data.split("_")[3])
        new_start = max(1950, start_year - 10)
        keyboard = create_birthday_calendar(year=new_start, step="year", user_id=callback_query.from_user.id, is_edit_mode=False)
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
        
    elif data.startswith("birthday_year_next_"):
        # Navigate to next year range
        end_year = int(data.split("_")[3])
        new_start = end_year + 1
        keyboard = create_birthday_calendar(year=new_start, step="year", user_id=callback_query.from_user.id, is_edit_mode=False)
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
        
    elif data.startswith("birthday_back_year_"):
        # Go back to year selection with preserved year context
        year = int(data.split("_")[3])
        messages = get_messages_dynamic(callback_query.from_user.id)
        current_state = await state.get_state()
        is_edit_mode = current_state and current_state.startswith("ProfileStates:editing_birthday")
        keyboard = create_birthday_calendar(year=year, step="year", user_id=callback_query.from_user.id, is_edit_mode=is_edit_mode)
        await callback_query.message.edit_text(
            messages["ONBOARDING"]["BIRTHDAY"]["SELECT_YEAR_AGAIN"],
            reply_markup=keyboard
        )
        
    elif data.startswith("birthday_back_month_"):
        # Go back to month selection with preserved year and month context
        parts = data.split("_")
        year = int(parts[3])
        month = int(parts[4])
        messages = get_messages_dynamic(callback_query.from_user.id)
        current_state = await state.get_state()
        is_edit_mode = current_state and current_state.startswith("ProfileStates:editing_birthday")
        keyboard = create_birthday_calendar(year=year, month=month, step="month", user_id=callback_query.from_user.id, is_edit_mode=is_edit_mode)
        await callback_query.message.edit_text(
            messages["ONBOARDING"]["BIRTHDAY"]["SELECT_MONTH"],
            reply_markup=keyboard
        )
        
    elif data == "birthday_skip":
        # User wants to skip birthday
        await state.update_data(birthday=None)
        await state.set_state(OnboardingStates.waiting_for_photo)
        
        # Send birthday skip confirmation
        await callback_query.message.edit_text(
            get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["BIRTHDAY"]["SKIPPED"]
        )
        
        # Send photo prompt as separate message
        await callback_query.message.answer(
            get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["PHOTO"]["PROMPT"]
        )
    
    elif data == "birthday_clear":
        # User wants to clear birthday
        current_state = await state.get_state()
        if current_state and current_state.startswith("ProfileStates:editing_birthday"):
            # In edit mode: clear birthday and return to edit menu
            user_id = callback_query.from_user.id
            async with db_pool.acquire() as conn:
                await conn.execute(
                    "UPDATE public.users SET intro_birthday = NULL, updated_at = now() WHERE user_id = $1",
                    user_id
                )
            # Show confirmation
            await callback_query.message.edit_text("✅ Дата рождения удалена")
            # Mark that changes were made in this editing session
            await state.update_data(changes_made=True)
            messages_local = get_messages_dynamic(user_id)
            # Send updated profile text
            user_info = await get_user_info(db_pool, user_id)
            profile_text = build_profile_text(user_info, user_id, is_own_profile=True)
            await callback_query.message.answer(profile_text)
            # Show edit menu
            keyboard = get_edit_profile_keyboard()
            await callback_query.message.answer(messages_local["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
            await state.set_state(ProfileStates.editing_profile)
        else:
            # In onboarding mode: clear birthday and proceed to photo step
            await state.update_data(birthday=None)
            await state.set_state(OnboardingStates.waiting_for_photo)
            # Send birthday cleared confirmation
            await callback_query.message.edit_text(
                get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["BIRTHDAY"]["BIRTHDAY_CLEARED"]
            )
            
            # Send photo prompt as separate message
            await callback_query.message.answer(
                get_messages_dynamic(callback_query.from_user.id)["ONBOARDING"]["PHOTO"]["PROMPT"]
            )
    
    await callback_query.answer()


async def handle_photo(message: Message, state: FSMContext, db_pool):
    """Handle photo input"""
    print(f"DEBUG: handle_photo called for user {message.from_user.id}")
    print(f"DEBUG: Message has photo: {message.photo is not None}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.clear()
        await message.answer("Регистрация отменена. Используйте /start для начала заново.", reply_markup=ReplyKeyboardRemove())
        return
    
    if not message.photo:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["PHOTO"]["INVALID"])
        return
    
    # Use the largest photo
    photo = max(message.photo, key=lambda p: p.file_size)
    photo_id = photo.file_id
    
    # Validate photo ID
    is_valid, error_message = InputValidator.validate_photo(photo_id)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, попробуйте отправить фото еще раз:")
        return
    
    # Download and convert photo to base64
    try:
        import base64
        import httpx
        
        # Get file info from Telegram
        async with httpx.AsyncClient() as client:
            file_response = await client.get(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
                params={"file_id": photo_id}
            )
            file_data = file_response.json()
            
            if file_data.get("ok"):
                file_path = file_data["result"]["file_path"]
                image_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                
                # Download the image
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                image_data = image_response.content
                
                # Validate image before processing
                is_valid, validation_message = validate_image_size_and_format(image_data)
                if not is_valid:
                    await message.answer(f"❌ {validation_message}")
                    return
                
                # Show validation success
                await message.answer(validation_message)
                
                # Convert to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                await state.update_data(photo_base64=image_base64)
                await message.answer("✅ Фото сохранено успешно!")
            else:
                await message.answer("❌ Не удалось обработать фото. Пожалуйста, попробуйте еще раз.")
                return
                
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await message.answer("❌ Не удалось обработать фото. Пожалуйста, попробуйте еще раз.")
        return
    
    print(f"DEBUG: Photo processed successfully, transitioning to profile_confirmation state")
    await state.set_state(OnboardingStates.profile_confirmation)
    
    # Show profile summary and ask for confirmation
    data = await state.get_data()
    messages = get_messages()
    fields = messages['ONBOARDING']['PROFILE']['FIELDS']
    
    profile_text = f"{fields['NAME']} {data.get('name', 'Not set')}\n"
    profile_text += f"{fields['FIELD_OF_ACTIVITY']} {data.get('field_of_activity', 'Not set')}\n"
    profile_text += f"{fields['LOCATION']} {data.get('location', 'Not set')}\n"
    profile_text += f"{fields['DESCRIPTION']} {data.get('description', 'Not set')}\n"
    profile_text += f"{fields['LINKEDIN']} {data.get('linkedin', 'Not set')}\n"
    profile_text += f"{fields['HOBBIES_DRIVERS']} {data.get('hobbies_drivers', 'Not set')}\n"
    profile_text += f"{fields['SKILLS']} {data.get('skills', 'Not set')}\n"
    profile_text += f"{fields['BIRTHDAY']} {data.get('birthday', 'Not set')}\n"
    profile_text += f"{fields['PHOTO']} {fields['PHOTO_SET'] if data.get('photo_base64') else fields['PHOTO_NOT_SET']}\n\n"
    profile_text += messages['ONBOARDING']['PROFILE']['ASK_CONFIRM_PROFILE']
    
    keyboard = get_profile_confirmation_keyboard()
    await message.answer(profile_text, reply_markup=keyboard)
    print(f"DEBUG: Profile confirmation message sent")


async def handle_profile_confirmation(message: Message, state: FSMContext, db_pool, openai_client=None):
    """Handle profile confirmation"""
    print(f"DEBUG: Profile confirmation handler called with text: '{message.text}'")
    messages = get_messages_dynamic(message.from_user.id)
    print(f"DEBUG: Expected YES value: '{messages['KEYBOARD']['YES']}'")
    print(f"DEBUG: Text matches: {message.text == messages['KEYBOARD']['YES']}")
    
    if (message.text == messages["KEYBOARD"]["YES"] or 
        message.text and message.text.lower() in ["yes", "да", "y", "д"]):
        # Check if all required fields are present in FSM state before saving
        user_id = message.from_user.id
        data = await state.get_data()
        
        # Check for missing fields in FSM state - only truly required fields
        required_fields = ['name', 'description']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            # Some fields are missing, ask for them
            await message.answer(f"❌ В вашем профиле отсутствует информация: {', '.join(missing_fields)}. Позвольте мне запросить недостающие данные.")
            
            # Continue with missing required fields only
            if not data.get('name'):
                await state.set_state(OnboardingStates.waiting_for_name)
                await message.answer(messages["ONBOARDING"]["NAME"]["PROMPT"])
            elif not data.get('description'):
                await state.set_state(OnboardingStates.waiting_for_description)
                await message.answer(messages["ONBOARDING"]["DESCRIPTION"]["PROMPT"])
            return
        
        # All fields are present, save profile to database
        data = await state.get_data()
        
        try:
            # Vectorize description if available, otherwise create default vector
            # This ensures users always have a vector_description so /my_matches works
            description_vector = None
            if data.get("description") and len(data.get("description", "").strip()) >= 10:
                description_vector = await vectorize_description(data.get("description"), openai_client)
                if description_vector:
                    print(f"Generated {len(description_vector)}-dimensional vector for user {user_id}")
                else:
                    print(f"Failed to vectorize description for user {user_id}")
            
            # If no vector was created (no description or vectorization failed), create default vector
            if description_vector is None:
                try:
                    from vectorization import create_default_vector
                    description_vector = await create_default_vector()
                    print(f"Created default vector for user {user_id} (no description or vectorization failed)")
                except Exception as e:
                    print(f"Warning: Failed to create default vector for user {user_id}: {e}")
                    # Fallback: use zero vector
                    description_vector = [0.0] * 3072
            
            # Extract Telegram username from user info
            # Use same logic as in thanks.py: username if available, otherwise user_id as string
            # This ensures consistency: user_telegram_link always contains a valid identifier
            telegram_username = None
            if message.from_user.username:
                # Normalize username: remove @ if present
                telegram_username = message.from_user.username.strip()
                if telegram_username.startswith('@'):
                    telegram_username = telegram_username[1:]
            else:
                # No username available - use user_id as string (same as in thanks.py)
                # This is the reliable identifier for users without usernames
                telegram_username = str(user_id)
            
            await set_user_onboarding_data(
                db_pool,
                user_id,
                {
                    "name": data.get("name"),
                    "location": data.get("location"),
                    "description": data.get("description"),
                    "linkedin": data.get("linkedin"),
                    "hobbies_drivers": data.get("hobbies_drivers"),
                    "skills": data.get("skills"),
                    "field_of_activity": data.get("field_of_activity"),
                    "birthday": data.get("birthday"),
                    "photoId": data.get("photo_base64"),  # Store base64 instead of file ID
                    "user_telegram_link": telegram_username  # Always set: username or user_id as string
                },
                {
                    "descriptionVector": description_vector,
                    "locationVector": None
                }
            )
            
            await upsert_user_state(db_pool, user_id, "ACTIVE", message.chat.id)
            await state.clear()
            await message.answer(messages["ONBOARDING"]["PROFILE"]["CONFIRM"], reply_markup=ReplyKeyboardRemove())
            
            # Trigger automatic matching after successful onboarding
            try:
                from match_system import run_automatic_matching
                await run_automatic_matching()
            except Exception as e:
                print(f"Error running automatic matching: {e}")
            
        except Exception as e:
            print(f"Error saving profile: {e}")
            await message.answer(messages["ONBOARDING"]["PROFILE"]["ERROR"])
    
    elif (message.text == messages["ONBOARDING"]["PROFILE"]["CONTINUE_EDITING"] or
          message.text and message.text.lower() in ["edit", "редактировать", "изменить", "change"]):
        # Restart onboarding
        await state.clear()
        await message.answer("Продолжаем редактирование профиля...", reply_markup=ReplyKeyboardRemove())
        await start_onboarding(message, state, db_pool)
    
    else:
        # Invalid response
        keyboard = get_profile_confirmation_keyboard()
        await message.answer("Пожалуйста, выберите Да или Продолжить редактирование.\n\nИли напишите:\n• \"да\" чтобы подтвердить\n• \"редактировать\" чтобы изменить", reply_markup=keyboard)


# Profile viewing and editing functions
async def build_profile_details(user_info: Dict[str, Any]) -> str:
    """Build profile details string from user info"""
    messages = get_messages()
    fields = messages['ONBOARDING']['PROFILE']['FIELDS']
    details = []
    
    if user_info.get("intro_name"):
        details.append(f"{fields['NAME']} {user_info['intro_name']}")
    if user_info.get("field_of_activity"):
        details.append(f"{fields['FIELD_OF_ACTIVITY']} {user_info['field_of_activity']}")
    if user_info.get("intro_location"):
        details.append(f"{fields['LOCATION']} {user_info['intro_location']}")
    if user_info.get("intro_description"):
        details.append(f"{fields['DESCRIPTION']} {user_info['intro_description']}")
    if user_info.get("intro_linkedin"):
        details.append(f"{fields['LINKEDIN']} {user_info['intro_linkedin']}")
    if user_info.get("intro_hobbies_drivers"):
        details.append(f"{fields['HOBBIES_DRIVERS']} {user_info['intro_hobbies_drivers']}")
    if user_info.get("intro_skills"):
        details.append(f"{fields['SKILLS']} {user_info['intro_skills']}")
    if user_info.get("intro_birthday"):
        birthday_formatted = format_birthday(user_info['intro_birthday'])
        details.append(f"{fields['BIRTHDAY']} {birthday_formatted or user_info['intro_birthday']}")
    if user_info.get("intro_image"):
        details.append(f"{fields['PHOTO']} {fields['PHOTO_SET']}")
    else:
        details.append(f"{fields['PHOTO']} {fields['PHOTO_NOT_SET']}")
    
    return "\n".join(details)


async def handle_view_profile(message: Message, state: FSMContext, db_pool):
    """Handle /view_profile command"""
    try:
        print(f"DEBUG: view_profile command called by user {message.from_user.id}")
        user_id = message.from_user.id
        
        # First, check if user exists by Telegram user_id
        user_info = await get_user_info(db_pool, user_id)
        
        # If not found by user_id, check if user exists by username (for frontend-created users)
        if not user_info and message.from_user.username:
            async with db_pool.acquire() as conn:
                # Look for user with matching username and negative user_id (temporary)
                existing_user = await conn.fetchrow(
                    "SELECT user_id, user_telegram_link FROM users WHERE user_telegram_link = $1 AND user_id < 0",
                    message.from_user.username
                )
                
                if existing_user:
                    print(f"DEBUG: Found frontend-created user with temporary ID {existing_user['user_id']}, updating to {user_id}")
                    # Update the user_id to the actual Telegram user_id, preserving finishedonboarding and state
                    finishedonboarding_value = existing_user.get('finishedonboarding', True)
                    state_value = existing_user.get('state', 'ACTIVE')
                    await conn.execute(
                        "UPDATE users SET user_id = $1, chat_id = $1, finishedonboarding = $3, state = $4, updated_at = NOW() WHERE user_id = $2",
                        user_id, existing_user['user_id'], finishedonboarding_value, state_value
                    )
                    print(f"DEBUG: Updated user_id to {user_id}, preserved finishedonboarding={finishedonboarding_value}, state={state_value}")
                    # Now get the updated user info
                    user_info = await get_user_info(db_pool, user_id)
        
        print(f"DEBUG: user_info retrieved: {user_info}")
        
        if not user_info:
            await message.answer("Профиль не найден. Пожалуйста, сначала завершите регистрацию с помощью /start")
            return
        
        # Send photo first if available
        if user_info.get("intro_image"):
            print(f"DEBUG: Sending photo (image data length: {len(user_info['intro_image'])})")
            try:
                import base64
                import aiohttp
                from io import BytesIO
                from aiogram.types import BufferedInputFile
                
                image_data = user_info["intro_image"]
                
                # Handle different image formats
                if image_data.startswith('data:image/'):
                    # Data URL format - extract base64 part
                    base64_data = image_data.split(',')[1]
                    photo_data = base64.b64decode(base64_data)
                elif image_data.startswith(('http://', 'https://')):
                    # URL format - download and convert to base64
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_data) as response:
                            if response.status == 200:
                                photo_data = await response.read()
                            else:
                                print(f"DEBUG: Failed to download image from URL: {response.status}")
                                return
                else:
                    # Assume it's raw base64 data
                    photo_data = base64.b64decode(image_data)
                
                # Create BufferedInputFile for aiogram
                input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                await message.answer_photo(input_file)
            except Exception as photo_error:
                print(f"DEBUG: Error sending photo: {photo_error}")
                # Continue without photo if there's an error
        
        # Send profile details using new format - view only, no editing
        messages = get_messages_dynamic(user_id)
        profile_text = build_profile_text(user_info, user_id, is_own_profile=True)
        
        print(f"DEBUG: Sending profile text: {profile_text}")
        await message.answer(profile_text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        # No state change needed for view-only mode
        print(f"DEBUG: view_profile completed successfully")
    except Exception as e:
        print(f"ERROR in handle_view_profile: {e}")
        await message.answer(f"Ошибка при просмотре профиля: {str(e)}")


async def handle_edit_profile(message: Message, state: FSMContext, db_pool):
    """Handle /edit_profile command"""
    user_id = message.from_user.id
    
    # First, check if user exists by Telegram user_id
    user_info = await get_user_info(db_pool, user_id)
    
    # If not found by user_id, check if user exists by username (for frontend-created users)
    if not user_info and message.from_user.username:
        async with db_pool.acquire() as conn:
            # Look for user with matching username and negative user_id (temporary)
            existing_user = await conn.fetchrow(
                "SELECT user_id, user_telegram_link FROM users WHERE user_telegram_link = $1 AND user_id < 0",
                message.from_user.username
            )
            
            if existing_user:
                print(f"DEBUG: Found frontend-created user with temporary ID {existing_user['user_id']}, updating to {user_id}")
                # Update the user_id to the actual Telegram user_id
                await conn.execute(
                    "UPDATE users SET user_id = $1, chat_id = $1, updated_at = NOW() WHERE user_id = $2",
                    user_id, existing_user['user_id']
                )
                # Now get the updated user info
                user_info = await get_user_info(db_pool, user_id)
    
    if not user_info:
        await message.answer("Профиль не найден. Пожалуйста, сначала завершите регистрацию с помощью /start")
        return
    
    # Load existing data into session
    await state.update_data(
        name=user_info.get("intro_name"),
        location=user_info.get("intro_location"),
        description=user_info.get("intro_description"),
        linkedin=user_info.get("intro_linkedin"),
        photo_base64=user_info.get("intro_image")  # Store as photo_base64 to match photo handler
    )
    
    # Send photo if available
    if user_info.get("intro_image"):
        try:
            import base64
            import aiohttp
            from aiogram.types import BufferedInputFile
            
            image_data = user_info["intro_image"]
            
            # Handle different image formats
            if image_data.startswith('data:image/'):
                # Data URL format - extract base64 part
                base64_data = image_data.split(',')[1]
                photo_data = base64.b64decode(base64_data)
            elif image_data.startswith(('http://', 'https://')):
                # URL format - download and convert to base64
                print(f"DEBUG: Downloading image from URL: {image_data}")
                
                # Check if it's ui-avatars.com and modify URL to request PNG format
                if 'ui-avatars.com' in image_data and 'format=' not in image_data:
                    image_data = image_data + '&format=png'
                    print(f"DEBUG: Modified URL to request PNG: {image_data}")
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_data) as response:
                        if response.status == 200:
                            photo_data = await response.read()
                            content_type = response.headers.get('content-type', 'unknown')
                            print(f"DEBUG: Downloaded image data, size: {len(photo_data)} bytes")
                            print(f"DEBUG: Image content type: {content_type}")
                            
                            # Check if it's SVG and skip if so
                            if 'svg' in content_type.lower() or photo_data.startswith(b'<svg'):
                                print(f"DEBUG: Skipping SVG image (not supported by Telegram)")
                                return
                        else:
                            print(f"DEBUG: Failed to download image from URL: {response.status}")
                            return
            else:
                # Assume it's raw base64 data
                photo_data = base64.b64decode(image_data)
            
            # Create BufferedInputFile for aiogram
            input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
            await message.answer_photo(input_file)
        except Exception as photo_error:
            print(f"DEBUG: Error sending photo in edit_profile: {photo_error}")
            # Continue without photo if there's an error
    
    # Send profile details
    profile_details = await build_profile_details(user_info)
    messages = get_messages()
    profile_text = f"{messages['ONBOARDING']['PROFILE']['SEND_PROFILE']}\n{profile_details}\n\n{messages['ONBOARDING']['PROFILE']['ASK_ANY_CHANGES']}"
    
    keyboard = get_edit_profile_keyboard()
    await message.answer(profile_text, reply_markup=keyboard)
    await state.set_state(ProfileStates.editing_profile)


async def handle_profile_view_response(message: Message, state: FSMContext, db_pool):
    """Handle response in profile viewing state"""
    if message.text and message.text.lower() in ["выход", "exit"]:
        # User cancels viewing - clear state and remove keyboard
        await state.clear()
        await message.answer("Просмотр профиля завершен.", reply_markup=ReplyKeyboardRemove())
    else:
        # Handle edit profile responses - delegate to edit handler
        await handle_profile_edit_response(message, state, db_pool)


async def handle_profile_edit_response(message: Message, state: FSMContext, db_pool):
    """Handle detailed profile editing responses"""
    messages = get_messages_dynamic(message.from_user.id)
    
    # Initialize changes tracking if not exists
    data = await state.get_data()
    if 'changes_made' not in data:
        await state.update_data(changes_made=False)
    
    if message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_LOCATION"]:
        await state.set_state(ProfileStates.editing_location)
        keyboard = get_location_keyboard(message.chat.type)
        await message.answer(messages["ONBOARDING"]["LOCATION"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_NAME"]:
        await state.set_state(ProfileStates.editing_name)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["NAME"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_DESCRIPTION"]:
        await state.set_state(ProfileStates.editing_description)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["DESCRIPTION"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_LINKEDIN"]:
        await state.set_state(ProfileStates.editing_linkedin)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["LINKEDIN"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_PHOTO"]:
        await state.set_state(ProfileStates.editing_photo)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["PHOTO"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_HOBBIES_DRIVERS"]:
        await state.set_state(ProfileStates.editing_hobbies_drivers)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["HOBBIES_DRIVERS"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_SKILLS"]:
        await state.set_state(ProfileStates.editing_skills)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["SKILLS"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_FIELD_OF_ACTIVITY"]:
        await state.set_state(ProfileStates.editing_field_of_activity)
        keyboard = get_exit_keyboard()
        await message.answer(messages["ONBOARDING"]["FIELD_OF_ACTIVITY"]["PROMPT"], reply_markup=keyboard)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["EDIT_BIRTHDAY"]:
        await state.set_state(ProfileStates.editing_birthday)
        await show_birthday_calendar(message, is_edit_mode=True)
    
    elif message.text == messages["ONBOARDING"]["PROFILE"]["START_OVER"]:
        # Clear session data and start fresh onboarding
        await state.clear()
        await message.answer("Начинаем регистрацию заново...", reply_markup=ReplyKeyboardRemove())
        await start_onboarding(message, state, db_pool)
    
    elif message.text and message.text.lower() in ["выход", "exit"]:
        # User cancels editing - check if changes were made
        data = await state.get_data()
        changes_made = data.get('changes_made', False)
        
        await state.clear()
        
        if changes_made:
            await message.answer(messages["ONBOARDING"]["PROFILE"]["EDITING_CANCELLED_WITH_CHANGES"], reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(messages["ONBOARDING"]["PROFILE"]["EDITING_CANCELLED_NO_CHANGES"], reply_markup=ReplyKeyboardRemove())
    
    elif message.text and message.text.lower() in ["нет", "no", "не нужно", "не хочу", "не хочу редактировать", "всё нормально", "всё хорошо"]:
        # User doesn't want to make any changes
        await state.clear()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["NO_CHANGES_NEEDED"], reply_markup=ReplyKeyboardRemove())
    
    else:
        # Invalid response
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["INVALID_EDIT_PROFILE_KB"], reply_markup=keyboard)


# Edit mode handlers - these return to edit menu after updating field
async def geocode_location(lat: float, lon: float) -> str:
    """Convert GPS coordinates to readable location name"""
    api_key = os.getenv("GEOCODING_API_KEY")
    
    print(f"DEBUG: geocode_location called with lat={lat}, lon={lon}")
    print(f"DEBUG: GEOCODING_API_KEY is {'set' if api_key else 'not set'}")
    
    if api_key:
        try:
            import httpx
            url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={api_key}&language=ru"
            print(f"DEBUG: Making geocoding request to: {url}")
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()
                print(f"DEBUG: Geocoding response status: {resp.status_code}")
                print(f"DEBUG: Geocoding response data: {data}")
                
                if data.get("results"):
                    result = data["results"][0]
                    
                    # Try to get the most relevant location name
                    # Priority: locality > administrative_area_level_2 > administrative_area_level_1 > country
                    location_name = None
                    
                    # Extract address components
                    address_components = result.get("address_components", [])
                    print(f"DEBUG: Address components: {address_components}")
                    
                    # Look for city/town (locality)
                    for component in address_components:
                        if "locality" in component.get("types", []):
                            location_name = component["long_name"]
                            print(f"DEBUG: Found locality: {location_name}")
                            break
                    
                    # If no locality, look for administrative area level 2 (county/region)
                    if not location_name:
                        for component in address_components:
                            if "administrative_area_level_2" in component.get("types", []):
                                location_name = component["long_name"]
                                print(f"DEBUG: Found administrative_area_level_2: {location_name}")
                                break
                    
                    # If still no location, look for administrative area level 1 (state/province)
                    if not location_name:
                        for component in address_components:
                            if "administrative_area_level_1" in component.get("types", []):
                                location_name = component["long_name"]
                                print(f"DEBUG: Found administrative_area_level_1: {location_name}")
                                break
                    
                    # If still no location, look for country
                    if not location_name:
                        for component in address_components:
                            if "country" in component.get("types", []):
                                location_name = component["long_name"]
                                print(f"DEBUG: Found country: {location_name}")
                                break
                    
                    # Fallback to formatted address if no specific location found
                    if not location_name:
                        location_name = result.get("formatted_address", f"{lat:.6f}, {lon:.6f}")
                        print(f"DEBUG: Using formatted_address: {location_name}")
                    
                    print(f"DEBUG: Final geocoded location: {location_name}")
                    return location_name
                else:
                    print(f"DEBUG: No results in geocoding response, falling back to coordinates")
                    return f"{lat:.6f}, {lon:.6f}"
        except Exception as e:
            print(f"DEBUG: Geocoding error: {e}")
            return f"{lat:.6f}, {lon:.6f}"
    else:
        print(f"DEBUG: No API key, falling back to coordinates")
        return f"{lat:.6f}, {lon:.6f}"


async def auto_save_single_field(message: Message, state: FSMContext, db_pool, field_name: str, new_value: str, openai_client=None):
    """Automatically save single field to database and update profile display"""
    try:
        print(f"DEBUG: auto_save_single_field called for field: {field_name}, value: '{new_value}'")
        user_id = message.from_user.id
        data = await state.get_data()
        
        # Update the specific field in session data
        data[field_name] = new_value
        await state.update_data(**data)
        print(f"DEBUG: Updated session data for field: {field_name}")
        
        # Map field names to database columns
        field_mapping = {
            "name": "intro_name",
            "location": "intro_location",
            "description": "intro_description",
            "linkedin": "intro_linkedin",
            "hobbies_drivers": "intro_hobbies_drivers",
            "skills": "intro_skills",
            "field_of_activity": "field_of_activity",
            "birthday": "intro_birthday",
            "photo_base64": "intro_image"
        }
        
        db_column = field_mapping.get(field_name)
        if not db_column:
            raise ValueError(f"Unknown field: {field_name}")
        
        # Handle special cases for different field types
        if field_name == "birthday":
            # Convert date to proper format or handle empty values
            if new_value:
                if hasattr(new_value, 'strftime'):
                    new_value = new_value.strftime("%Y-%m-%d")
                elif isinstance(new_value, str):
                    new_value = new_value
                else:
                    new_value = str(new_value)
            else:
                new_value = None  # Set to None for empty values
        
        # Update only the specific field in database
        print(f"DEBUG: Updating database field {db_column} for user {user_id}")
        print(f"DEBUG: SQL query: UPDATE public.users SET {db_column} = '{new_value}', updated_at = now() WHERE user_id = {user_id}")
        
        async with db_pool.acquire() as conn:
            if field_name == "birthday":
                # Special handling for birthday - convert to date or null
                if new_value:
                    from datetime import datetime
                    try:
                        birthday_date = datetime.strptime(new_value, "%Y-%m-%d").date()
                        result = await conn.execute(
                            f"UPDATE public.users SET {db_column} = $1, updated_at = now() WHERE user_id = $2",
                            birthday_date, user_id
                        )
                        print(f"DEBUG: Updated birthday to date: {birthday_date}, result: {result}")
                        
                        # Check if birthday is today and send greeting immediately
                        try:
                            from scheduler import get_scheduler_bot_and_pool
                            from birthday_greetings import check_birthday_for_user
                            bot, _ = get_scheduler_bot_and_pool()
                            # Run in background to avoid blocking
                            asyncio.create_task(check_birthday_for_user(bot, db_pool, user_id))
                        except Exception as e:
                            logger.warning(f"Could not check birthday immediately for user {user_id}: {e}")
                    except ValueError:
                        result = await conn.execute(
                            f"UPDATE public.users SET {db_column} = $1, updated_at = now() WHERE user_id = $2",
                            new_value, user_id
                        )
                        print(f"DEBUG: Updated birthday to string: {new_value}, result: {result}")
                else:
                    # Set birthday to NULL for empty values
                    result = await conn.execute(
                        f"UPDATE public.users SET {db_column} = $1, updated_at = now() WHERE user_id = $2",
                        None, user_id
                    )
                    print(f"DEBUG: Set birthday to NULL, result: {result}")
            else:
                result = await conn.execute(
                    f"UPDATE public.users SET {db_column} = $1, updated_at = now() WHERE user_id = $2",
                    new_value, user_id
                )
                print(f"DEBUG: Updated {db_column} to: '{new_value}', result: {result}")
        
        # After updating any field, check if user has required fields and set finishedonboarding=true if so
        # Required fields: name and description (at least 10 chars)
        async with db_pool.acquire() as conn:
            user_check = await conn.fetchrow(
                """
                SELECT 
                    intro_name,
                    intro_description,
                    finishedonboarding
                FROM public.users 
                WHERE user_id = $1
                """,
                user_id
            )
            if user_check:
                has_name = user_check['intro_name'] and len(user_check['intro_name'].strip()) > 0
                has_description = user_check['intro_description'] and len(user_check['intro_description'].strip()) >= 10
                
                # If user has required fields but finishedonboarding is false, set it to true
                if has_name and has_description and not user_check['finishedonboarding']:
                    await conn.execute(
                        "UPDATE public.users SET finishedonboarding = true, updated_at = now() WHERE user_id = $1",
                        user_id
                    )
                    print(f"DEBUG: Auto-enabled finishedonboarding=true for user {user_id} (has required fields: name and description)")
        
        # Vectorize description if it was updated
        # Update vector ONLY if description is meaningful (>=10 chars)
        # This ensures matching quality - users without real descriptions won't be matched
        if field_name == "description":
            try:
                description_vector = None
                
                # Only vectorize if description is meaningful (>=10 characters)
                # Users without meaningful descriptions will keep their existing vector (or default)
                # but won't be included in get_matchable_users (which requires intro_description >= 10)
                if new_value and len(new_value.strip()) >= 10:
                    # Try to vectorize the actual description - MUST succeed for matching to work
                    description_text = new_value.strip()
                    print(f"Vectorizing description for user {user_id}, length: {len(description_text)}")
                    description_vector = await vectorize_description(description_text, openai_client)
                    
                    if description_vector and len(description_vector) > 0:
                        async with db_pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE public.users SET vector_description = $1, updated_at = now() WHERE user_id = $2",
                                description_vector, user_id
                            )
                            print(f"✓ Successfully updated vector_description for user {user_id} with real description vector (dimension: {len(description_vector)})")
                    else:
                        print(f"❌ ERROR: Failed to vectorize description for user {user_id} - vector_description is None or empty")
                        # Try to create default vector as fallback so /my_matches still works
                        try:
                            from vectorization import create_default_vector
                            default_vector = await create_default_vector()
                            if default_vector:
                                async with db_pool.acquire() as conn:
                                    await conn.execute(
                                        "UPDATE public.users SET vector_description = $1, updated_at = now() WHERE user_id = $2",
                                        default_vector, user_id
                                    )
                                    print(f"Created default vector as fallback for user {user_id} (vectorization failed)")
                            else:
                                print(f"❌ CRITICAL: Failed to create default vector fallback for user {user_id}")
                        except Exception as fallback_error:
                            print(f"❌ CRITICAL: Exception creating default vector fallback for user {user_id}: {fallback_error}")
                            import traceback
                            traceback.print_exc()
                elif new_value is None or len(new_value.strip()) < 10:
                    # Description was cleared or is too short
                    # Keep existing vector but user won't be matched (get_matchable_users requires intro_description >= 10)
                    # If user had no vector before, create default one so /my_matches still works
                    async with db_pool.acquire() as conn:
                        existing_vector = await conn.fetchval(
                            "SELECT vector_description FROM users WHERE user_id = $1",
                            user_id
                        )
                        
                        if existing_vector is None:
                            # User has no vector - create default so /my_matches works
                            from vectorization import create_default_vector
                            default_vector = await create_default_vector()
                            if default_vector:
                                await conn.execute(
                                    "UPDATE public.users SET vector_description = $1, updated_at = now() WHERE user_id = $2",
                                    default_vector, user_id
                                )
                                print(f"Created default vector for user {user_id} (description too short/empty)")
                        else:
                            # Keep existing vector - user just won't be matched until they add description
                            print(f"User {user_id} description cleared/short - keeping existing vector, user won't be matched")
            except Exception as vector_error:
                print(f"❌ ERROR: Exception during vectorization for user {user_id}: {vector_error}")
                import traceback
                traceback.print_exc()
                # Try to create default vector as fallback
                try:
                    from vectorization import create_default_vector
                    default_vector = await create_default_vector()
                    if default_vector:
                        async with db_pool.acquire() as conn:
                            await conn.execute(
                                "UPDATE public.users SET vector_description = $1, updated_at = now() WHERE user_id = $2",
                                default_vector, user_id
                            )
                            print(f"Created default vector as exception fallback for user {user_id}")
                except Exception as fallback_error:
                    print(f"❌ CRITICAL: Failed to create default vector after exception for user {user_id}: {fallback_error}")
        
        # Update profile display
        print(f"DEBUG: Calling update_profile_display_after_edit for field: {field_name}")
        try:
            await update_profile_display_after_edit(message, state, db_pool, field_name, new_value)
            print(f"DEBUG: update_profile_display_after_edit completed successfully")
        except Exception as display_error:
            print(f"DEBUG: Error in update_profile_display_after_edit: {display_error}")
            raise display_error
        
        # Mark that changes were made in this editing session
        await state.update_data(changes_made=True)
        print(f"DEBUG: Marked changes_made=True and returning True")
        
        return True
    except Exception as e:
        print(f"Error auto-saving {field_name}: {e}")
        await message.answer(f"❌ Ошибка при сохранении {field_name}. Попробуйте еще раз.")
        return False


async def update_profile_display_after_edit(message: Message, state: FSMContext, db_pool, field_name: str, new_value: str):
    """Update profile display after field edit"""
    try:
        print(f"DEBUG: update_profile_display_after_edit called for field: {field_name}")
        user_id = message.from_user.id
        
        # Get updated user info from database
        user_info = await get_user_info(db_pool, user_id)
        print(f"DEBUG: Retrieved user_info: {user_info is not None}")
        
        if not user_info:
            print(f"DEBUG: No user_info found, returning")
            return
        
        # Send updated profile based on what was changed
        if field_name == "photo_base64" and new_value:
            # Send new photo
            try:
                import base64
                from aiogram.types import BufferedInputFile
                
                photo_data = base64.b64decode(new_value)
                input_file = BufferedInputFile(photo_data, filename="profile_photo.jpg")
                await message.answer_photo(input_file)
            except Exception as photo_error:
                print(f"Error sending updated photo: {photo_error}")
        
        # Send updated profile text
        print(f"DEBUG: Getting messages for user {user_id}")
        messages = get_messages_dynamic(user_id)
        print(f"DEBUG: Building profile text for user {user_id}")
        profile_text = build_profile_text(user_info, user_id, is_own_profile=True)
        print(f"DEBUG: Profile text built, length: {len(profile_text)}")
        
        # Show which field was updated
        field_names = {
            "name": "Имя",
            "location": "Местоположение", 
            "description": "Описание",
            "linkedin": "LinkedIn",
            "hobbies_drivers": "Хобби и мотивация",
            "skills": "Навыки",
            "field_of_activity": "Сфера деятельности",
            "birthday": "День рождения",
            "photo_base64": "Фото"
        }
        
        field_display_name = field_names.get(field_name, field_name)
        print(f"DEBUG: Sending confirmation message for field: {field_display_name}")
        await message.answer(f"✅ {field_display_name} обновлено и сохранено!")
        
        # Show updated profile
        print(f"DEBUG: Sending updated profile text")
        await message.answer(profile_text, parse_mode="HTML")
        print(f"DEBUG: Profile text sent successfully")
        
        # Show edit menu again
        print(f"DEBUG: Showing edit menu and setting state to editing_profile")
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)
        print(f"DEBUG: Successfully set state to ProfileStates.editing_profile")
        
    except Exception as e:
        print(f"Error updating profile display: {e}")
        # Fallback to simple confirmation
        await message.answer(f"✅ Поле обновлено и сохранено!")


async def handle_name_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle name input in edit mode - auto-saves and updates display"""
    print(f"DEBUG: handle_name_edit_mode called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование имени отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["NAME"]["INVALID"])
        return
    
    name = message.text.strip()
    print(f"DEBUG: Name after strip: '{name}'")
    
    # Validate name
    is_valid, error_message = InputValidator.validate_name(name)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное имя:")
        return
    
    # Sanitize input
    name = InputValidator.sanitize_input(name)
    print(f"DEBUG: Name after sanitize: '{name}'")
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    print(f"DEBUG: Calling auto_save_single_field with name: '{name}'")
    success = await auto_save_single_field(message, state, db_pool, "name", name, openai_client)
    print(f"DEBUG: auto_save_single_field returned: {success}")
    
    if not success:
        print(f"DEBUG: Failed to save name, showing fallback edit menu")
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_location_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle location input in edit mode - auto-saves and updates display"""
    print(f"DEBUG: handle_location_edit_mode called for user {message.from_user.id}")
    print(f"DEBUG: Message has location: {message.location is not None}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование местоположения отменено", reply_markup=keyboard)
        return
    
    location_text = None
    
    if message.location:
        # Use improved geocoding function
        lat = message.location.latitude
        lon = message.location.longitude
        print(f"DEBUG: Got location: lat={lat}, lon={lon}")
        location_text = await geocode_location(lat, lon)
        print(f"DEBUG: Geocoded location: '{location_text}'")
    elif message.text and message.text.lower() not in [get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["DONT_SHARE"].lower(), "пропустить", "skip"]:
        location_text = message.text.strip()
        print(f"DEBUG: Processing text location: '{location_text}'")
        
        # Validate text location
        is_valid, error_message = InputValidator.validate_location(location_text)
        if not is_valid:
            print(f"DEBUG: Location validation failed: {error_message}")
            await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное местоположение:")
            return
        
        # Sanitize input
        location_text = InputValidator.sanitize_input(location_text)
        print(f"DEBUG: Location after sanitize: '{location_text}'")

        # Normalize and enrich via geocoding if API is available
        api_key = os.getenv("GEOCODING_API_KEY")
        if api_key:
            try:
                import httpx
                params = {"address": location_text, "key": api_key}
                url = "https://maps.googleapis.com/maps/api/geocode/json"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url, params=params)
                    data = resp.json()
                    if data.get("results"):
                        # Use the first result's formatted address for normalization
                        location_text = data["results"][0]["formatted_address"]
                        print(f"DEBUG: Location after geocoding: '{location_text}'")
            except Exception as e:
                print(f"DEBUG: Geocoding failed: {e}")
                # Keep original text if geocoding fails
                pass
    elif message.text == get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["DONT_SHARE"]:
        # User doesn't want to share location - set empty location
        location_text = ""
        print(f"DEBUG: User chose not to share location")
    
    # location_text can be None (no input), empty string (don't share), or actual location
    # Only show error if user provided invalid input (None means no input at all)
    if location_text is None:
        print(f"DEBUG: Location text is None, showing invalid message")
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["LOCATION"]["INVALID"])
        return
    
    print(f"DEBUG: Final location_text: '{location_text}'")
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    print(f"DEBUG: Calling auto_save_single_field with location: '{location_text}'")
    success = await auto_save_single_field(message, state, db_pool, "location", location_text, openai_client)
    print(f"DEBUG: auto_save_single_field returned: {success}")
    
    if not success:
        print(f"DEBUG: Failed to save location, showing fallback edit menu")
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_description_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle description input in edit mode - auto-saves and updates display"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование описания отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["DESCRIPTION"]["INVALID"])
        return
    
    description = message.text.strip()
    
    # Validate description
    is_valid, error_message = InputValidator.validate_description(description)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректное описание:")
        return
    
    # Sanitize input
    description = InputValidator.sanitize_input(description)
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    success = await auto_save_single_field(message, state, db_pool, "description", description, openai_client)
    if not success:
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_linkedin_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle LinkedIn input in edit mode - returns to edit menu after saving"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование LinkedIn отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        # Allow empty LinkedIn - set to empty string
        linkedin = ""
    else:
        linkedin = message.text.strip()
    
    # Validate LinkedIn (now allows empty values and "Not available" alternatives)
    is_valid, error_message = InputValidator.validate_linkedin_url(linkedin)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректную ссылку на LinkedIn или 'Не указан':")
        return
    
    # Sanitize input
    linkedin = InputValidator.sanitize_input(linkedin)
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    success = await auto_save_single_field(message, state, db_pool, "linkedin", linkedin, openai_client)
    if not success:
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_hobbies_drivers_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle hobbies/drivers input in edit mode - returns to edit menu after saving"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование хобби и мотивации отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["HOBBIES_DRIVERS"]["INVALID"])
        return
    
    hobbies_drivers = message.text.strip()
    
    # Validate hobbies/drivers
    is_valid, error_message = InputValidator.validate_hobbies_drivers(hobbies_drivers)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректную информацию о хобби и мотивации:")
        return
    
    # Sanitize input
    hobbies_drivers = InputValidator.sanitize_input(hobbies_drivers)
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    success = await auto_save_single_field(message, state, db_pool, "hobbies_drivers", hobbies_drivers, openai_client)
    if not success:
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_skills_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle skills input in edit mode - returns to edit menu after saving"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование навыков отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["SKILLS"]["INVALID"])
        return
    
    skills = message.text.strip()
    
    # Validate skills
    is_valid, error_message = InputValidator.validate_skills(skills)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, введите корректную информацию о навыках:")
        return
    
    # Sanitize input
    skills = InputValidator.sanitize_input(skills)
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    success = await auto_save_single_field(message, state, db_pool, "skills", skills, openai_client)
    if not success:
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_field_of_activity_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle field of activity input in edit mode - returns to edit menu after saving"""
    print(f"DEBUG: handle_field_of_activity_edit_mode called for user {message.from_user.id}")
    print(f"DEBUG: Message text: '{message.text}'")
    
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование сферы деятельности отменено", reply_markup=keyboard)
        return
    
    if not message.text:
        # Allow empty field of activity - set to "Not specified"
        field_of_activity = "Not specified"
        print(f"DEBUG: Empty field of activity, setting to: '{field_of_activity}'")
    else:
        field_of_activity = message.text.strip()
        print(f"DEBUG: Field of activity after strip: '{field_of_activity}'")
        
        # Handle special values
        if field_of_activity.lower() in ["не указано", "not specified", "не указан", "не указана"]:
            field_of_activity = "Not specified"
            print(f"DEBUG: Normalized special value to: '{field_of_activity}'")
    
    # Sanitize input
    field_of_activity = InputValidator.sanitize_input(field_of_activity)
    print(f"DEBUG: Field of activity after sanitize: '{field_of_activity}'")
    
    # Auto-save and update display
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
    
    print(f"DEBUG: Calling auto_save_single_field with field_of_activity: '{field_of_activity}'")
    success = await auto_save_single_field(message, state, db_pool, "field_of_activity", field_of_activity, openai_client)
    print(f"DEBUG: auto_save_single_field returned: {success}")
    
    if success:
        print(f"DEBUG: Field of activity saved successfully, returning to edit menu")
        # auto_save_single_field already handles showing the updated profile and edit menu
        # and sets the state to ProfileStates.editing_profile
    else:
        print(f"DEBUG: Failed to save field of activity, showing fallback edit menu")
        # Show edit menu as fallback
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
        await state.set_state(ProfileStates.editing_profile)


async def handle_photo_edit_mode(message: Message, state: FSMContext, db_pool):
    """Handle photo input in edit mode - returns to edit menu after saving"""
    # Check for Exit button first
    if message.text and message.text.lower() in ["выход", "exit"]:
        await state.set_state(ProfileStates.editing_profile)
        messages = get_messages_dynamic(message.from_user.id)
        keyboard = get_edit_profile_keyboard()
        await message.answer("Редактирование фото отменено", reply_markup=keyboard)
        return
    
    if not message.photo:
        await message.answer(get_messages_dynamic(message.from_user.id)["ONBOARDING"]["PHOTO"]["INVALID"])
        return
    
    # Use the largest photo
    photo = max(message.photo, key=lambda p: p.file_size)
    photo_id = photo.file_id
    
    # Validate photo ID
    is_valid, error_message = InputValidator.validate_photo(photo_id)
    if not is_valid:
        await message.answer(f"❌ {error_message}\n\nПожалуйста, попробуйте отправить фото еще раз:")
        return
    
    # Download and convert photo to base64
    try:
        import base64
        import httpx
        
        # Get file info from Telegram
        async with httpx.AsyncClient() as client:
            file_response = await client.get(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_TOKEN')}/getFile",
                params={"file_id": photo_id}
            )
            file_data = file_response.json()
            
            if file_data.get("ok"):
                file_path = file_data["result"]["file_path"]
                image_url = f"https://api.telegram.org/file/bot{os.getenv('TELEGRAM_TOKEN')}/{file_path}"
                
                # Download the image
                image_response = await client.get(image_url)
                image_response.raise_for_status()
                image_data = image_response.content
                
                # Validate image before processing
                is_valid, validation_message = validate_image_size_and_format(image_data)
                if not is_valid:
                    await message.answer(f"❌ {validation_message}")
                    return
                
                # Show validation success
                await message.answer(validation_message)
                
                # Convert to base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Auto-save and update display
                success = await auto_save_single_field(message, state, db_pool, "photo_base64", image_base64)
                if not success:
                    # Show edit menu as fallback
                    messages = get_messages_dynamic(message.from_user.id)
                    keyboard = get_edit_profile_keyboard()
                    await message.answer(messages["ONBOARDING"]["PROFILE"]["ASK_ANY_CHANGES"], reply_markup=keyboard)
                    await state.set_state(ProfileStates.editing_profile)
            else:
                await message.answer("❌ Не удалось обработать фото. Пожалуйста, попробуйте еще раз.")
                
    except Exception as e:
        print(f"Error processing photo in edit mode: {e}")
        await message.answer("❌ Не удалось обработать фото. Пожалуйста, попробуйте еще раз.")
