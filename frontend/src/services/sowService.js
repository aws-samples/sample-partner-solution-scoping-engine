import apiClient from './apiClient.js';

/**
 * Service for SOW (Statement of Work) related API calls
 */

/**
 * Get SOWs for review with pagination
 * @param {number} limit - Number of SOWs to fetch
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Object>} Response with SOWs and pagination info
 */
export const getSOWsForReview = async (limit = 20, offset = 0) => {
    try {
        const data = await apiClient.get(`/sow-reviews?limit=${limit}&offset=${offset}`);
        return data;
    } catch (error) {
        console.error('Error fetching SOWs for review:', error);
        throw error;
    }
};

/**
 * Submit feedback for a SOW document
 * @param {string} chatId - Chat ID associated with the SOW
 * @param {Object} feedback - Feedback object with feedback_type and comments
 * @returns {Promise<Object>} Response from the server
 */
export const submitSOWFeedback = async (chatId, feedback) => {
    try {
        const data = await apiClient.post(`/sow-reviews/${chatId}/feedback`, feedback);
        return data;
    } catch (error) {
        console.error('Error submitting SOW feedback:', error);
        throw error;
    }
};

/**
 * Download SOW PDF document
 * @param {string} chatId - Chat ID associated with the SOW
 * @param {string} versionId - Optional version ID for specific version
 * @returns {Promise<void>} Downloads the file
 */
export const downloadSOW = async (chatId, versionId = null) => {
    try {
        let endpoint = `/sow-reviews/${chatId}/download`;
        if (versionId) {
            endpoint += `?version_id=${versionId}`;
        }

        // For file downloads, we need to use raw fetch since we need the response headers and blob
        const response = await fetch(`${apiClient.baseURL}${endpoint}`, {
            method: 'GET',
            credentials: 'include'
        });

        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            console.log('Authentication required - redirecting to login');
            window.location.href = '/api/auth?provider=oauth2';
            return null;
        }

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to download SOW');
        }

        // Get filename from response headers or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `SOW_${chatId}_${new Date().toISOString().split('T')[0]}.pdf`;
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }

        // Create blob and download
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
    } catch (error) {
        console.error('Error downloading SOW:', error);
        throw error;
    }
};

/**
 * Get SOW versions for a specific chat
 * @param {string} chatId - Chat ID associated with the SOW
 * @returns {Promise<Object>} Response with version information
 */
export const getSOWVersions = async (chatId) => {
    try {
        const data = await apiClient.get(`/sow-reviews/${chatId}/versions`);
        return data;
    } catch (error) {
        console.error('Error fetching SOW versions:', error);
        throw error;
    }
};

/**
 * Get SOW metadata for a specific chat
 * @param {string} chatId - Chat ID associated with the SOW
 * @returns {Promise<Object>} SOW metadata
 */
export const getSOWMetadata = async (chatId) => {
    try {
        const data = await apiClient.get(`/sow-reviews/${chatId}/metadata`);
        return data;
    } catch (error) {
        console.error('Error fetching SOW metadata:', error);
        throw error;
    }
};

/**
 * Get SOW review statistics
 * @returns {Promise<Object>} Review statistics
 */
export const getSOWReviewStats = async () => {
    try {
        const data = await apiClient.get('/sow-reviews/stats');
        return data;
    } catch (error) {
        console.error('Error fetching SOW review statistics:', error);
        throw error;
    }
};

/**
 * Get SOW configuration
 * @returns {Promise<Object>} SOW configuration
 */
export const getSOWConfig = async () => {
    try {
        const data = await apiClient.get('/sow-config');
        return data;
    } catch (error) {
        console.error('Error fetching SOW configuration:', error);
        throw error;
    }
};