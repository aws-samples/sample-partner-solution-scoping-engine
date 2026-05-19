// Configuration settings for the frontend application

// API base URL from environment variables
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

// Other configuration settings
export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
export const ALLOWED_FILE_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/csv',
    'text/markdown',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png',
    'image/jpeg',
    'image/jpg'
];

// File type display names
export const FILE_TYPE_NAMES = {
    'application/pdf': 'PDF',
    'application/msword': 'Word Document',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'Word Document',
    'text/plain': 'Text File',
    'text/csv': 'CSV File',
    'text/markdown': 'Markdown File',
    'application/vnd.ms-excel': 'Excel Spreadsheet',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'Excel Spreadsheet',
    'application/vnd.ms-powerpoint': 'PowerPoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PowerPoint',
    'image/png': 'PNG Image',
    'image/jpeg': 'JPEG Image',
    'image/jpg': 'JPEG Image'
};
