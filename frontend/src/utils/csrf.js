// CSRF Token Manager
let csrfToken = null;

/**
 * Get CSRF token from backend
 * @returns {Promise<string>} CSRF token
 */
export async function getCsrfToken() {
  if (csrfToken) {
    return csrfToken;
  }
  
  try {
    const response = await fetch('/api/csrf-token', {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Failed to fetch CSRF token');
    }
    
    const data = await response.json();
    csrfToken = data.csrf_token;
    return csrfToken;
  } catch (error) {
    console.error('Failed to get CSRF token:', error);
    throw error;
  }
}

/**
 * Clear cached CSRF token (call when token expires or on logout)
 */
export function clearCsrfToken() {
  csrfToken = null;
}
