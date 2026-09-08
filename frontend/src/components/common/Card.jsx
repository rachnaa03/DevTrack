import React from 'react';

/**
 * Reusable Card Container Primitive with subtle border and backdrop blur.
 */
export const Card = ({ children, className = '', ...props }) => {
  return (
    <div className={`card ${className}`.trim()} {...props}>
      {children}
    </div>
  );
};

export default Card;
