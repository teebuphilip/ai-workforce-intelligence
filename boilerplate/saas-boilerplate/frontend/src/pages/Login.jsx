import { useEffect } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useNavigate } from 'react-router-dom';
import useConfig from '../hooks/useConfig';

function Login() {
  const { loginWithRedirect, isAuthenticated } = useAuth0();
  const navigate = useNavigate();
  const config = useConfig();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      loginWithRedirect();
    }
  }, [isAuthenticated, loginWithRedirect, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Redirecting to login...</h2>
      </div>
    </div>
  );
}

export default Login;
