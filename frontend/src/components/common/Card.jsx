import React from 'react';

export const Card = ({ 
  children, 
  variant = 'raised', // 'raised' | 'inset' | 'flat'
  className = '',
  onClick
}) => {
  const styles = {
    raised: 'bg-surface-container-lowest neomorphic-raised border border-outline-variant rounded-3xl p-md',
    inset: 'bg-surface-container-low neomorphic-inset border border-outline-variant rounded-2xl p-md',
    flat: 'bg-surface-container border border-outline-variant rounded-2xl p-md'
  };

  return (
    <div 
      onClick={onClick}
      className={`${styles[variant]} ${onClick ? 'cursor-pointer hover:translate-y-[-2px] hover:shadow-lg transition-all duration-200' : ''} ${className}`}
    >
      {children}
    </div>
  );
};
