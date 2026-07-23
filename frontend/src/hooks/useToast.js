import { useState, useCallback } from 'react';

export const useToast = () => {
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState('success');

  const triggerToast = useCallback((msg, type = 'success') => {
    setToastMessage(msg);
    setToastType(type);
  }, []);

  const clearToast = useCallback(() => {
    setToastMessage(null);
  }, []);

  return {
    toastMessage,
    toastType,
    triggerToast,
    clearToast
  };
};
