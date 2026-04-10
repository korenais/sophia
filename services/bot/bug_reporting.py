"""
Automatic Bug Reporting System

This module provides functionality to automatically create bug reports
for critical errors that affect system functionality. Bug reports are
saved to the feedbacks table and can be viewed in the admin interface.
"""

import logging
import traceback
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncpg
import hashlib

logger = logging.getLogger(__name__)

# System user ID for automatic bug reports (0 indicates system-generated)
SYSTEM_USER_ID = 0

class BugReportSystem:
    """Handles automatic bug report creation for critical errors"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self._recent_reports: Dict[str, datetime] = {}
        # Prevent duplicate reports within 24 hours
        self.duplicate_window_hours = 24
        # Only report critical and high severity issues
        self.min_severity = "high"  # "low", "medium", "high", "critical"
    
    def _is_critical_severity(self, severity: str) -> bool:
        """Check if severity is critical enough to report"""
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        min_level = severity_levels.get(self.min_severity, 3)
        error_level = severity_levels.get(severity.lower(), 0)
        return error_level >= min_level
    
    async def report_bug(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
        severity: str = "medium"
    ) -> Optional[int]:
        """
        Create a bug report for a critical error.
        Only reports high and critical severity issues to avoid spam.
        
        Args:
            error_type: Category of error (e.g., "birthday_greeting", "notification", "config")
            error_message: Human-readable error message
            context: Additional context information
            exception: Exception object if available
            severity: "low", "medium", "high", "critical"
        
        Returns:
            Bug report ID if created, None if duplicate was prevented or severity too low
        """
        try:
            # Filter by severity - only report critical/high
            if not self._is_critical_severity(severity):
                logger.debug(f"Skipping bug report (severity {severity} below threshold {self.min_severity}): {error_type}")
                return None
            
            # Check for duplicates
            report_hash = self._hash_report(error_type, error_message, context)
            is_duplicate = await self._is_duplicate(report_hash, error_type, error_message)
            if is_duplicate:
                logger.info(f"Skipping duplicate bug report (similar report exists in last 6-24h): {error_type} - {error_message[:50]}")
                return None
            
            # Create report content
            report_content = self._format_bug_report(
                error_type, error_message, context, exception, severity
            )
            
            # Save report to database
            report_id = await self._save_bug_report(report_content)
            
            # Track recent reports to prevent duplicates
            self._recent_reports[report_hash] = datetime.now()
            self._cleanup_old_reports()
            
            logger.info(f"Bug report created (ID: {report_id}): {error_type} - {error_message[:50]}")
            return report_id
            
        except Exception as e:
            logger.error(f"Failed to create bug report: {e}")
            return None
    
    def _format_bug_report(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]],
        exception: Optional[Exception],
        severity: str
    ) -> str:
        """Format bug report with professional structure"""
        
        severity_levels = {
            "critical": "CRITICAL",
            "high": "HIGH PRIORITY",
            "medium": "MEDIUM PRIORITY",
            "low": "LOW PRIORITY"
        }
        severity_display = severity_levels.get(severity.lower(), severity.upper())
        
        lines = []
        lines.append("AUTOMATED SYSTEM ERROR REPORT")
        lines.append("=" * 70)
        lines.append("")
        
        # Report Header
        lines.append("REPORT METADATA")
        lines.append("-" * 70)
        lines.append(f"Severity Level:     {severity_display}")
        lines.append(f"Error Category:     {error_type.replace('_', ' ').title()}")
        lines.append(f"Report Timestamp:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"Report Source:      Automated System Monitoring")
        lines.append("")
        
        # Error Summary
        lines.append("ERROR SUMMARY")
        lines.append("-" * 70)
        lines.append(error_message)
        lines.append("")
        
        # Context Information
        if context:
            lines.append("ERROR CONTEXT")
            lines.append("-" * 70)
            for key, value in sorted(context.items()):
                # Sanitize sensitive information
                if 'token' in key.lower() or 'password' in key.lower() or 'key' in key.lower():
                    value = "[REDACTED]"
                # Format key nicely
                formatted_key = key.replace('_', ' ').title()
                lines.append(f"  {formatted_key:.<25} {value}")
            lines.append("")
        
        # Exception Details
        if exception:
            lines.append("TECHNICAL DETAILS")
            lines.append("-" * 70)
            lines.append(f"Exception Type:     {type(exception).__name__}")
            lines.append(f"Exception Message:  {str(exception)}")
            lines.append("")
            lines.append("Stack Trace:")
            lines.append("-" * 70)
            traceback_lines = traceback.format_exc().split('\n')
            for line in traceback_lines:
                if line.strip():
                    lines.append(f"  {line}")
            lines.append("")
        
        # System Configuration Status
        lines.append("SYSTEM CONFIGURATION")
        lines.append("-" * 70)
        config_info = self._get_config_status()
        for key, value in sorted(config_info.items()):
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"  {formatted_key:.<25} {value}")
        lines.append("")
        
        # Recommended Actions
        lines.append("RECOMMENDED ACTIONS")
        lines.append("-" * 70)
        recommendations = self._get_recommendations(error_type, error_message, context)
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"  {i}. {rec}")
        else:
            lines.append("  Review error details and system configuration above.")
        lines.append("")
        
        lines.append("=" * 70)
        lines.append("This report was automatically generated by the system monitoring")
        lines.append("and error reporting service. For technical support, review the")
        lines.append("error details and recommended actions above.")
        
        return "\n".join(lines)
    
    def _get_config_status(self) -> Dict[str, str]:
        """Get configuration status (non-sensitive)"""
        config = {}
        
        # Check critical environment variables (show only if set/not set, not values)
        critical_vars = [
            "TELEGRAM_TOKEN",
            "DB_URL",
            "TELEGRAM_GROUP_ID",
            "BIRTHDAY_TOPIC_ID",
            "BIRTHDAYS",
            "FEEDBACK_USER_ID"
        ]
        
        for var in critical_vars:
            value = os.getenv(var)
            if var in ["TELEGRAM_TOKEN", "DB_URL"]:
                # Hide sensitive values
                config[var] = "SET" if value else "NOT SET"
            else:
                config[var] = str(value) if value else "NOT SET"
        
        return config
    
    def _get_recommendations(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> list:
        """Get recommendations based on error type"""
        recommendations = []
        
        if error_type == "birthday_greeting":
            if "BIRTHDAY_TOPIC_ID" in str(error_message) or "thread not found" in str(error_message).lower():
                recommendations.append("Verify BIRTHDAY_TOPIC_ID is correct and topic exists in the Telegram group")
                recommendations.append("Check if the bot has permission to send messages in the topic")
            if "TELEGRAM_GROUP_ID" in str(error_message):
                recommendations.append("Verify TELEGRAM_GROUP_ID is correct")
                recommendations.append("Ensure bot is a member of the group")
        
        elif error_type == "notification":
            if "thread not found" in str(error_message).lower():
                recommendations.append("Check if topic/thread ID exists in the Telegram group")
                recommendations.append("Verify bot has access to the specified topic")
        
        elif error_type == "config":
            recommendations.append("Review environment variables and ensure all required values are set")
            recommendations.append("Check configuration files and deployment settings")
        
        elif error_type == "database":
            recommendations.append("Check database connection and credentials")
            recommendations.append("Verify database is running and accessible")
            recommendations.append("Review database logs for additional errors")
        
        else:
            recommendations.append("Review error logs for additional context")
            recommendations.append("Check system status and recent changes")
        
        return recommendations
    
    def _hash_report(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create hash for duplicate detection"""
        # Create a hash from error type, message, and key context fields
        hash_data = f"{error_type}:{error_message}"
        if context:
            # Include relevant context fields but exclude timestamps
            relevant_fields = {k: v for k, v in context.items() if k not in ["timestamp", "time", "created_at"]}
            hash_data += f":{str(sorted(relevant_fields.items()))}"
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    async def _is_duplicate(self, report_hash: str, error_type: str, error_message: str) -> bool:
        """Check if a similar report was created recently and still exists in database.
        
        If a previous report was deleted (no longer exists in DB), a new one will be created.
        This allows tracking recurring issues even if previous reports were resolved/deleted.
        
        Note: For critical errors that persist (e.g., configuration errors),
        we allow creating new reports with reduced duplicate window (6 hours instead of 24)
        to track that the issue is still ongoing.
        """
        # Use shorter window for critical/configuration errors to allow tracking ongoing issues
        duplicate_window = 6 if error_type in ["config", "birthday_greeting"] else self.duplicate_window_hours
        
        # Check in-memory cache first
        if report_hash in self._recent_reports:
            last_time = self._recent_reports[report_hash]
            if datetime.now() - last_time < timedelta(hours=duplicate_window):
                # Cache says duplicate, but verify it still exists in DB
                # If report was deleted, allow creating new one
                if await self._verify_report_still_exists(report_hash, error_type, error_message, duplicate_window):
                    return True
                else:
                    # Report was deleted, remove from cache and allow new report
                    logger.info(f"Previous bug report was deleted, allowing new report creation")
                    del self._recent_reports[report_hash]
        
        # Check database for recent similar reports that still exist
        try:
            async with self.db_pool.acquire() as conn:
                # Check for reports from system user with similar content that still exist
                cutoff_time = datetime.now() - timedelta(hours=duplicate_window)
                rows = await conn.fetch(
                    """
                    SELECT id, text, created_at FROM public.feedbacks
                    WHERE user_id = $1
                    AND type = 'issue'
                    AND created_at > $2
                    ORDER BY created_at DESC
                    LIMIT 50
                    """,
                    SYSTEM_USER_ID,
                    cutoff_time
                )
                
                # Check if any recent report has similar content and still exists
                for row in rows:
                    # Extract error type and message from report text to compare
                    report_text = row['text']
                    # Check if error type and key parts of error message appear in recent report
                    if error_type in report_text and any(
                        keyword in report_text for keyword in error_message.split()[:5]  # First 5 words
                    ):
                        # Verify this specific report still exists (wasn't deleted)
                        report_exists = await self._check_report_exists_by_id(row['id'])
                        if report_exists:
                            return True
                        else:
                            logger.info(f"Similar bug report (ID: {row['id']}) was deleted, allowing new report")
        except Exception as e:
            logger.warning(f"Error checking for duplicate reports: {e}")
            # On error, don't block report creation
        
        return False
    
    async def _verify_report_still_exists(
        self, 
        report_hash: str, 
        error_type: str, 
        error_message: str,
        duplicate_window: int
    ) -> bool:
        """Verify that a previously reported bug still exists in database"""
        try:
            async with self.db_pool.acquire() as conn:
                cutoff_time = datetime.now() - timedelta(hours=duplicate_window)
                rows = await conn.fetch(
                    """
                    SELECT id, text FROM public.feedbacks
                    WHERE user_id = $1
                    AND type = 'issue'
                    AND created_at > $2
                    AND text LIKE $3
                    ORDER BY created_at DESC
                    LIMIT 10
                    """,
                    SYSTEM_USER_ID,
                    cutoff_time,
                    f"%{error_type}%"
                )
                
                for row in rows:
                    if any(keyword in row['text'] for keyword in error_message.split()[:5]):
                        return True
                return False
        except Exception as e:
            logger.warning(f"Error verifying report existence: {e}")
            return True  # On error, assume it exists to be safe
    
    async def _check_report_exists_by_id(self, report_id: int) -> bool:
        """Check if a specific bug report still exists in database"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM public.feedbacks WHERE id = $1",
                    report_id
                )
                return row is not None
        except Exception as e:
            logger.warning(f"Error checking report existence by ID {report_id}: {e}")
            return True  # On error, assume it exists to be safe
    
    async def _save_bug_report(self, report_content: str) -> int:
        """Save bug report to database"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO public.feedbacks(user_id, type, text)
                VALUES($1, $2, $3)
                RETURNING id
                """,
                SYSTEM_USER_ID,
                "issue",
                report_content
            )
            return row['id']
    
    def _cleanup_old_reports(self):
        """Clean up old entries from recent reports cache"""
        cutoff = datetime.now() - timedelta(hours=self.duplicate_window_hours * 2)
        self._recent_reports = {
            k: v for k, v in self._recent_reports.items() if v > cutoff
        }


# Global bug report system instance
_bug_reporter: Optional[BugReportSystem] = None

def init_bug_reporting(db_pool: asyncpg.Pool):
    """Initialize the global bug reporting system"""
    global _bug_reporter
    _bug_reporter = BugReportSystem(db_pool)
    logger.info("Bug reporting system initialized")

async def report_bug(
    error_type: str,
    error_message: str,
    context: Optional[Dict[str, Any]] = None,
    exception: Optional[Exception] = None,
    severity: str = "medium"
) -> Optional[int]:
    """Report a bug using the global system"""
    if _bug_reporter is None:
        logger.warning("Bug reporting system not initialized, cannot create bug report")
        return None
    
    return await _bug_reporter.report_bug(
        error_type, error_message, context, exception, severity
    )
