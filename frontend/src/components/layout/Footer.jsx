import React from 'react';

export const Footer = () => {
  return (
    <footer className="bg-surface-container-lowest py-lg border-t border-outline-variant mt-auto">
      <div className="max-w-container-max mx-auto px-md flex flex-col md:flex-row justify-between items-center gap-md">
        <h3 className="font-h3 text-primary opacity-50 font-bold">ATS Resume Intelligence</h3>
        <div className="flex gap-md text-on-secondary-container font-label-caps text-label-caps font-semibold">
          <a className="hover:text-primary transition-colors" href="#">Privacy Policy</a>
          <a className="hover:text-primary transition-colors" href="#">Terms of Service</a>
          <a className="hover:text-primary transition-colors" href="#">Help Center</a>
        </div>
        <p className="text-on-secondary-container font-label-caps text-label-caps opacity-60">
          © 2026 ATS Resume Intelligence. All rights reserved.
        </p>
      </div>
    </footer>
  );
};
