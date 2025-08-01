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
        # Ensure content is bytes for hashing
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def detect_change(self, old_hash, new_content=None, new_hash_value=None):
        """
        Detects if there's a change by comparing the old hash with the hash of new content
        or a provided new hash value.
        Returns (is_changed, change_details, final_new_hash).
        """
        final_new_hash = None

        if new_hash_value:
            final_new_hash = new_hash_value
            logger.debug(f"Using provided new hash value: {final_new_hash[:8]}...")
        elif new_content is not None:
            final_new_hash = self._calculate_hash(new_content)
            logger.debug(f"Calculated new hash from content: {final_new_hash[:8]}...")
        else:
            logger.warning("Neither new_content nor new_hash_value provided for change detection.")
            return False, "No new content or hash to compare.", old_hash # Keep old hash if no new data

        if old_hash is None:
            if final_new_hash:
                logger.info("Initial content hash recorded.")
                return False, "Initial content recorded.", final_new_hash
            else:
                logger.warning("No content/hash fetched for initial recording.")
                return False, "No content to record.", None
        
        if final_new_hash is None:
            logger.warning("New content/hash could not be fetched for comparison.")
            return False, "New content/hash not available for comparison.", old_hash # Keep old hash if new data failed

        if old_hash != final_new_hash:
            logger.info(f"Change detected! Old hash: {old_hash[:8]}..., New hash: {final_new_hash[:8]}...")
            return True, "Content hash changed.", final_new_hash
        else:
            logger.info("No change detected.")
            return False, "No change.", final_new_hash