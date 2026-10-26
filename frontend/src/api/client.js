const BASE_URL = import.meta.env.VITE_API_URL !== undefined 
  ? import.meta.env.VITE_API_URL 
  : (import.meta.env.DEV ? 'http://localhost:8000' : '');

let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(cb) {
  refreshSubscribers.push(cb);
}

function onRefreshed(success) {
  refreshSubscribers.forEach((cb) => cb(success));
  refreshSubscribers = [];
}

/**
 * Custom fetch wrapper that automatically includes cookies and handles automatic token refreshing.
 */
export async function apiFetch(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`;
  
  const fetchOptions = {
    ...options,
    credentials: 'include', // Ensure HTTP-only cookies are included
  };

  let response = await fetch(fullUrl, fetchOptions);

  // If unauthorized (token expired), attempt to refresh automatically
  if (response.status === 401 && !url.includes('/api/users/login') && !url.includes('/api/users/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      try {
        const refreshRes = await fetch(`${BASE_URL}/api/users/refresh`, {
          method: 'POST',
          credentials: 'include',
        });

        if (refreshRes.ok) {
          isRefreshing = false;
          onRefreshed(true);
          // Retry original request
          return fetch(fullUrl, fetchOptions);
        } else {
          isRefreshing = false;
          onRefreshed(false);
          // Refresh token expired or invalid
          window.dispatchEvent(new Event('auth:unauthorized'));
          return response;
        }
      } catch (err) {
        isRefreshing = false;
        onRefreshed(false);
        window.dispatchEvent(new Event('auth:unauthorized'));
        return response;
      }
    } else {
      // Wait for ongoing refresh to complete, then retry
      return new Promise((resolve) => {
        subscribeTokenRefresh((success) => {
          if (success) {
            resolve(fetch(fullUrl, fetchOptions));
          } else {
            resolve(response);
          }
        });
      });
    }
  }

  return response;
}

/**
 * Helper to check current authentication status with backend
 */
export async function checkAuthStatus() {
  try {
    const res = await apiFetch('/api/users/me');
    if (res.ok) {
      const data = await res.json();
      return data;
    }
    return { authenticated: false };
  } catch (err) {
    return { authenticated: false };
  }
}
