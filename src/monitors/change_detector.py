import logging
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChangeDetector:
    def __init__(self):
        logging.info("ChangeDetector initialized.")

    def _calculate_hash(self, content):
        """Calculates the SHA256 hash of the given content."""
        if content is None:
            return None
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def detect_change(self, old_content, new_content):
        """
        Compares old and new content to detect if a change has occurred.
        
        Args:
            old_content (str): The previously stored content.
            new_content (str): The newly scraped content.
            
        Returns:
            tuple: A tuple containing (is_changed, change_details).
                   is_changed (bool): True if content has changed, False otherwise.
                   change_details (dict): A dictionary with details about the change.
        """
        if old_content is None and new_content is None:
            logging.info("Both old and new content are None. No change detected.")
            return False, {"message": "No content available for comparison."}
        
        if old_content is None and new_content is not None:
            logging.info("New content found where old content was missing. Detected as a change.")
            return True, {"message": "New content added."}
            
        if old_content is not None and new_content is None:
            logging.info("Old content existed but new content is missing. Detected as a change.")
            return True, {"message": "Content removed."}

        old_hash = self._calculate_hash(old_content)
        new_hash = self._calculate_hash(new_content)

        if old_hash != new_hash:
            logging.info("Content hash mismatch. Change detected.")
            return True, {"message": "Content modified.", "old_hash": old_hash, "new_hash": new_hash}
        else:
            logging.info("Content hashes match. No change detected.")
            return False, {"message": "No significant change detected."}

if __name__ == '__main__':
    detector = ChangeDetector()

    # Test Case 1: No change
    print("\n--- Test Case 1: No change ---")
    content1 = "This is the original content."
    content2 = "This is the original content."
    changed, details = detector.detect_change(content1, content2)
    print(f"Changed: {changed}, Details: {details}")

    # Test Case 2: Content modified
    print("\n--- Test Case 2: Content modified ---")
    content3 = "This is the modified content."
    changed, details = detector.detect_change(content1, content3)
    print(f"Changed: {changed}, Details: {details}")

    # Test Case 3: New content added (old was None)
    print("\n--- Test Case 3: New content added ---")
    changed, details = detector.detect_change(None, content1)
    print(f"Changed: {changed}, Details: {details}")

    # Test Case 4: Content removed (new is None)
    print("\n--- Test Case 4: Content removed ---")
    changed, details = detector.detect_change(content1, None)
    print(f"Changed: {changed}, Details: {details}")

    # Test Case 5: Both None
    print("\n--- Test Case 5: Both None ---")
    changed, details = detector.detect_change(None, None)
    print(f"Changed: {changed}, Details: {details}")