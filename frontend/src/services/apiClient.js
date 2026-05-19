const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
import { getCsrfToken, clearCsrfToken } from '../utils/csrf';

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    // Add CSRF token for state-changing methods
    const needsCsrf = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method?.toUpperCase());
    let csrfToken = null;
    
    if (needsCsrf) {
      try {
        csrfToken = await getCsrfToken();
      } catch (error) {
        console.error('Failed to get CSRF token:', error);
      }
    }
    
    const defaultOptions = {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, defaultOptions);
      
      // Handle CSRF token errors
      if (response.status === 400) {
        const errorData = await this.parseErrorResponse(response);
        if (errorData.message?.includes('CSRF') || errorData.error?.includes('CSRF')) {
          console.log('CSRF token invalid - refreshing and retrying');
          clearCsrfToken();
          
          // Get new token and retry once
          try {
            const newToken = await getCsrfToken();
            defaultOptions.headers['X-CSRFToken'] = newToken;
            const retryResponse = await fetch(url, defaultOptions);
            
            if (retryResponse.ok) {
              const contentType = retryResponse.headers.get('content-type');
              if (contentType && contentType.includes('application/json')) {
                return await retryResponse.json();
              } else {
                const text = await retryResponse.text();
                return text || null;
              }
            }
          } catch (retryError) {
            console.error('CSRF retry failed:', retryError);
          }
        }
      }
      
      // Handle 401 Unauthorized - try to refresh auth status first
      if (response.status === 401) {
        console.log('Authentication required - checking if session can be refreshed');
        
        // Try to check auth status one more time in case it was a temporary issue
        try {
          const authResponse = await fetch(`${this.baseURL}/auth/auth-status`, {
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (authResponse.ok) {
            console.log('Session refresh successful - retrying original request');
            // Retry the original request once
            const retryResponse = await fetch(url, defaultOptions);
            if (retryResponse.ok) {
              const contentType = retryResponse.headers.get('content-type');
              if (contentType && contentType.includes('application/json')) {
                return await retryResponse.json();
              } else {
                const text = await retryResponse.text();
                return text || null;
              }
            }
          }
        } catch (refreshError) {
          console.log('Session refresh failed:', refreshError.message);
        }
        
        // If refresh failed or retry failed, redirect to login
        console.log('Redirecting to login');
        window.location.href = '/api/auth?provider=oauth2';
        return null;
      }

      if (!response.ok) {
        const errorData = await this.parseErrorResponse(response);
        throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        const text = await response.text();
        return text || null;
      }
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Network error: Unable to connect to the server');
      }
      throw error;
    }
  }

  async parseErrorResponse(response) {
    try {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        const text = await response.text();
        return { message: text || response.statusText };
      }
    } catch {
      return { message: response.statusText };
    }
  }

  // HTTP method helpers
  async get(endpoint, options = {}) {
    return this.request(endpoint, { method: 'GET', ...options });
  }

  async post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
      ...options,
    });
  }

  async put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
      ...options,
    });
  }

  async delete(endpoint, options = {}) {
    return this.request(endpoint, { method: 'DELETE', ...options });
  }

  // File upload helper
  async upload(endpoint, formData, options = {}) {
    // Get CSRF token for file uploads
    let csrfToken = null;
    try {
      csrfToken = await getCsrfToken();
    } catch (error) {
      console.error('Failed to get CSRF token for upload:', error);
    }
    
    const uploadOptions = {
      method: 'POST',
      body: formData,
      credentials: 'include',
      headers: {
        // Don't set Content-Type for FormData - let browser set it with boundary
        ...(csrfToken && { 'X-CSRFToken': csrfToken }),
        ...options.headers,
      },
    };

    // Remove Content-Type if it was set in default options
    delete uploadOptions.headers['Content-Type'];

    return this.request(endpoint, uploadOptions);
  }
}

// Export singleton instance
export default new ApiClient();