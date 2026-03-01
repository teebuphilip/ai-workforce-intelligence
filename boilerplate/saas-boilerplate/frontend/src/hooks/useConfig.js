import { useState, useEffect } from 'react';
import config from '../config/business_config.json';

function useConfig() {
  const [businessConfig, setBusinessConfig] = useState(config);

  // Could fetch from API for dynamic updates
  useEffect(() => {
    // For now, just use local config
    // In production, optionally fetch from API:
    // fetch('/api/config').then(r => r.json()).then(setBusinessConfig);
  }, []);

  return businessConfig;
}

export default useConfig;
