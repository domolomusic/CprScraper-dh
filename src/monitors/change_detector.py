import hashlib
import logging

logger = logging.getLogger(__name__)

class ChangeDetector:
    def __init__(self):
        logger.info("ChangeDetector initialized.")

    def _calculate_hash(self, content):
        """Calculates the SHA256 hash of the given content."""
        if content is None:
            return None
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def detect_change(self, old_hash, new_content):
        """
        Detects if there's a change by comparing the old hash with the hash of new content.
        Returns (is_changed, change_details, new_hash).
        """
        new_hash = self._calculate_hash(new_content)

        if old_hash is None:
            if new_hash:
                logger.info("Initial content hash recorded.")
                return False, "Initial content recorded.", new_hash
            else:
                logger.warning("No content fetched for initial hash calculation.")
                return False, "No content to record.", None
        
        if new_hash is None:
            logger.warning("New content could not be fetched for comparison.")
            return False, "New content not available for comparison.", old_hash # Keep old hash if new content failed

        if old_hash != new_hash:
            logger.info(f"Change detected! Old hash: {old_hash[:8]}..., New hash: {new_hash[:8]}...")
            return True, "Content hash changed.", new_hash
        else:
            logger.info("No change detected.")
            return False, "No change.", new_hash