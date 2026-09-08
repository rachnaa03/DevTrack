import React from 'react';

/**
 * Reusable Badge Primitive.
 * Variants: 'primary', 'success', 'warning', 'error'
 */
export const Badge = ({ children, variant = 'primary', className = '', ...props }) => {
  return (
    <span className={`badge badge-${variant} ${className}`.trim()} {...props}>
      {children}
    </span>
  );
};

export default Badge;
