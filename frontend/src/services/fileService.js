import apiClient from './apiClient.js';

/**
 * Upload a file to the server
 * @param {string} chatId - The ID of the chat session
 * @param {File} file - The file to upload
 * @param {string} option - 'read' to have the AI read the file, 'save' to save to library
 * @returns {Promise} - Promise that resolves when the upload is complete
 */
export const uploadFile = async (chatId, file, option) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('option', option);

    try {
        const data = await apiClient.upload(`/chats/${chatId}/upload`, formData);
        return data;
    } catch (error) {
        console.error('Error uploading file:', error);
        throw error;
    }
};

/**
 * Get a list of documents for a chat session
 * @param {string} chatId - The ID of the chat session
 * @returns {Promise<Array>} - Promise that resolves to an array of documents
 */
export const getChatDocuments = async (chatId) => {
    try {
        const data = await apiClient.get(`/chats/${chatId}/documents`);
        return data;
    } catch (error) {
        console.error('Error getting chat documents:', error);
        throw error;
    }
};

/**
 * Get an S3 signed URL for a document
 * @param {string} chatId - The ID of the chat session
 * @param {string} documentName - The name of the document
 * @returns {Promise<Object>} - Promise that resolves to an object with url and uri
 */
export const getDocumentS3SignedUrl = async (chatId, documentName) => {
    try {
        const data = await apiClient.get(`/chats/${chatId}/documents/diagram/s3_signedurl/${documentName}`);
        return data;
    } catch (error) {
        console.error('Error getting S3 signed URL:', error);
        throw error;
    }
};

/**
 * Get a CloudFront signed URL for a document
 * @param {string} chatId - The ID of the chat session
 * @param {string} documentPath - The path of the document including prefix and extension
 * @param {string} versionId - Optional version ID of the document
 * @returns {Promise<Object>} - Promise that resolves to an object with url and uri
 */
export const getDocumentCFSignedUrl = async (chatId, documentPath, versionId = null) => {
    try {
        let endpoint = `/chats/${chatId}/documents/cf_signedurl/${documentPath}`;
        
        // Build query parameters
        const params = new URLSearchParams();
        if (versionId) {
            params.append('version_id', versionId);
        }
        // Add cache-busting parameter to ensure fresh signed URL on each request
        params.append('_t', Date.now().toString());
        
        endpoint += `?${params.toString()}`;
        
        console.debug(`WAFR_PREVIEW_DEBUG: Calling CF signed URL endpoint: ${endpoint}`);
        console.debug(`WAFR_PREVIEW_DEBUG: Request timestamp: ${new Date().toISOString()}`);
        
        const data = await apiClient.get(endpoint);
        
        console.debug(`WAFR_PREVIEW_DEBUG: CF signed URL response received:`, {
          hasUrl: !!data?.url,
          urlLength: data?.url?.length,
          uri: data?.uri
        });
        
        return data;
    } catch (error) {
        console.error('WAFR_PREVIEW_DEBUG: Error getting CloudFront signed URL:', error);
        console.error('WAFR_PREVIEW_DEBUG: Error details:', {
          name: error.name,
          message: error.message,
          stack: error.stack
        });
        throw error;
    }
};
/**
 * Fi
le Classification Service
 * Handles fetching file classification configuration from backend
 */
class FileClassificationService {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Get file classification configuration from backend
     * @returns {Promise<Object>} Classification configuration
     */
    async getClassificationConfig() {
        const cacheKey = 'classification_config';
        const cached = this.cache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }

        try {
            const response = await fetch('/api/file-classification/config', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to fetch classification config');
            }

            // Cache the result
            this.cache.set(cacheKey, {
                data: result.config,
                timestamp: Date.now()
            });

            return result.config;
        } catch (error) {
            console.error('Error fetching classification config:', error);
            throw new Error('Unable to load file classification configuration. Please check your connection and try again.');
        }
    }

    /**
     * Get assistant-specific classification configuration
     * @param {string} assistantPersona - The assistant persona
     * @returns {Promise<Object>} Assistant-specific configuration
     */
    async getAssistantConfig(assistantPersona) {
        const cacheKey = `assistant_config_${assistantPersona}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
            return cached.data;
        }

        try {
            const response = await fetch(`/api/file-classification/config/${assistantPersona}`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Failed to fetch assistant config');
            }

            // Cache the result
            this.cache.set(cacheKey, {
                data: result.config,
                timestamp: Date.now()
            });

            return result.config;
        } catch (error) {
            console.error('Error fetching assistant config:', error);
            throw new Error(`Unable to load configuration for ${assistantPersona}. Please check your connection and try again.`);
        }
    }

    /**
     * Clear cache (useful for testing or when config changes)
     */
    clearCache() {
        this.cache.clear();
    }
}

// Export singleton instance for file classification
export const fileClassificationService = new FileClassificationService();

/**
 * Get file classification configuration from backend
 * @returns {Promise<Object>} Classification configuration
 */
export const getFileClassificationConfig = async () => {
    return await fileClassificationService.getClassificationConfig();
};

/**
 * Get assistant-specific classification configuration
 * @param {string} assistantPersona - The assistant persona
 * @returns {Promise<Object>} Assistant-specific configuration
 */
export const getAssistantClassificationConfig = async (assistantPersona) => {
    return await fileClassificationService.getAssistantConfig(assistantPersona);
};

/**
 * Clear file classification cache
 */
export const clearFileClassificationCache = () => {
    fileClassificationService.clearCache();
};
/**

 * File Classification Utilities
 * Business logic for file classification and validation
 */
export class FileClassificationUtils {
    // Cache for configuration data
    static _configCache = null;
    static _assistantConfigCache = new Map();
    
    static async shouldUseClassification(assistantPersona) {
        try {
            const assistantConfig = await this.getAssistantConfig(assistantPersona);
            return assistantConfig.assistant_config?.enabled || false;
        } catch (error) {
            console.error('Error checking classification config:', error);
            return false;
        }
    }
    
    static async getAssistantConfig(assistantPersona) {
        try {
            // Check cache first
            if (this._assistantConfigCache.has(assistantPersona)) {
                return this._assistantConfigCache.get(assistantPersona);
            }
            
            const config = await fileClassificationService.getAssistantConfig(assistantPersona);
            
            // Cache the result
            this._assistantConfigCache.set(assistantPersona, config);
            
            return config;
        } catch (error) {
            console.error('Error getting assistant config:', error);
            throw error; // Re-throw to let caller handle
        }
    }
    
    static async getClassificationRules() {
        try {
            if (this._configCache) {
                return this._configCache;
            }
            
            const config = await fileClassificationService.getClassificationConfig();
            this._configCache = config;
            
            return config;
        } catch (error) {
            console.error('Error getting classification rules:', error);
            throw error; // Re-throw to let caller handle
        }
    }
    
    static async classifyFile(fileName) {
        try {
            const config = await this.getClassificationRules();
            const fileNameLower = fileName.toLowerCase();
            
            // Collect all matches with their priorities and confidence levels
            const matches = [];
            
            // Check each classification rule
            for (const [classificationType, rules] of Object.entries(config.rules || {})) {
                // Skip 'other' type in automatic classification
                if (classificationType === 'other') continue;
                
                // Check priority keywords first (highest confidence)
                if (rules.priority_keywords && rules.priority_keywords.some(keyword => fileNameLower.includes(keyword.toLowerCase()))) {
                    matches.push({
                        type: classificationType,
                        confidence: 'very_high',
                        method: 'priority_keyword',
                        priority: rules.priority || 999,
                        matchedKeyword: rules.priority_keywords.find(keyword => fileNameLower.includes(keyword.toLowerCase()))
                    });
                }
                // Check regular keywords (high confidence)
                else if (rules.keywords && rules.keywords.some(keyword => fileNameLower.includes(keyword.toLowerCase()))) {
                    matches.push({
                        type: classificationType,
                        confidence: 'high',
                        method: 'keyword',
                        priority: rules.priority || 999,
                        matchedKeyword: rules.keywords.find(keyword => fileNameLower.includes(keyword.toLowerCase()))
                    });
                }
                // Check extensions (medium confidence) - only if no keyword match
                else if (rules.extensions && rules.extensions.some(ext => fileNameLower.endsWith(ext.toLowerCase()))) {
                    matches.push({
                        type: classificationType,
                        confidence: 'medium',
                        method: 'extension',
                        priority: rules.priority || 999
                    });
                }
            }
            
            // If we have matches, return the one with highest priority and confidence
            if (matches.length > 0) {
                // Sort by confidence first (very_high > high > medium), then by priority (ascending)
                matches.sort((a, b) => {
                    const confidenceOrder = { 'very_high': 0, 'high': 1, 'medium': 2 };
                    const aConfidence = confidenceOrder[a.confidence] || 999;
                    const bConfidence = confidenceOrder[b.confidence] || 999;
                    
                    if (aConfidence !== bConfidence) {
                        return aConfidence - bConfidence;
                    }
                    
                    // If same confidence, sort by priority
                    if (a.priority !== b.priority) {
                        return a.priority - b.priority;
                    }
                    
                    return 0;
                });
                
                const bestMatch = matches[0];
                console.log(`File classification for "${fileName}": ${bestMatch.type} (${bestMatch.confidence}, priority: ${bestMatch.priority}, matched: ${bestMatch.matchedKeyword || 'extension'})`);
                
                return {
                    type: bestMatch.type,
                    confidence: bestMatch.confidence === 'very_high' ? 'high' : bestMatch.confidence, // Normalize for backward compatibility
                    method: bestMatch.method
                };
            }
            
            return {
                type: null,
                confidence: 'none',
                method: 'none'
            };
        } catch (error) {
            console.error('Error classifying file:', error);
            return {
                type: null,
                confidence: 'none',
                method: 'error'
            };
        }
    }
    
    static async validateFilesNeedClassification(files, assistantPersona) {
        try {
            const shouldUse = await this.shouldUseClassification(assistantPersona);
            if (!shouldUse) {
                return false;
            }
            
            const assistantConfig = await this.getAssistantConfig(assistantPersona);
            if (!assistantConfig.assistant_config?.show_classification_modal) {
                return false;
            }
            
            // Check each file asynchronously
            const classificationPromises = files.map(file => this.classifyFile(file.name));
            const classifications = await Promise.all(classificationPromises);
            
            return classifications.some((classification, index) => {
                const fileName = files[index].name;
                
                // Always need manual classification if confidence is none
                if (classification.confidence === 'none') {
                    console.log(`File "${fileName}" needs manual classification: no auto-classification found`);
                    return true;
                }
                
                // Need manual classification for medium confidence on required types
                if (classification.confidence === 'medium' && 
                    assistantConfig.assistant_config.required_types?.includes(classification.type)) {
                    console.log(`File "${fileName}" needs manual classification: medium confidence on required type`);
                    return true;
                }
                
                // For POC funding assistant, be extra careful with document classification
                if (assistantPersona === 'apn_funding_assistant') {
                    // If a document file doesn't have high confidence classification, ask for manual review
                    const isDocumentFile = fileName.toLowerCase().match(/\.(pdf|docx|doc)$/);
                    if (isDocumentFile && classification.confidence !== 'high') {
                        console.log(`File "${fileName}" needs manual classification: document file without high confidence in POC funding context`);
                        return true;
                    }
                }
                
                return false;
            });
        } catch (error) {
            console.error('Error validating files need classification:', error);
            return false;
        }
    }
    
    static async validateRequiredFiles(files, userClassifications, assistantPersona) {
        try {
            const assistantConfig = await this.getAssistantConfig(assistantPersona);
            if (!assistantConfig.assistant_config?.enabled) {
                return { valid: true, missing: [] };
            }
            
            const classifiedTypes = new Set();
            
            // Get types from automatic classification
            const classificationPromises = files.map(file => this.classifyFile(file.name));
            const autoClassifications = await Promise.all(classificationPromises);
            
            autoClassifications.forEach((autoClassification) => {
                if (autoClassification.type && autoClassification.confidence === 'high') {
                    classifiedTypes.add(autoClassification.type);
                }
            });
            
            // Get types from user classifications (override automatic)
            Object.entries(userClassifications || {}).forEach(([, type]) => {
                if (type && type !== '') {
                    classifiedTypes.add(type);
                }
            });
            
            // Check required types
            const requiredTypes = assistantConfig.assistant_config.required_types || [];
            const optionalTypes = assistantConfig.assistant_config.optional_types || [];
            const missingTypes = requiredTypes.filter(type => !classifiedTypes.has(type));
            
            return {
                valid: missingTypes.length === 0,
                missing: missingTypes,
                required: requiredTypes,
                optional: optionalTypes,
                classified: Array.from(classifiedTypes)
            };
        } catch (error) {
            console.error('Error validating required files:', error);
            return { valid: true, missing: [] };
        }
    }
    
    static async getClassificationOptions(assistantPersona) {
        try {
            const assistantConfig = await this.getAssistantConfig(assistantPersona);
            const config = assistantConfig.assistant_config;
            
            if (!config) {
                return [{
                    value: '',
                    label: 'Auto-detect',
                    description: 'Let the system automatically detect the file type'
                }];
            }
            
            // Get all available types for this assistant
            const allowedTypes = [...new Set([...(config.required_types || []), ...(config.optional_types || []), 'other'])];
            
            const options = [
                {
                    value: '',
                    label: 'Auto-detect',
                    description: 'Let the system automatically detect the file type'
                }
            ];
            
            allowedTypes.forEach(type => {
                const rule = assistantConfig.rules?.[type];
                if (rule) {
                    const isRequired = config.required_types?.includes(type);
                    options.push({
                        value: type,
                        label: isRequired ? `${rule.label} (Required)` : rule.label,
                        description: rule.description,
                        required: isRequired
                    });
                }
            });
            
            return options;
        } catch (error) {
            console.error('Error getting classification options:', error);
            return [{
                value: '',
                label: 'Auto-detect',
                description: 'Let the system automatically detect the file type'
            }];
        }
    }
    
    static async getSelectOptions(assistantPersona) {
        try {
            const options = await this.getClassificationOptions(assistantPersona);
            return options.map(option => ({
                label: option.label,
                value: option.value,
                description: option.description,
                tags: option.required ? ['Required'] : []
            }));
        } catch (error) {
            console.error('Error getting select options:', error);
            return [{
                label: 'Auto-detect',
                value: '',
                description: 'Let the system automatically detect the file type',
                tags: []
            }];
        }
    }
    
    static async getFileTypeIcon(classificationType) {
        try {
            const config = await this.getClassificationRules();
            const rule = config.rules?.[classificationType];
            return rule?.icon || 'file';
        } catch (error) {
            console.error('Error getting file type icon:', error);
            return 'file';
        }
    }
    
    static async isRequiredType(classificationType, assistantPersona) {
        try {
            const assistantConfig = await this.getAssistantConfig(assistantPersona);
            return assistantConfig.assistant_config?.required_types?.includes(classificationType) || false;
        } catch (error) {
            console.error('Error checking if required type:', error);
            return false;
        }
    }
    
    static async getAutoClassifications(files, assistantPersona) {
        try {
            const classifications = {};
            
            // Process files in parallel
            const classificationPromises = files.map(async (file) => {
                const classification = await this.classifyFile(file.name);
                // Include both high and medium confidence classifications
                if (classification.type && (classification.confidence === 'high' || classification.confidence === 'medium')) {
                    classifications[file.name] = classification.type;
                }
            });
            
            await Promise.all(classificationPromises);
            
            return classifications;
        } catch (error) {
            console.error('Error getting auto classifications:', error);
            return {};
        }
    }
    
    // Utility method to clear cache when needed
    static clearCache() {
        this._configCache = null;
        this._assistantConfigCache.clear();
        fileClassificationService.clearCache();
    }
}/**
 * Get 
allowed file extensions from backend configuration
 * @returns {Promise<Array>} Array of allowed file extensions
 */
export const getAllowedExtensions = async () => {
    try {
        const config = await fileClassificationService.getClassificationConfig();
        return config.allowed_extensions || [];
    } catch (error) {
        console.error('Error getting allowed extensions:', error);
        throw new Error('Unable to load allowed file extensions. Please check your connection and try again.');
    }
};

/**
 * Check if a file extension is allowed
 * @param {string} extension - File extension to check (with or without dot)
 * @returns {Promise<boolean>} True if extension is allowed
 */
export const isExtensionAllowed = async (extension) => {
    try {
        const allowedExtensions = await getAllowedExtensions();
        const ext = extension.toLowerCase().replace(/^\./, ''); // Remove leading dot
        
        // Check both with and without dots in the allowed list
        return allowedExtensions.includes(ext) || allowedExtensions.includes(`.${ext}`);
    } catch (error) {
        console.error('Error checking extension:', error);
        throw error; // Re-throw to let caller handle
    }
};

/**
 * Validate multiple files against allowed extensions
 * @param {FileList|Array} files - Files to validate
 * @returns {Promise<Object>} Validation result with valid/invalid files
 */
export const validateFileExtensions = async (files) => {
    try {
        const allowedExtensions = await getAllowedExtensions();
        const validFiles = [];
        const invalidFiles = [];
        
        for (const file of files) {
            const extension = file.name.split('.').pop().toLowerCase();
            const isAllowed = allowedExtensions.includes(extension) || allowedExtensions.includes(`.${extension}`);
            
            if (isAllowed) {
                validFiles.push(file);
            } else {
                invalidFiles.push({
                    file,
                    reason: `Extension .${extension} not allowed. Allowed: ${allowedExtensions.join(', ')}`
                });
            }
        }
        
        return {
            valid: invalidFiles.length === 0,
            validFiles,
            invalidFiles,
            allowedExtensions
        };
    } catch (error) {
        console.error('Error validating file extensions:', error);
        throw new Error('Unable to validate file extensions. Please check your connection and try again.');
    }
};