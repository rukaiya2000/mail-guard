const LOG_LEVELS = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
}

const LOG_LEVEL = import.meta.env.VITE_LOG_LEVEL || 'info'
const CURRENT_LEVEL = LOG_LEVELS[LOG_LEVEL.toUpperCase()] || LOG_LEVELS.INFO

class Logger {
  constructor(name) {
    this.name = name
  }

  _log(level, levelName, message, data) {
    if (LOG_LEVELS[levelName] < CURRENT_LEVEL) {
      return
    }

    const timestamp = new Date().toISOString()
    const prefix = `[${timestamp}] [${this.name}] [${levelName}]`

    const logData = {
      timestamp,
      logger: this.name,
      level: levelName,
      message,
      ...(data && { data }),
    }

    switch (levelName) {
      case 'ERROR':
        console.error(`${prefix}`, message, data || '')
        break
      case 'WARN':
        console.warn(`${prefix}`, message, data || '')
        break
      case 'INFO':
        console.info(`${prefix}`, message, data || '')
        break
      case 'DEBUG':
        console.debug(`${prefix}`, message, data || '')
        break
      default:
        console.log(`${prefix}`, message, data || '')
    }

    // Could send to external logging service here
    this._sendToLoggingService(logData)
  }

  debug(message, data) {
    this._log(LOG_LEVELS.DEBUG, 'DEBUG', message, data)
  }

  info(message, data) {
    this._log(LOG_LEVELS.INFO, 'INFO', message, data)
  }

  warn(message, data) {
    this._log(LOG_LEVELS.WARN, 'WARN', message, data)
  }

  error(message, data) {
    this._log(LOG_LEVELS.ERROR, 'ERROR', message, data)
  }

  _sendToLoggingService(logData) {
    // TODO: Integrate with logging service (Datadog, LogRocket, etc.)
    // Example:
    // if (window.logService) {
    //   window.logService.log(logData)
    // }
  }
}

// Create logger instances for different modules
export const createLogger = (name) => new Logger(name)

export default Logger
