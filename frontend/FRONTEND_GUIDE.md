# Frontend Development Guide

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── axios.js           # Axios configuration with interceptors
│   ├── components/
│   │   ├── Auth/
│   │   │   ├── Login.jsx
│   │   │   └── Register.jsx
│   │   ├── Classification/
│   │   │   ├── Classifier.jsx
│   │   │   └── BatchClassifier.jsx
│   │   ├── Analytics/
│   │   │   └── Analytics.jsx
│   │   ├── Common/
│   │   │   └── MetricCard.jsx
│   │   └── ...other components
│   ├── hooks/
│   │   └── useDebounce.js
│   ├── utils/
│   │   ├── constants.js       # API endpoints and constants
│   │   ├── logger.js          # Frontend logging
│   │   └── errorHandler.js    # Error handling utilities
│   ├── contexts/
│   │   ├── AuthContext.jsx
│   │   └── ThemeContext.jsx
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── package.json
```

## Getting Started

### Prerequisites
- Node.js 16+
- npm or yarn

### Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm run dev
```

Server runs on http://localhost:5173

### Build for Production
```bash
npm run build
npm run preview  # Test production build locally
```

## API Integration

### Using Axios
```javascript
import api from '@/api/axios'

// GET request
const response = await api.get('/api/v1/metrics')

// POST request
const response = await api.post('/api/v1/classify', {
  email_text: 'Email content...'
})

// With authentication (automatically added by interceptor)
const response = await api.get('/api/v1/me')
```

### Error Handling
```javascript
import { handleError } from '@/utils/errorHandler'

try {
  const response = await api.post('/api/v1/classify', data)
} catch (error) {
  const { message, type, status } = handleError(error)
  // Show toast notification with message
}
```

### API Endpoints
All API endpoints defined in `src/utils/constants.js`:
```javascript
import { API_ENDPOINTS } from '@/utils/constants'

api.post(API_ENDPOINTS.CLASSIFY, data)
api.get(API_ENDPOINTS.METRICS)
```

## State Management

### Authentication (AuthContext)
```javascript
import { useAuth } from '@/AuthContext'

const { user, token, login, logout, loading } = useAuth()

if (!user) {
  // Show login page
}
```

### Theme (ThemeContext)
```javascript
import { useTheme } from '@/ThemeContext'

const { isDark, setIsDark } = useTheme()

return (
  <div className={isDark ? 'dark bg-gray-900' : 'bg-gray-100'}>
    {/* Content */}
  </div>
)
```

## Components Best Practices

### Props Validation
```javascript
import PropTypes from 'prop-types'

function MyComponent({ title, value, isLoading }) {
  return <div>{title}: {value}</div>
}

MyComponent.propTypes = {
  title: PropTypes.string.required,
  value: PropTypes.number,
  isLoading: PropTypes.bool,
}

MyComponent.defaultProps = {
  isLoading: false,
}
```

### Hooks
```javascript
// Custom hook for API calls
const useClassification = () => {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const classify = async (emailText) => {
    setLoading(true)
    try {
      const response = await api.post(API_ENDPOINTS.CLASSIFY, {
        email_text: emailText
      })
      setResult(response.data)
      setError(null)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  return { result, loading, error, classify }
}
```

### Debouncing
```javascript
import useDebounce from '@/hooks/useDebounce'

function SearchEmails() {
  const [searchTerm, setSearchTerm] = useState('')
  const debouncedSearchTerm = useDebounce(searchTerm, 300)

  useEffect(() => {
    if (debouncedSearchTerm) {
      // Perform search
    }
  }, [debouncedSearchTerm])

  return (
    <input
      value={searchTerm}
      onChange={(e) => setSearchTerm(e.target.value)}
      placeholder="Search..."
    />
  )
}
```

## Styling

### Tailwind CSS Classes
- Use utility-first approach
- Dark mode support: `dark:bg-gray-900`
- Responsive design: `md:`, `lg:`, `xl:`

### Common Classes
```jsx
{/* Container */}
<div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

{/* Card */}
<div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">

{/* Button */}
<button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">

{/* Input */}
<input className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
```

## Testing

### Unit Tests
```bash
npm run test
```

### E2E Tests
```bash
npm run test:e2e
```

### Coverage
```bash
npm run test:coverage
```

## Performance Optimization

### Code Splitting
```javascript
import { lazy, Suspense } from 'react'

const Analytics = lazy(() => import('./components/Analytics'))

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <Analytics />
    </Suspense>
  )
}
```

### Memoization
```javascript
import { memo, useCallback } from 'react'

const MetricCard = memo(({ title, value }) => (
  <div>{title}: {value}</div>
))

function Dashboard() {
  const handleUpdate = useCallback(() => {
    // Update logic
  }, [])
}
```

### Image Optimization
```javascript
// Use optimized images
<img 
  src={optimizedImage} 
  alt="Description"
  loading="lazy"
  width={100}
  height={100}
/>
```

## Logging

### Logger Usage
```javascript
import { createLogger } from '@/utils/logger'

const logger = createLogger('Classifier')

logger.debug('Classifying email', { emailLength: email.length })
logger.info('Classification successful', { label: result.label })
logger.warn('Low confidence score', { confidence: 0.55 })
logger.error('Classification failed', { error: error.message })
```

## Environment Variables

Create `.env` file from `.env.example`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_GMAIL_INBOX=true
VITE_LOG_LEVEL=info
```

Access in code:
```javascript
const apiUrl = import.meta.env.VITE_API_BASE_URL
const isGmailEnabled = import.meta.env.VITE_ENABLE_GMAIL_INBOX === 'true'
```

## Common Issues

### CORS Errors
- Ensure backend ALLOWED_ORIGINS includes frontend URL
- Check API_BASE_URL in environment

### Authentication Issues
- Verify token is stored in localStorage
- Check token expiration
- Clear cache and retry

### Slow Performance
- Check network tab for slow API calls
- Profile with browser DevTools
- Enable React DevTools

## Deployment

### Build
```bash
npm run build
```

### Serve Production Build
```bash
npm run preview
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## Debugging

### Browser DevTools
- Use React DevTools extension
- Check Network tab for API calls
- View Application > Local Storage for auth tokens

### Console Logging
```javascript
logger.debug('Debug info', { data: value })
logger.error('Error occurred', { error })
```

### Remote Debugging
```javascript
// Connect to remote debugger
// node --inspect-brk node_modules/.bin/react-scripts start
```

## Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Axios Documentation](https://axios-http.com)
