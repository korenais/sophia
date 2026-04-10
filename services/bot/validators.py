import re
import logging
from typing import Optional, Tuple, List
from urllib.parse import urlparse
import unicodedata

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class InputValidator:
    """Validates user input for various fields"""
    
    @staticmethod
    def is_emoji(char: str) -> bool:
        """
        Check if a character is an emoji using Unicode categories
        """
        if not char:
            return False
        
        # Check Unicode categories for emojis
        category = unicodedata.category(char)
        
        # Emoji categories in Unicode
        emoji_categories = [
            'So',  # Symbol, other (includes many emojis)
        ]
        
        # Check if it's in emoji categories
        if category in emoji_categories:
            return True
        
        # Additional checks for specific emoji ranges
        code_point = ord(char)
        
        # Common emoji ranges
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map Symbols
            (0x1F1E0, 0x1F1FF),  # Regional indicator symbols
            (0x2600, 0x26FF),    # Miscellaneous Symbols
            (0x2700, 0x27BF),    # Dingbats
            (0xFE00, 0xFE0F),    # Variation Selectors
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            (0x1F018, 0x1F270),  # Various other emoji ranges
        ]
        
        for start, end in emoji_ranges:
            if start <= code_point <= end:
                return True
        
        return False
    
    @staticmethod
    def contains_only_valid_name_chars(text: str) -> bool:
        """
        Check if text contains only valid characters for names (letters, spaces, punctuation, emojis)
        """
        if not text:
            return False
        
        for char in text:
            # Allow letters (including Cyrillic)
            if char.isalpha():
                continue
            
            # Allow spaces, hyphens, dots, apostrophes
            if char in ' -.\'':
                continue
            
            # Allow emojis
            if InputValidator.is_emoji(char):
                continue
            
            # Allow zero-width joiner (for compound emojis)
            if ord(char) == 0x200D:  # Zero Width Joiner
                continue
            
            # If we get here, character is not allowed
            return False
        
        return True
    
    # LinkedIn URL patterns
    LINKEDIN_PATTERNS = [
        r'^https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_]+/?$',
        r'^https?://(?:www\.)?linkedin\.com/pub/[a-zA-Z0-9\-_]+/?$',
        r'^linkedin\.com/in/[a-zA-Z0-9\-_]+/?$',
        r'^linkedin\.com/pub/[a-zA-Z0-9\-_]+/?$',
    ]
    
    # Name validation
    MIN_NAME_LENGTH = 2
    MAX_NAME_LENGTH = 50
    
    # Description validation
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 500
    
    # Location validation
    MIN_LOCATION_LENGTH = 2
    MAX_LOCATION_LENGTH = 100
    
    @staticmethod
    def validate_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user name
        Returns: (is_valid, error_message)
        """
        if not name or not name.strip():
            return False, "Имя не может быть пустым"
        
        name = name.strip()
        
        if len(name) < InputValidator.MIN_NAME_LENGTH:
            return False, f"Имя должно содержать минимум {InputValidator.MIN_NAME_LENGTH} символа"
        
        if len(name) > InputValidator.MAX_NAME_LENGTH:
            return False, f"Имя не должно превышать {InputValidator.MAX_NAME_LENGTH} символов"
        
        if not InputValidator.contains_only_valid_name_chars(name):
            return False, "Имя может содержать только буквы, пробелы, дефисы, точки, апострофы и эмодзи"
        
        # Check for suspicious patterns
        if re.search(r'(.)\1{3,}', name):  # Repeated characters
            return False, "Имя содержит слишком много повторяющихся символов"
        
        if re.search(r'\b(admin|root|bot|test|user|guest)\b', name.lower()):
            return False, "Имя содержит запрещенные слова"
        
        return True, None
    
    @staticmethod
    def validate_linkedin_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate LinkedIn URL - allows empty values and "Не указан" alternatives
        Returns: (is_valid, error_message)
        """
        if not url or not url.strip():
            return True, None  # Allow empty values
        
        url = url.strip()
        
        # Allow common "not available" alternatives
        not_available_patterns = [
            r'^(none|n/a|na|not available|недоступен|не указан|отсутствует|пусто)$',
            r'^[-_\.]+$',  # Just dashes, underscores, dots
        ]
        
        for pattern in not_available_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True, None
        
        # Check if it matches any valid LinkedIn pattern
        for pattern in InputValidator.LINKEDIN_PATTERNS:
            if re.match(pattern, url, re.IGNORECASE):
                return True, None
        
        # Try to parse and validate the URL structure
        try:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            
            if parsed.netloc.lower() not in ['linkedin.com', 'www.linkedin.com']:
                return False, "URL должен быть с LinkedIn или выберите 'Не указан'"
            
            if not parsed.path.startswith(('/in/', '/pub/')):
                return False, "URL LinkedIn должен быть профилем (/in/ или /pub/) или выберите 'Не указан'"
            
            # Extract username from path
            username = parsed.path.split('/')[-1]
            if not username or not re.match(r'^[a-zA-Z0-9\-_]+$', username):
                return False, "Неверный идентификатор профиля LinkedIn"
            
            return True, None
            
        except Exception as e:
            logger.warning(f"Error parsing LinkedIn URL: {e}")
            return False, "Неверный формат URL"
    
    @staticmethod
    def validate_description(description: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user description
        Returns: (is_valid, error_message)
        """
        if not description or not description.strip():
            return False, "Описание не может быть пустым"
        
        description = description.strip()
        
        if len(description) < InputValidator.MIN_DESCRIPTION_LENGTH:
            return False, f"Описание должно содержать минимум {InputValidator.MIN_DESCRIPTION_LENGTH} символов"
        
        if len(description) > InputValidator.MAX_DESCRIPTION_LENGTH:
            return False, f"Описание не должно превышать {InputValidator.MAX_DESCRIPTION_LENGTH} символов"
        
        # Check for suspicious content
        suspicious_patterns = [
            r'https?://',  # URLs
            r'@\w+',       # Mentions
            r'#\w+',       # Hashtags
            r'\b\d{10,}\b', # Long numbers (phone numbers, etc.)
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return False, "Описание содержит запрещенный контент (URL, упоминания, хештеги или номера телефонов)"
        
        # Check for spam-like patterns
        if re.search(r'(.)\1{4,}', description):  # Repeated characters
            return False, "Описание содержит слишком много повторяющихся символов"
        
        # Check word count (minimum meaningful content)
        words = description.split()
        if len(words) < 3:
            return False, "Описание должно содержать минимум 3 слова"
        
        return True, None
    
    @staticmethod
    def validate_location(location: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user location
        Returns: (is_valid, error_message)
        """
        if not location or not location.strip():
            return False, "Местоположение не может быть пустым"
        
        location = location.strip()
        
        if len(location) < InputValidator.MIN_LOCATION_LENGTH:
            return False, f"Местоположение должно содержать минимум {InputValidator.MIN_LOCATION_LENGTH} символа"
        
        if len(location) > InputValidator.MAX_LOCATION_LENGTH:
            return False, f"Местоположение не должно превышать {InputValidator.MAX_LOCATION_LENGTH} символов"
        
        # Allow Unicode letters by using \w with UNICODE flag, but disallow digits and underscores explicitly
        # Permit spaces, commas, hyphens, parentheses, dots and apostrophes
        if not re.match(r'^[\w\s,\-\(\)\.\']+$', location, re.UNICODE):
            return False, "Местоположение содержит неверные символы"
        if re.search(r'[\d_]', location):
            return False, "Местоположение не должно содержать цифры или подчеркивания"
        
        # Check for suspicious patterns
        if re.search(r'(.)\1{3,}', location):  # Repeated characters
            return False, "Местоположение содержит слишком много повторяющихся символов"
        
        return True, None
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        Sanitize user input by removing potentially harmful content
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text
    
    @staticmethod
    def validate_hobbies_drivers(hobbies_drivers: str) -> Tuple[bool, Optional[str]]:
        """
        Validate hobbies and drivers text
        Returns: (is_valid, error_message)
        """
        if not hobbies_drivers or not hobbies_drivers.strip():
            return False, "Информация о хобби и мотивации не может быть пустой"
        
        hobbies_drivers = hobbies_drivers.strip()
        
        if len(hobbies_drivers) < 10:
            return False, "Информация о хобби и мотивации должна содержать минимум 10 символов"
        
        if len(hobbies_drivers) > 300:
            return False, "Информация о хобби и мотивации не должна превышать 300 символов"
        
        # Check word count (minimum meaningful content)
        # Allow shorter responses if they contain meaningful content
        words = hobbies_drivers.split()
        if len(words) < 2:
            return False, "Информация о хобби и мотивации должна содержать минимум 2 слова"
        
        return True, None
    
    @staticmethod
    def validate_skills(skills: str) -> Tuple[bool, Optional[str]]:
        """
        Validate skills text
        Returns: (is_valid, error_message)
        """
        if not skills or not skills.strip():
            return False, "Информация о навыках не может быть пустой"
        
        skills = skills.strip()
        
        if len(skills) < 10:
            return False, "Информация о навыках должна содержать минимум 10 символов"
        
        if len(skills) > 300:
            return False, "Информация о навыках не должна превышать 300 символов"
        
        # Check word count (minimum meaningful content)
        # Allow shorter responses if they contain meaningful content
        words = skills.split()
        if len(words) < 2:
            return False, "Информация о навыках должна содержать минимум 2 слова"
        
        return True, None
    
    @staticmethod
    def validate_photo(photo_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate photo ID (basic validation)
        Returns: (is_valid, error_message)
        """
        if not photo_id or not photo_id.strip():
            return False, "ID фото не может быть пустым"
        
        photo_id = photo_id.strip()
        
        # Basic validation for Telegram file IDs
        if not re.match(r'^[A-Za-z0-9_\-]+$', photo_id):
            return False, "Неверный формат ID фото"
        
        if len(photo_id) < 10 or len(photo_id) > 200:
            return False, "ID фото имеет неверную длину"
        
        return True, None

class UsernameValidator:
    """Validates and manages usernames"""
    
    @staticmethod
    def is_valid_telegram_username(username: str) -> bool:
        """
        Check if a Telegram username is valid
        """
        if not username:
            return False
        
        # Remove @ if present
        username = username.lstrip('@')
        
        # Telegram username rules
        if len(username) < 5 or len(username) > 32:
            return False
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        
        if username.startswith('_') or username.endswith('_'):
            return False
        
        if '__' in username:
            return False
        
        return True
    
    @staticmethod
    def normalize_username(username: str) -> str:
        """
        Normalize username by removing @ and converting to lowercase
        """
        if not username:
            return ""
        
        return username.lstrip('@').lower()

class ContentFilter:
    """Filters potentially inappropriate content"""
    
    # List of restricted words (basic example)
    RESTRICTED_WORDS = [
        'spam', 'scam', 'fake', 'bot', 'admin', 'root',
        'hack', 'crack', 'illegal', 'fraud'
    ]
    
    @staticmethod
    def contains_restricted_content(text: str) -> bool:
        """
        Check if text contains restricted content
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        for word in ContentFilter.RESTRICTED_WORDS:
            if word in text_lower:
                return True
        
        return False
    
    @staticmethod
    def filter_content(text: str) -> str:
        """
        Filter out restricted content from text
        """
        if not text:
            return ""
        
        filtered_text = text
        for word in ContentFilter.RESTRICTED_WORDS:
            # Replace with asterisks
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            filtered_text = pattern.sub('*' * len(word), filtered_text)
        
        return filtered_text


