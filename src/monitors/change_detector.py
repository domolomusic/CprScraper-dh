import hashlib
import logging

logger = logging.getLogger(__name__)

class ChangeDetector:
    def __init__(self):
        logger.info("ChangeDetector initialized.")

    def _calculate_hash(self, content):
        """Calculates the SHA256 hash of the given content."""
        if not content:
            return None
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def detect_change(self, old_hash, new_content=None, new_hash_value=None):
        """
        Detects if there's a change by comparing hashes.
        
        Args:
            old_hash (str): The previously stored hash.
            new_content (str, optional): The new content to hash.
            new_hash_value (str, optional): The pre-calculated hash (e.g., for PDFs).
            
        Returns:
            tuple: (is_changed, change_details, final_new_hash)
        """
        final_new_hash = None

        if new_hash_value:
            final_new_hash = new_hash_value
            logger.debug(f"Using provided new hash: {final_new_hash[:10]}...")
        elif new_content is not None:
            final_new_hash = self._calculate_hash(new_content)
            logger.debug(f"Calculated new hash from content: {final_new_hash[:10]}...")
        else:
            logger.warning("No new content or new hash value provided for change detection.")
            return False, "No new content to compare.", old_hash # No change, keep old hash

        if not final_new_hash:
            logger.error("Could not determine a new hash for comparison.")
            return False, "Failed to generate new hash.", old_hash # No change, keep old hash

        if old_hash is None:
            logger.info("No previous hash found. This is the first scrape.")
            return True, "Initial content scraped.", final_new_hash
        
        if old_hash != final_new_hash:
            logger.info(f"Change detected! Old hash: {old_hash[:10]}..., New hash: {final_new_hash[:10]}...")
            return True, "Content hash changed.", final_new_hash
        else:
            logger.info("No change detected. Hashes match.")
            return False, "No change.", final_new_hash