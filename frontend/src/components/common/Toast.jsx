import React, { useEffect } from 'react';

export const Toast = ({ message, type = 'success', onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  const icons = {
    success: 'check_circle',
    warning: 'warning',
    error: 'error',
    info: 'info'
  };

  const bgColors = {
    success: 'bg-[#E0F2E9] border-[#A5D6A7] text-green-900',
    warning: 'bg-orange-50 border-orange-200 text-primary-container',
    error: 'bg-error-container border-error/20 text-on-error-container',
    info: 'bg-primary-fixed border-primary/20 text-primary'
  };

  return (
    <div className={`fixed bottom-4 right-4 z-50 flex items-center gap-3 px-5 py-3 rounded-xl border shadow-lg animate-fade-in backdrop-blur-md ${bgColors[type]}`}>
      <span className="material-symbols-outlined">{icons[type]}</span>
      <span className="text-sm font-semibold">{message}</span>
      <button onClick={onClose} className="ml-3 hover:opacity-75 focus:outline-none">
        <span className="material-symbols-outlined text-sm">close</span>
      </button>
    </div>
  );
};
