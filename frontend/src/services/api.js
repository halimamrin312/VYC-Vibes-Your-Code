const DEFAULT_PROD_API_BASE_URL = 'https://swarm-ai-backend-production.up.railway.app';

const normalizeBaseUrl = (value) => {
  if (!value) return '';
  return value.replace(/\/+$/, '');
};

const getRailwayBackendUrl = () => {
  const publicDomain = import.meta.env.RAILWAY_PUBLIC_DOMAIN;
  const serviceName = import.meta.env.RAILWAY_SERVICE_NAME;

  if (publicDomain && serviceName && serviceName.includes('backend')) {
    return `https://${publicDomain}`;
  }

  if (publicDomain && publicDomain.includes('backend')) {
    return `https://${publicDomain}`;
  }

  return '';
};

export const getApiBaseUrl = () => {
  const configuredBaseUrl = normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL || '');

  if (configuredBaseUrl) {
    return configuredBaseUrl;
  }

  const railwayBackendUrl = getRailwayBackendUrl();
  if (railwayBackendUrl) {
    return railwayBackendUrl;
  }

  if (import.meta.env.DEV) {
    return '/api';
  }

  return DEFAULT_PROD_API_BASE_URL;
};

export const apiFetch = (path, options = {}) => {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  return fetch(url, options);
};
