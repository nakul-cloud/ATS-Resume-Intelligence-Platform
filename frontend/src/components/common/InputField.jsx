import React from 'react';

export const InputField = ({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
  isTextArea = false,
  rows = 4,
  maxLength,
  helperText,
  className = ''
}) => {
  const inputStyles = 'w-full bg-surface-container-low border border-outline-variant rounded-xl p-3 neomorphic-inset focus:ring-1 focus:ring-primary-container outline-none transition-all resize-none font-body-md text-body-md text-on-surface';

  return (
    <div className={`space-y-1 ${className}`}>
      {label && <label className="text-label-caps font-label-caps text-outline block mb-xs">{label}</label>}
      <div className="relative">
        {isTextArea ? (
          <textarea
            rows={rows}
            placeholder={placeholder}
            value={value}
            onChange={onChange}
            maxLength={maxLength}
            className={inputStyles}
          />
        ) : (
          <input
            type={type}
            placeholder={placeholder}
            value={value}
            onChange={onChange}
            maxLength={maxLength}
            className={inputStyles}
          />
        )}
        {maxLength && value && (
          <span className="absolute bottom-2 right-2 text-[10px] text-outline">
            {value.length} / {maxLength} characters
          </span>
        )}
      </div>
      {helperText && <p className="text-xs text-outline mt-xs">{helperText}</p>}
    </div>
  );
};
