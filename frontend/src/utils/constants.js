export const API_ENDPOINTS = {
  // Auth
  REGISTER: '/api/v1/register',
  LOGIN: '/api/v1/login',
  ME: '/api/v1/me',

  // Classification
  CLASSIFY: '/api/v1/classify',
  CLASSIFY_BATCH: '/api/v1/classify-batch',
  PARSE_EMAIL: '/api/v1/parse-email',

  // Analytics
  METRICS: '/api/v1/metrics',
  HISTORY: '/api/v1/history',
  ANALYTICS: '/api/v1/analytics',

  // Activity
  ACTIVITY: '/api/v1/activity',
  ADMIN_ACTIVITY: '/api/v1/admin/activity',

  // Export
  EXPORT_CSV: '/api/v1/export/csv',
  EXPORT_PDF: '/api/v1/export/pdf',

  // Gmail
  GMAIL_INBOX: '/api/v1/gmail/inbox',

  // Health
  HEALTH: '/health',
}

export const CLASSIFICATION_LABELS = {
  PHISHING: 'PHISHING',
  SPAM: 'SPAM',
  LEGITIMATE: 'LEGITIMATE',
}

export const LABEL_COLORS = {
  PHISHING: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  SPAM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  LEGITIMATE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
}

export const LABEL_EMOJIS = {
  PHISHING: '🚨',
  SPAM: '⚠️',
  LEGITIMATE: '✅',
}

export const ERROR_MESSAGES = {
  UNAUTHORIZED: 'Unauthorized. Please log in again.',
  FORBIDDEN: 'Access denied.',
  NOT_FOUND: 'Resource not found.',
  BAD_REQUEST: 'Invalid request.',
  SERVER_ERROR: 'Server error. Please try again later.',
  NETWORK_ERROR: 'Network error. Please check your connection.',
  RATE_LIMITED: 'Too many requests. Please wait a moment.',
}

export const TOAST_DURATIONS = {
  SHORT: 3000,
  MEDIUM: 5000,
  LONG: 8000,
}

export const PAGINATION = {
  DEFAULT_LIMIT: 50,
  MAX_BATCH_SIZE: 50,
}

export const TIMEOUTS = {
  API_REQUEST: 30000,
  DEBOUNCE_SEARCH: 300,
  DEBOUNCE_FILTER: 500,
}
