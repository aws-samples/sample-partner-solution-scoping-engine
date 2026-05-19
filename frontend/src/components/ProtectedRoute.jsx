import { Box, Spinner } from '@cloudscape-design/components';
import { useAuth } from '../hooks/useAuth';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  
  if (loading) {
    return (
      <Box textAlign="center" padding="xxl">
        <Spinner size="large" />
        <Box variant="p" color="text-status-info" margin={{ top: 's' }}>
          Loading...
        </Box>
      </Box>
    );
  }
  
  if (!isAuthenticated) {
    window.location.href = '/api/auth?provider=oauth2';
    return null;
  }
  
  return children;
};

export default ProtectedRoute;
