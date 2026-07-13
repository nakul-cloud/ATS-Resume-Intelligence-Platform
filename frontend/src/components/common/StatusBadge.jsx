import React from 'react';

export const StatusBadge = ({ type = 'success', label, className = '' }) => {
  const styles = {
    success: 'bg-[#E0F2E9] text-green-800 border border-[#A5D6A7]',
    warning: 'bg-orange-50 text-primary-container border border-orange-100',
    error: 'bg-error-container text-on-error-container border border-error/20',
    info: 'bg-primary/5 text-primary border border-primary/20'
  };

  return (
    <span className={`px-3 py-1 rounded-full text-xs font-bold ${styles[type]} ${className}`}>
      {label}
    </span>
  );
};
