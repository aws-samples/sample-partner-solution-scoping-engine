/**
 * Format a date string into a human-readable format
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date string
 */
export const formatDate = (dateString) => {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    // Check if date is valid
    if (isNaN(date.getTime())) {
        return '';
    }
    
    // Format: "May 19, 2025, 3:30 PM"
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    });
};
