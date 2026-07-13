import React from 'react';

export const Button = ({ 
  children, 
  onClick, 
  variant = 'primary', // 'primary' | 'ghost' | 'dark' | 'gradient' | 'danger'
  type = 'button',
  disabled = false,
  className = '',
  icon
}) => {
  const baseStyles = 'px-6 py-2.5 rounded-xl font-label-caps text-label-caps font-semibold flex items-center justify-center gap-2 transition-all duration-200 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-primary-container text-white shadow-lg hover:brightness-110 active:scale-95',
    ghost: 'text-on-surface-variant hover:bg-secondary-container border border-outline-variant neomorphic-raised',
    dark: 'bg-primary text-on-primary shadow-sm hover:brightness-110',
    gradient: 'primary-solid-btn text-white',
    danger: 'bg-error text-on-error hover:opacity-90',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${className}`}
    >
      {icon && <span className="material-symbols-outlined text-lg">{icon}</span>}
      {children}
    </button>
  );
};
