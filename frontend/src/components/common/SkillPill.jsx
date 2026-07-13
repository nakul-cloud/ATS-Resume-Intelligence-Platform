import React from 'react';

export const SkillPill = ({ skill, className = '' }) => {
  return (
    <span className={`bg-secondary-container text-on-secondary-container border border-outline-variant/30 px-3 py-1 rounded-full text-xs font-semibold ${className}`}>
      {skill}
    </span>
  );
};
