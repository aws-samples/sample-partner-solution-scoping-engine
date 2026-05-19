// File: frontend/src/services/chatService.js
import apiClient from './apiClient.js';

/**
 * Fetches all chats for the user with optional filtering.
 * @param {string} stageFilter - Optional filter for chat stage
 * @param {number} limit - Maximum number of chats to return
 * @param {number} offset - Number of chats to skip
 * @returns {Promise<Object>} - A promise that resolves to the chats and total count
 */
export const getAllChats = async (stageFilter = null, limit = 20, offset = 0) => {
    let endpoint = `/chats?limit=${limit}&offset=${offset}`;

    if (stageFilter) {
        console.debug("DEBUG: chatService - Adding stage filter to URL:", stageFilter);
        endpoint += `&stage=${stageFilter}`;
    }
    
    // Include completed SA reviews when showing finalized solutions
    if (stageFilter === 'SOLUTION_FINALIZED') {
        endpoint += '&include_completed_sa_reviews=true';
    }

    console.debug("DEBUG: chatService - Final endpoint for getAllChats:", endpoint);

    try {
        const data = await apiClient.get(endpoint);
        console.debug("DEBUG: chatService - Response data:", data);
        return data;
    } catch (error) {
        console.error("DEBUG: chatService - Exception caught:", error);
        throw error;
    }
};

/**
 * Creates a new chat session on the backend.
 * 
 * @param {object} chatConfig 
 * @param {string} chatConfig.assistantId - The ID of the selected AI assistant.
 * @param {string} chatConfig.customerPersona - The ID of the selected customer persona.
 * @param {string} chatConfig.interactionMethod - The selected interaction method.
 * @returns {Promise<object>} - A promise that resolves to the chat session details.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const createChat = async (chatConfig) => {
    // Extract values from objects if needed
    const assistantPersona = typeof chatConfig.assistantId === 'object' && chatConfig.assistantId !== null
        ? chatConfig.assistantId.value
        : chatConfig.assistantId;

    const customerPersona = typeof chatConfig.customerPersona === 'object' && chatConfig.customerPersona !== null
        ? chatConfig.customerPersona.value
        : chatConfig.customerPersona;

    const payload = {
        assistant_persona: assistantPersona,
        customer_persona: customerPersona,
        interaction_method: chatConfig.interactionMethod,
        chat_name: chatConfig.chatName
    };

    try {
        const data = await apiClient.post('/chats', payload);
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Sends a message to the chat session and handles streaming response.
 * 
 * @param {string} chatId - The ID of the chat session.
 * @param {string} message - The message content to send.
 * @param {function} onStream - Callback function to handle streaming chunks.
 * @param {object} options - Additional options including files
 * @returns {Promise<void>} - A promise that resolves when the stream is complete.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const sendMessage = async (chatId, message, onStream, options = {}) => {
    const endpoint = `/chats/${chatId}/messages`;

    try {
        // Get CSRF token
        const { getCsrfToken } = await import('../utils/csrf');
        const csrfToken = await getCsrfToken();
        
        let requestBody;
        let headers = {
            'Accept': 'application/json',
            'X-CSRFToken': csrfToken
        };

        // Check if we have files to upload
        if (options.files && options.files.length > 0) {
            // Use FormData for file uploads
            const formData = new FormData();

            // Ensure message is properly set - use empty string if null/undefined
            const messageContent = message || '';
            formData.append('message', messageContent);
            formData.append('timestamp', new Date().toISOString());

            // Add other options (excluding files and fileClassifications)
            Object.keys(options).forEach(key => {
                if (key !== 'files' && key !== 'fileClassifications' && options[key] !== undefined && options[key] !== null) {
                    formData.append(key, String(options[key]));
                }
            });

            // Add file classifications if provided
            if (options.fileClassifications) {
                formData.append('fileClassifications', JSON.stringify(options.fileClassifications));
            }

            // Add files
            options.files.forEach((file) => {
                formData.append('files', file);
            });

            requestBody = formData;

            // Debug logging
            console.log('Sending FormData with message:', messageContent);
            console.log('Number of files:', options.files.length);

            // Don't set Content-Type header for FormData - let browser set it with boundary
        } else {
            // Use JSON for text-only messages
            requestBody = JSON.stringify({
                message: message,
                timestamp: new Date().toISOString(),
                ...options  // Include any additional options (useTools, intent, etc.)
            });
            headers['Content-Type'] = 'application/json';
        }

        // For streaming, we need to use the raw fetch with custom handling
        // since apiClient doesn't support streaming responses yet
        console.log('🔍 FETCH DEBUG - About to send request:');
        console.log('🔍 FETCH DEBUG - URL:', `${apiClient.baseURL}${endpoint}`);
        console.log('🔍 FETCH DEBUG - Headers:', headers);
        console.log('🔍 FETCH DEBUG - Body type:', requestBody instanceof FormData ? 'FormData' : typeof requestBody);
        if (requestBody instanceof FormData) {
            console.log('🔍 FETCH DEBUG - FormData entries:');
            for (let [key, value] of requestBody.entries()) {
                if (value instanceof File) {
                    console.log(`🔍 FETCH DEBUG -   ${key}: File(${value.name}, ${value.size} bytes, ${value.type})`);
                } else {
                    console.log(`🔍 FETCH DEBUG -   ${key}: ${typeof value === 'string' ? value.substring(0, 100) : value}`);
                }
            }
        }
        
        const response = await fetch(`${apiClient.baseURL}${endpoint}`, {
            method: 'POST',
            credentials: 'include',
            headers: headers,
            body: requestBody,
        });
        
        console.log('🔍 FETCH DEBUG - Response status:', response.status);
        console.log('🔍 FETCH DEBUG - Response headers:', Object.fromEntries(response.headers.entries()));

        // Handle 401 Unauthorized - redirect to login
        if (response.status === 401) {
            console.log('Authentication required - redirecting to login');
            window.location.href = '/api/auth?provider=oauth2';
            return null;
        }

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                // Ignore if response body is not JSON
            }
            const errorMessage = errorData?.error || response.statusText || `HTTP error! Status: ${response.status}`;
            throw new Error(`Failed to send message: ${errorMessage}`);
        }

        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedResponse = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // Decode the chunk and process it
            const chunk = decoder.decode(value, { stream: true });
            console.log(`chatService - Chunk response: ${chunk}`)
            try {
                // Try to parse as JSON first
                try {
                    const data = JSON.parse(chunk);
                    console.log(`chatService - data response: ${data}`)
                    if (data.type === 'content') {
                        console.log(`chatService - data.type content: ${data}`)
                        accumulatedResponse += data.content;
                        onStream(accumulatedResponse);
                    } else if (data.type === 'tool_result') {
                        console.log(`chatService - data.type tool_result: ${JSON.stringify(data)}`)
                        // For tool_result, pass the entire data object to onStream
                        onStream(JSON.stringify(data));
                    } else if (data.type === 'message_update') {
                        console.log(`chatService - data.type message_update: ${JSON.stringify(data)}`)
                        // For message_update, pass the entire data object to onStream
                        onStream(JSON.stringify(data));
                    } else if (data.type === 'info') {
                        console.log(`chatService - info message: ${data.content}`)
                        // Handle thinking/info messages - stream them like content
                        accumulatedResponse += data.content;
                        onStream(accumulatedResponse);
                    }
                } catch (e) {
                    // If it's not valid JSON, treat as plain text
                    console.log(`chatService - not valid JSON treat as plain text: ${chunk}`)
                    accumulatedResponse += chunk;
                    onStream(accumulatedResponse);
                }
            } catch (e) {
                // Continue even if there's an error processing a chunk
            }
        }

        console.log(`chatService - accumulatedResponse response: ${accumulatedResponse}`)
        return { response: accumulatedResponse };

    } catch (error) {
        throw error;
    }
};

/**
 * Fetches available personas from the backend.
 * @returns {Promise<object>} - A promise that resolves to the personas object with enabled/disabled states and descriptions.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const getPersonas = async () => {
    try {
        const data = await apiClient.get('/personas');
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Fetches chat session for a specific chat.
 * @param {string} chatId - The ID of the chat to fetch.
 * @returns {Promise<object>} - A promise that resolves to the complete chat session.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const getChatSession = async (chatId) => {
    try {
        console.debug(`Fetching chat session for chat ID: ${chatId}`);
        const data = await apiClient.get(`/chats/${chatId}`);
        console.debug(`Successfully fetched chat session for chat ID: ${chatId}`);
        console.debug(`Chat data structure:`, data);

        // Process the messages to ensure they're in the right format
        if (data && data.messages) {
            console.debug(`Chat has ${data.messages.length} messages`);

            // Log the structure of the first message to help with debugging
            if (data.messages.length > 0) {
                console.debug(`First message structure:`, data.messages[0]);
            }
        }

        return data;
    } catch (error) {
        console.error(`Error in getChatSession:`, error);
        throw error;
    }
};

// Add other chat-related API functions here later (e.g., sendMessage, getChatHistory, etc.) 
/**
 * Fetches the 5 most recent chats for the user.
 * @returns {Promise<Array>} - A promise that resolves to an array of recent chats.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const getRecentChats = async () => {
    try {
        console.debug('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Calling API endpoint: /chats/recent');
        const data = await apiClient.get('/chats/recent');
        console.debug('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Response data:', data);
        return data;
    } catch (error) {
        console.error('RECENT-CHATS-FEATURE-TROUBLESHOOTING: Exception caught:', error);
        throw error;
    }
};

/**
 * Fetches SA review chats for the user with optional limit.
 * @param {number} limit - Maximum number of reviews to return (default: 5)
 * @returns {Promise<Object>} - A promise that resolves to the user's SA review chats.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const getRecentSAReviews = async (limit = 5) => {
    try {
        const data = await apiClient.get(`/chats/reviews?limit=${limit}`);
        return data.chats || data; // Handle both old and new response formats
    } catch (error) {
        throw error;
    }
};

/**
 * Fetches all reviews assigned to the current SA user.
 * @returns {Promise<Object>} - A promise that resolves to the user's assigned reviews.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const getMyReviews = async () => {
    try {
        const data = await apiClient.get('/chats/reviews?limit=1000');
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Updates the name of a chat.
 * @param {string} chatId - The ID of the chat to update.
 * @param {string} newName - The new name for the chat.
 * @returns {Promise<object>} - A promise that resolves to the updated chat.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const updateChatName = async (chatId, newName) => {
    try {
        const data = await apiClient.put(`/chats/${chatId}/name`, {
            name: newName
        });
        return data;
    } catch (error) {
        throw error;
    }
};
/**
 * Deletes a chat session.
 * @param {string} chatId - The ID of the chat to delete.
 * @returns {Promise<object>} - A promise that resolves to the success response.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const deleteChat = async (chatId) => {
    try {
        const data = await apiClient.delete(`/chats/${chatId}`);
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Saves SA feedback for a chat.
 * @param {string} chatId - The ID of the chat to save feedback for.
 * @param {object} feedback - The feedback data.
 * @param {string} feedback.type - The type of feedback ('positive' or 'negative').
 * @param {string} feedback.detail - The feedback details.
 * @returns {Promise<object>} - A promise that resolves to the updated chat.
 * @throws {Error} - Throws an error if the network request fails.
 */
export const saveSAFeedback = async (chatId, feedback) => {
    try {
        const data = await apiClient.post(`/chats/${chatId}/sa-feedback`, {
            type: feedback.type,
            detail: feedback.detail
        });
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Saves feedback for a chat.
 * @param {string} chatId - The ID of the chat to save feedback for.
 * @param {object} feedback - The feedback data.
 * @param {string} feedback.type - The type of feedback ('positive' or 'negative').
 * @param {string} feedback.provider - The provider of the feedback ('User', 'Partner', or 'Customer').
 * @param {string} feedback.detail - The feedback details.
 * @returns {Promise<object>} - A promise that resolves to the updated chat.
/**
 * @throws {Error} - Throws an error if the network request fails.
 */
export const saveFeedback = async (chatId, feedback) => {
    try {
        const data = await apiClient.post(`/chats/${chatId}/feedback`, feedback);
        return data;
    } catch (error) {
        throw error;
    }
};

/**
 * Request SA review for a chat
 * @param {string} chatId - The chat ID to request review for
 * @returns {Promise<Object>} - A promise that resolves to the request result
 */
export const requestSAReview = async (chatId, comment = '') => {
    const response = await apiClient.post('/sa-review/request', {
        chat_id: chatId,
        comment: comment
    });
    return response;
};

export const cancelSAReview = async (chatId, comment = '') => {
    const response = await apiClient.post('/sa-review/cancel-request', {
        chat_id: chatId,
        comment: comment
    });
    return response;
};
