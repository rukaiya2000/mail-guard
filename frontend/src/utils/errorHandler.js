import { ERROR_MESSAGES } from './constants'
import { createLogger } from './logger'

const logger = createLogger('ErrorHandler')

export class APIError extends Error {
  constructor(message, status, response) {
    super(message)
    this.status = status
    this.response = response
    this.name = 'APIError'
  }
}

export const handleError = (error) => {
  logger.error('Error caught', { error: error.message })

  if (error.response) {
    const status = error.response.status
    const data = error.response.data

    switch (status) {
      case 400:
        return {
          message: data?.detail || ERROR_MESSAGES.BAD_REQUEST,
          type: 'error',
          status,
        }
      case 401:
        return {
          message: ERROR_MESSAGES.UNAUTHORIZED,
          type: 'error',
          status,
        }
      case 403:
        return {
          message: ERROR_MESSAGES.FORBIDDEN,
          type: 'error',
          status,
        }
      case 404:
        return {
          message: ERROR_MESSAGES.NOT_FOUND,
          type: 'error',
          status,
        }
      case 429:
        return {
          message: ERROR_MESSAGES.RATE_LIMITED,
          type: 'warning',
          status,
        }
      case 500:
      case 502:
      case 503:
        return {
          message: ERROR_MESSAGES.SERVER_ERROR,
          type: 'error',
          status,
        }
      default:
        return {
          message: data?.detail || `Error: ${status}`,
          type: 'error',
          status,
        }
    }
  } else if (error.request) {
    logger.error('No response from server', { error: error.message })
    return {
      message: ERROR_MESSAGES.NETWORK_ERROR,
      type: 'error',
      status: 0,
    }
  } else {
    logger.error('Error setting up request', { error: error.message })
    return {
      message: error.message || ERROR_MESSAGES.SERVER_ERROR,
      type: 'error',
      status: 0,
    }
  }
}

export const getErrorMessage = (error) => {
  const handled = handleError(error)
  return handled.message
}
